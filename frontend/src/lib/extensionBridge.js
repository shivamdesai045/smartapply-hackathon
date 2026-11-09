function request(type, payload={}, timeoutMs=6000) {
 return new Promise((resolve,reject)=>{
  const requestId=crypto.randomUUID();
  const timer=setTimeout(()=>{window.removeEventListener('message',handler);reject(new Error('Enable or reload the updated extension, then refresh this page.'));},timeoutMs);
  function handler(e) {
   if(e.source!==window || e.origin!==location.origin || e.data?.type!==type+'_RES' || e.data.requestId!==requestId) return;
   clearTimeout(timer);window.removeEventListener('message',handler);
   e.data.success?resolve(e.data):reject(new Error(e.data.error||'Extension could not complete the request.'));
  }
  window.addEventListener('message',handler);
  window.postMessage({type,requestId,...payload},location.origin);
 });
}
export function isExtensionInstalled(){return !!document.documentElement.getAttribute('data-sahayak-extension');}
export async function pingExtension(){return isExtensionInstalled();}
export function sendProfileToExtension(profile){ const safe={...profile};delete safe.aadhaar;delete safe.pan;return request('SAHAYAK_DIRECT_SYNC',{profile:safe}); }
export function prepareApplication(profile,portal,service){return request('SAHAYAK_PREPARE_APPLICATION',{profile,portal,service});}

export async function saveProfileInExtension(profile){
 const version=document.documentElement.getAttribute('data-sahayak-extension');
 if(!version)throw new Error('Extension not detected here. Open this website in the same Chrome profile where Sahayak AutoFill is installed, then refresh it.');
 const [major,minor]=version.split('.').map(Number);
 if(!(major>0||major===0&&minor>=4))throw new Error(`Your browser is running extension ${version}. Direct saving needs 0.4.0 or newer. Update the files in the original extension folder, click Reload on its card at chrome://extensions, then refresh this website.`);
 return request('SAHAYAK_SAVE_PROFILE',{profile});
}
