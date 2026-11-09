(() => {
 const trusted=window===window.top && ['http://127.0.0.1:5173','http://localhost:5173'].includes(location.origin);
 function announce(){if(trusted&&document.documentElement)document.documentElement.setAttribute('data-sahayak-extension','0.4.1');}
 announce();document.addEventListener('DOMContentLoaded',announce);
 if(trusted)window.addEventListener('message',async event=>{
  if(event.source!==window||event.origin!==location.origin||!event.data?.requestId)return;
  const {type,requestId,profile,portal,service}=event.data;
  const action={SAHAYAK_SAVE_PROFILE:'SAVE_REVIEWED_PROFILE',SAHAYAK_DIRECT_SYNC:'QUEUE_DIRECT_SYNC',SAHAYAK_PREPARE_APPLICATION:'PREPARE_APPLICATION'}[type];
  if(!action)return;
  let result;
  try{result=await chrome.runtime.sendMessage({action,profile,portal,service});}catch(e){result={success:false,error:e.message};}
  window.postMessage({type:type+'_RES',requestId,...result},location.origin);
 });
 async function showFill(){
  if(window!==window.top||trusted)return;
  let state;try{state=await chrome.runtime.sendMessage({action:'GET_APPLICATION_STATE'});}catch{return;}
  if(!state?.success)return;
  const host=document.createElement('div');host.id='sahayak-reviewed-autofill';
  host.style.cssText='position:fixed;bottom:18px;right:18px;z-index:2147483647';
  const root=host.attachShadow({mode:'closed'});
  root.innerHTML='<style>:host{all:initial}section{font:14px system-ui;background:white;color:#172033;border:1px solid #ccd2e0;border-radius:14px;padding:16px;width:290px;box-shadow:0 8px 35px #0003}button{background:#4f46e5;color:white;border:0;border-radius:7px;padding:10px;cursor:pointer;margin:8px 4px 0 0}button:disabled{opacity:.5}p{font-size:12px;line-height:1.5}h3{margin:0 0 8px;font-size:16px}.clear{background:#e5e7eb;color:#172033}</style><section><h3>Application autofill</h3><div class="service"></div><button class="fill">Fill reviewed details</button><button class="clear">Clear</button><p role="status">Open the application form, then fill. Existing entries are preserved.</p><p>Review before submitting. Login, OTP and CAPTCHA are manual.</p></section>';
  root.querySelector('.service').textContent=state.service;
  const status=root.querySelector('[role=status]');
  root.querySelector('.fill').onclick=async()=>{
   const button=root.querySelector('.fill');button.disabled=true;
   try{
    const res=await chrome.runtime.sendMessage({action:'FILL_APPLICATION'});
    if(!res?.success)throw Error(res?.error||'Autofill unavailable');
    const r=res.result||{};
    status.textContent=`Filled ${(r.filled||[]).length} fields. Preserved ${(r.skipped||[]).length} existing entries. `+((r.noOption||[]).length?'Some dropdown choices need your selection. ':'')+'Check every field; unmatched fields need manual entry. For dependent dropdowns, choose State first and click Fill again.';
   }catch(e){status.textContent=e.message;}finally{button.disabled=false;}
  };
  root.querySelector('.clear').onclick=async()=>{await chrome.runtime.sendMessage({action:'CLEAR_APPLICATION'});host.remove();};
  document.body.append(host);
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',showFill,{once:true});else showFill();
})();
