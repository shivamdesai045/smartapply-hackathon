import {useEffect,useState} from 'react';

export default function OcrReadiness(){
 const [status,setStatus]=useState(null);
 useEffect(()=>{
  let active=true;
  let nextCheck=0;
  const controller=new AbortController();
  const check=async()=>{if(Date.now()<nextCheck)return;nextCheck=Date.now()+15000;try{const response=await fetch('/api/ocr/health',{signal:controller.signal,cache:'no-store'});if(response.ok){const body=await response.json();if(active&&typeof body.ready==='boolean'){setStatus(body);nextCheck=Date.now()+(body.ready?60000:15000);}}}catch{/* Upload requests provide actionable connection errors. */}};
  check();const timer=setInterval(check,5000);
  return ()=>{active=false;controller.abort();clearInterval(timer);};
 },[]);
 if(!status)return null;
 return <p role="status" className="mb-4 rounded-lg border px-3 py-2 text-sm text-gray-700 dark:text-gray-300">
  {status.ready?'OCR ready — the recognition model is loaded. Queue time is shown separately while processing.':status.warming?'OCR is warming up. Let this finish before the live demo; image uploads may wait for startup.':'OCR is not ready yet. The first image may need model startup; a selectable-text PDF can still be read directly.'}
 </p>;
}
