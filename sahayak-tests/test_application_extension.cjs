const puppeteer=require('../frontend/node_modules/puppeteer-core');
const path=require('node:path');const assert=require('node:assert/strict');const fs=require('node:fs');
(async()=>{
 const browser=await puppeteer.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,pipe:true,enableExtensions:[path.resolve('sahayak-autofill/autofill-ext')],userDataDir:path.resolve('work/application-extension-browser')});
 try{
 const page=await browser.newPage();await page.setRequestInterception(true);page.on('request',r=>r.respond({status:200,contentType:'text/html',body:'<html><body>Synthetic application</body></html>'}));
 await page.goto('http://127.0.0.1:5173/extension-test');
 await page.waitForFunction(()=>document.documentElement.getAttribute('data-sahayak-extension')==='0.4.0');
 const target=await browser.waitForTarget(t=>t.type()==='service_worker');const worker=await target.worker();
 const send=(profile,portal='https://www.passportindia.gov.in/')=>page.evaluate(({profile,portal})=>new Promise(resolve=>{const requestId=crypto.randomUUID();function handler(e){if(e.data?.requestId===requestId&&e.data.type==='SAHAYAK_PREPARE_APPLICATION_RES'){window.removeEventListener('message',handler);resolve(e.data);}}window.addEventListener('message',handler);window.postMessage({type:'SAHAYAK_PREPARE_APPLICATION',requestId,profile,portal,service:'Synthetic passport application'},location.origin);}),{profile,portal});
 assert.equal((await send({fullName:'Synthetic Example'},'https://example.com')).success,false);
 assert.equal((await send({fullName:'Synthetic Example',aadhaar:'XXXX XXXX 1234'})).success,false);
 const profile={fullName:'Synthetic Example',dob:'2002-08-19',fatherName:'Synthetic Parent',passportNumber:'Z1234567',pan:'ABCDE1234F',tenthRollNumber:'SSC123',twelfthRollNumber:'HSC456',tenthBoard:'CBSE',email:'example@example.test',mobile:'9876543210'};
 const response=await send(profile);assert.equal(response.success,true,response.error);
 // Stop the new portal tab immediately; render a synthetic form, never submit or contact a government form.
 const tabInfo=await worker.evaluate(async()=>{const all=await chrome.storage.session.get(null);const key=Object.keys(all).find(k=>k.startsWith('application:'));return {id:Number(key.split(':')[1]),stored:!!all[key]?.profile,origin:all[key]?.origin,localKeys:Object.keys(await chrome.storage.local.get(null))};});
 assert.ok(tabInfo.stored);assert.ok(!tabInfo.localKeys.some(k=>k.startsWith('application:')));
 const tab=await browser.waitForTarget(t=>t.type()==='page'&&t.url().startsWith('https://www.passportindia.gov.in'));
 const portal=await tab.page();await portal.setRequestInterception(true);portal.on('request',r=>r.respond({status:200,contentType:'text/html',body:`<html><body><form onsubmit="window.wasSubmitted=true;return false"><label>Full name<input id="fullName"></label><label>Date of birth<input id="dob" type="date"></label><label>Passport number<input id="passport"></label><label>PAN number<input id="pan"></label><label>Father name<input id="father"></label><label>Email<input id="email" value="already@example.test"></label><label>OTP<input id="otp"></label><label>Mobile OTP<input id="mobileOtp"></label><label>Password<input id="password" type="password"></label><fieldset><legend>Class 10</legend><label>Roll number<input id="tenthRoll"></label><label>Board<select id="board"><option value="">Select</option><option>CBSE</option></select></label></fieldset><fieldset><legend>Class 12</legend><label>Roll number<input id="twelfthRoll"></label></fieldset><button type="submit">Submit</button></form></body></html>`}));
 await portal.goto('https://www.passportindia.gov.in/synthetic-extension-test');
 await portal.waitForSelector('#sahayak-reviewed-autofill');
 // Click the actual closed-shadow UI via CDP's pierced DOM.
 const cdp=await portal.createCDPSession();await cdp.send('DOM.enable');
 const doc=await cdp.send('DOM.getDocument',{depth:-1,pierce:true});
 const find=(node)=>{if(node.nodeName==='BUTTON'&&node.attributes?.includes('fill'))return node;for(const c of [...(node.children||[]),...(node.shadowRoots||[])]){const n=find(c);if(n)return n;}};
 const button=find(doc.root);assert.ok(button,'Floating Fill button exists');const remote=await cdp.send('DOM.resolveNode',{nodeId:button.nodeId});await cdp.send('Runtime.callFunctionOn',{objectId:remote.object.objectId,functionDeclaration:'function(){this.click();}'});
 await portal.waitForFunction(()=>document.querySelector('#fullName').value==='Synthetic Example');
 const values=await portal.evaluate(()=>Object.fromEntries([...document.querySelectorAll('input,select')].map(e=>[e.id,e.value])));
 assert.equal(values.dob,profile.dob);assert.equal(values.passport,profile.passportNumber);assert.equal(values.pan,profile.pan);assert.equal(values.father,profile.fatherName);assert.equal(values.tenthRoll,'SSC123');assert.equal(values.twelfthRoll,'HSC456');assert.equal(values.board,'CBSE');assert.equal(values.email,'already@example.test');assert.equal(values.otp,'');assert.equal(values.mobileOtp,'');assert.equal(values.password,'');assert.equal(await portal.evaluate(()=>!!window.wasSubmitted),false);
 const state=await worker.evaluate(async(id)=>{const stored=(await chrome.storage.session.get('application:'+id))['application:'+id];return {profileOnOfficialPage:!!stored,otherTab:await applicationFor({tab:{id:id+999},frameId:0,url:'https://www.passportindia.gov.in/'}),otherOrigin:await applicationFor({tab:{id},frameId:0,url:'https://example.com/'}),untrusted:trustedApp({frameId:0,url:'https://example.com/'})};},tabInfo.id);
 assert.equal(state.otherTab,null);assert.equal(state.otherOrigin,null);assert.equal(state.untrusted,false);
 await worker.evaluate(async id=>{const key='application:'+id;const item=(await chrome.storage.session.get(key))[key];item.expires=Date.now()-1;await chrome.storage.session.set({[key]:item});},tabInfo.id);
 assert.equal(await worker.evaluate(id=>applicationFor({tab:{id},frameId:0,url:'https://www.passportindia.gov.in/'}),tabInfo.id),null);
 console.log('PASS: actual extension handoff, floating-button fill, name/DOB/PAN/passport/parents/10th/12th, dropdown, preserve edits, OTP/password/no submission, target restrictions, session storage and expiry');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
