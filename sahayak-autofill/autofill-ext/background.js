importScripts('lib/autofill.js');
// Clicking the toolbar icon opens the Sahayak window and remembers which tab to fill.
chrome.action.onClicked.addListener((tab) => {
  chrome.windows.create({ url: chrome.runtime.getURL('app.html') + '?tab=' + tab.id, type: 'popup', width: 480, height: 800 });
});

// Auto-lock: after the idle time the saved unlock key is removed, so the next use asks for the passphrase again.
chrome.alarms.onAlarm.addListener((a) => { if (a.name === 'sahayakLock') chrome.storage.session.remove('sahayakKey'); });

// Direct Sync receiver from website content script
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg && msg.action === 'QUEUE_DIRECT_SYNC') {
    if (!trustedApp(sender)) { sendResponse({success:false,error:'Untrusted source'}); return; }
    const profile = msg.profile || {};
    delete profile.aadhaar;
    delete profile.pan;
    chrome.storage.session.set({ sahayakPendingSync: profile }).then(() => {
      try {
        chrome.action.setBadgeText({ text: '1' });
        chrome.action.setBadgeBackgroundColor({ color: '#4F46E5' });
      } catch (_) {}
      sendResponse({ success: true });
    }).catch((err) => {
      sendResponse({ success: false, error: err.message });
    });
    return true;
  }
});

const APP_ORIGINS = new Set(['http://127.0.0.1:5173','http://localhost:5173']);
function trustedApp(sender){try{return sender.frameId===0 && APP_ORIGINS.has(new URL(sender.url).origin);}catch{return false;}}
const PORTALS = new Set(['myaadhaar.uidai.gov.in','www.onlineservices.nsdl.com','voters.eci.gov.in','crsorgi.gov.in','nfsa.gov.in','sarathi.parivahan.gov.in','www.passportindia.gov.in','vahan.parivahan.gov.in','parivahan.gov.in','upsconline.nic.in','cetcell.mahacet.org','jeemain.nta.nic.in','neet.nta.nic.in','pmkisan.gov.in','beneficiary.nha.gov.in','pmaymis.gov.in','www.pmuy.gov.in','scholarships.gov.in']);
const PROFILE_KEYS = ['fullName','dob','gender','fatherName','motherName','guardianName','spouseName','mobile','email','address','city','district','state','pin','aadhaar','pan','passportNumber','voterId','drivingLicenceNumber','learnerLicenceNumber','birthCertificateNumber','placeOfBirth','nationality', ...['tenth','twelfth'].flatMap(p=>['RollNumber','Board','School','ExamYear','Percentage','TotalMarks'].map(k=>p+k))];
const PREFIX='application:';
function samePortal(url, application){
 // Permit official subdomain navigation only within these configured government portals.
 const roots=['passportindia.gov.in','uidai.gov.in','eci.gov.in','parivahan.gov.in'];
 const selected=new URL(application.origin);
 const root=roots.find(r=>selected.hostname===r||selected.hostname.endsWith('.'+r));
 return url.protocol==='https:' && !url.port && (url.origin===application.origin || !!root&&(url.hostname===root||url.hostname.endsWith('.'+root)));
}
async function applicationFor(sender){
 const key=PREFIX+sender.tab?.id;
 const item=(await chrome.storage.session.get(key))[key];
 if(!item)return null;
 if(item.expires<=Date.now()){await chrome.storage.session.remove(key);return null;}
 const url=new URL(sender.url);
 if(sender.frameId!==0||!samePortal(url,item))return null;
 return {...item,origin:url.origin};
}
chrome.runtime.onMessage.addListener((msg,sender,respond)=>{
 if(!['SAVE_REVIEWED_PROFILE','PREPARE_APPLICATION','GET_APPLICATION_STATE','FILL_APPLICATION','CLEAR_APPLICATION'].includes(msg?.action))return;
 (async()=>{
  if(msg.action==='SAVE_REVIEWED_PROFILE'){
   if(!trustedApp(sender))throw Error('Save details from the application review page.');
   const profile={};
   for(const key of PROFILE_KEYS){const value=msg.profile?.[key];if(typeof value==='string'&&value.trim())profile[key]=value.trim().slice(0,key==='address'?2000:200);}
   if(!profile.fullName)throw Error('Applicant name is required.');
   if(profile.aadhaar&&!/^[2-9]\d{11}$/.test(profile.aadhaar))throw Error('Enter a complete Aadhaar number or leave it blank.');
   if(profile.pan&&!/^[A-Z]{5}\d{4}[A-Z]$/.test(profile.pan))throw Error('Check the PAN number.');
   await chrome.storage.session.set({sahayakPendingSync:profile});
   await chrome.windows.create({url:chrome.runtime.getURL('app.html')+'?tab='+sender.tab.id,type:'popup',width:480,height:800});
   return {success:true,pendingUnlock:true};
  }
  if(msg.action==='PREPARE_APPLICATION'){
   if(!trustedApp(sender))throw Error('Prepare details from the application review page.');
   const url=new URL(msg.portal);
   if(url.protocol!=='https:'||url.port||url.username||url.password||!PORTALS.has(url.hostname))throw Error('This official portal is not configured for autofill.');
   const profile={};
   for(const key of PROFILE_KEYS){const value=msg.profile?.[key];if(typeof value==='string'&&value.trim())profile[key]=value.trim().slice(0,key==='address'?2000:200);}
   if(!profile.fullName)throw Error('Applicant name is required.');
   if(profile.aadhaar&&!/^\d{12}$/.test(profile.aadhaar))throw Error('A masked or incomplete Aadhaar cannot be used for autofill.');
   if(profile.pan&&!/^[A-Z]{5}\d{4}[A-Z]$/.test(profile.pan))throw Error('Check the PAN number.');
   // Bind data before navigation, so document_start cannot race storage.
   const tab=await chrome.tabs.create({url:'about:blank'});
   try{
    const expires=Date.now()+30*60*1000;
    await chrome.storage.session.set({[PREFIX+tab.id]:{profile,origin:url.origin,expires,service:String(msg.service||'Application').slice(0,120)}});
    await chrome.alarms.create(PREFIX+tab.id,{when:expires});
    await chrome.tabs.update(tab.id,{url:url.href});
   }catch(e){await chrome.storage.session.remove(PREFIX+tab.id);throw e;}
   return {success:true};
  }
  const application=await applicationFor(sender);
  if(!application)return {success:false,error:'No prepared details for this tab, or the 30-minute session expired.'};
  if(msg.action==='GET_APPLICATION_STATE')return {success:true,service:application.service};
  if(msg.action==='CLEAR_APPLICATION'){await chrome.storage.session.remove(PREFIX+sender.tab.id);return {success:true};}
  const results=await chrome.scripting.executeScript({target:{tabId:sender.tab.id,frameIds:[0]},func:sahayakAutofill,args:[application.profile,{overwrite:false,deriveAddress:false,allowedOrigin:application.origin}]});
  return {success:true,result:results[0]?.result};
 })().then(respond).catch(e=>respond({success:false,error:e.message}));
 return true;
});
chrome.tabs.onRemoved.addListener(id=>{chrome.storage.session.remove(PREFIX+id);chrome.alarms.clear(PREFIX+id);});
chrome.alarms.onAlarm.addListener(alarm=>{if(alarm.name.startsWith(PREFIX))chrome.storage.session.remove(alarm.name);});
