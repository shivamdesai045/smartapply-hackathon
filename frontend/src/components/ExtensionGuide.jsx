import {useEffect,useState} from 'react';

export default function ExtensionGuide(){
 const [version,setVersion]=useState('');
 const outdated=version && Number(version.split('.')[0])===0 && Number(version.split('.')[1])<4;
 const [feedback,setFeedback]=useState('');
 useEffect(()=>{
  const check=()=>setVersion(document.documentElement.getAttribute('data-sahayak-extension')||'');
  check();const observer=new MutationObserver(check);
  observer.observe(document.documentElement,{attributes:true,attributeFilter:['data-sahayak-extension']});
  return ()=>observer.disconnect();
 },[]);
 async function copy(text){try{await navigator.clipboard.writeText(text);setFeedback('Copied. Paste it into Chrome’s address bar.');}catch{setFeedback('Copy the address shown below and paste it into Chrome’s address bar.');}}
 return <details open={!version||!!outdated} className="rounded-xl border border-indigo-200 dark:border-indigo-800 bg-indigo-50 dark:bg-indigo-950/30 p-4">
  <summary className="cursor-pointer font-semibold text-lg">Extension setup & autofill guide <span className="block text-sm font-normal mt-1">{outdated?`Update needed: version ${version} cannot save details directly`:version?`Extension detected · version ${version}`:'Extension not detected in this browser'}</span></summary>
  <div className="space-y-5 mt-4 text-sm leading-relaxed">
   <p>Use <strong>Google Chrome on your computer</strong>. Open this app and the official website in the same Chrome profile. If you are viewing this inside another app’s built-in browser, copy this app’s address and open it in Chrome first.</p>
   <button type="button" onClick={()=>copy(location.origin)} className="rounded border px-3 py-2 bg-white dark:bg-gray-800">Copy this app’s address</button>
   <section aria-labelledby="extension-install-title">
    <h2 id="extension-install-title" className="font-bold text-base mb-2">1. Install the extension once</h2>
    <a href="/downloads/sahayak-autofill.zip" download="sahayak-autofill.zip" className="inline-flex rounded-lg bg-indigo-600 text-white font-semibold px-4 py-3 mb-3">Download extension ZIP</a>
    <p className="mb-3">No project folder needed. Downloading saves the extension files; Chrome still requires the installation steps below.</p>
    <ol className="list-decimal pl-5 space-y-3">
     <li>Click <strong>Download extension ZIP</strong> above. Open Downloads, right-click <strong>sahayak-autofill.zip</strong> and choose <strong>Extract All… → Extract</strong> on Windows. Keep the extracted folder somewhere permanent.</li>
     <li>Open a new Chrome tab. Type <code className="break-all">chrome://extensions</code> in the address bar and press Enter. <button type="button" onClick={()=>copy('chrome://extensions')} className="underline text-indigo-700 dark:text-indigo-300">Copy extensions address</button></li>
     <li>Find <strong>Developer mode</strong> at the top-right of the Extensions page and switch it <strong>on</strong>. The <strong>Load unpacked</strong> button will appear.</li>
     <li>Click <strong>Load unpacked</strong>, browse to the folder you just extracted (usually <strong>Downloads → sahayak-autofill</strong>), and click <strong>Select Folder</strong>. Choose the folder containing <code>manifest.json</code>, not the ZIP or an individual file. Do not delete or move this folder after installation.</li>
     <li>Look for the <strong>Sahayak AutoFill</strong> card. Make sure its enable switch is on. Optionally open Chrome’s puzzle-piece Extensions menu and pin Sahayak AutoFill for easy access.</li>
     <li>Return to this app and <strong>refresh the page</strong>. This guide should show <strong>Extension detected</strong>.</li>
    </ol>
    <p className="mt-3">Updating an existing installation? Download the latest ZIP, extract it and replace the files in the same folder you originally loaded. Then open <code>chrome://extensions</code>, click the circular <strong>Reload</strong> arrow on the Sahayak AutoFill card, and refresh this app.</p>
    <a href="https://developer.chrome.com/docs/extensions/get-started/tutorial/hello-world#load-unpacked" target="_blank" rel="noopener noreferrer" className="inline-block mt-2 underline text-indigo-700 dark:text-indigo-300">Chrome’s official installation instructions ↗</a>
   </section>
   <section aria-labelledby="extension-use-title">
    <h2 id="extension-use-title" className="font-bold text-base mb-2">2. Fill your official application</h2>
    <ol className="list-decimal pl-5 space-y-3">
     <li>Review the extracted details below. Choose the correct value wherever documents disagree, and edit or add missing information.</li>
     <li>To keep your profile in the extension, tick the review confirmation and click <strong>Save details directly to extension</strong>. Set a passphrase once (or unlock your existing vault). Your details save without importing a file. Later, open a form, click Chrome’s Sahayak extension icon, unlock and use its Fill button. Saved profiles can be edited or deleted there.</li>
     <li>For a temporary portal handoff, tick <strong>I have reviewed these details</strong>, then click <strong>Open official portal & prepare autofill</strong>. The button includes the name of your selected portal.</li>
     <li>In the newly opened portal tab, sign in if required and navigate to the application form. Keep using that tab.</li>
     <li>Click <strong>Fill reviewed details</strong> in the floating panel at the bottom-right. Read the result to see how many fields were filled. If selecting State loads District options, make that selection and click Fill again.</li>
     <li>Check every field, enter any unsupported details, and complete OTP or CAPTCHA yourself. <strong>You submit the application manually.</strong> Use <strong>Clear</strong> in the floating panel when finished.</li>
    </ol>
   </section>
   <section aria-labelledby="extension-help-title">
    <h2 id="extension-help-title" className="font-bold text-base mb-2">If something is missing</h2>
    <ul className="list-disc pl-5 space-y-2">
     <li><strong>Not detected:</strong> confirm the extension is enabled in the same Chrome profile, reload its card, and refresh this page. Installing it in Chrome does not enable it in an embedded browser.</li>
     <li><strong>No floating Fill button:</strong> open the portal from this review screen, not a separate tab. After 30 minutes, prepare the details again. A different, unsupported website cannot receive the prepared details.</li>
     <li><strong>Some fields stay blank:</strong> existing entries are preserved. Unusual widgets or embedded forms may need manual entry; a masked Aadhaar cannot supply the missing digits.</li>
     <li><strong>Developer mode is unavailable:</strong> a managed work or school browser may restrict extension installation. Use a permitted personal Chrome profile or ask its administrator.</li>
    </ul>
   </section>
   {feedback&&<p role="status" className="font-medium">{feedback}</p>}
  </div>
 </details>;
}
