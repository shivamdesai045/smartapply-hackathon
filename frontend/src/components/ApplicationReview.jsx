import {fetchReviewedIds} from '../lib/api';
import ExtensionGuide from './ExtensionGuide';
import {useMemo,useState,useEffect,useRef} from 'react';
import {buildApplicationFields,validateApplication} from '../lib/applicationProfile';
import {prepareApplication,saveProfileInExtension} from '../lib/extensionBridge';
export default function ApplicationReview({report,serviceName,onBack}) {
 const [secureReport,setSecureReport]=useState(report);
 const [loadingIds,setLoadingIds]=useState(true);
 const [idError,setIdError]=useState('');
 const [showIds,setShowIds]=useState(false);
 const edited=useRef(new Set());
 const fields=useMemo(()=>buildApplicationFields(secureReport),[secureReport]);
 const [values,setValues]=useState(()=>Object.fromEntries(fields.map(f=>[f.key,f.value])));
 const [resolved,setResolved]=useState({});
 const [confirmed,setConfirmed]=useState(false);
 const [busy,setBusy]=useState(false);
 const [message,setMessage]=useState('');
 const portal=report.servicePortal;
 const groupOf=f=>!f.supported?'Other extracted document details':/^(tenth|twelfth)/.test(f.key)?'Education':/aadhaar|pan|passportNumber|voterId|LicenceNumber|birthCertificateNumber/.test(f.key)?'Document numbers':/^(mobile|email|address|city|district|state|pin)$/.test(f.key)?'Contact and address':'Personal details';
 const groups=['Personal details','Contact and address','Document numbers','Education','Other extracted document details'];
 const update=(key,value)=>{edited.current.add(key);setValues(v=>({...v,[key]:value}));setResolved(v=>({...v,[key]:true}));setConfirmed(false);setMessage('');};
 useEffect(()=>{
  let active=true;
  setLoadingIds(true);
  fetchReviewedIds(serviceName,report.variant||'adult').then(result=>{
   if(!active)return;
   const secure=result.documents||[];
   const updated={...report,documents:[...(report.documents||[]).map(doc=>secure.some(s=>s.requirement===doc.requirement&&s.chosenOption===doc.chosenOption)?{...doc,docNumber:null,doc_fields:{...doc.doc_fields,doc_number:{value:null}}}:doc),
    ...secure.map(doc=>({requirement:doc.requirement,chosenOption:doc.chosenOption,doc_fields:{doc_number:{value:doc.ids.aadhaar||doc.ids.pan}}}))]};
   setSecureReport(updated);
   const loaded=buildApplicationFields(updated);
   setValues(current=>({...current,...Object.fromEntries(loaded.filter(f=>['aadhaar','pan'].includes(f.key)&&!edited.current.has(f.key)).map(f=>[f.key,f.value]))}));
  }).catch(()=>{if(active)setIdError('Could not unlock stored ID numbers. Refresh to retry, or enter them manually.');}).finally(()=>{if(active)setLoadingIds(false);});
  return()=>{active=false;};
 },[report,serviceName]);
 async function open(saveOnly=false){
  const conflict=fields.find(f=>f.conflict&&!resolved[f.key]);
  if(conflict){setMessage(`Choose or edit ${conflict.label}; the documents disagree.`);return;}
  const profile=Object.fromEntries(fields.filter(f=>f.supported&&values[f.key]?.trim()).map(f=>[f.key,values[f.key].trim()]));
  if(profile.aadhaar) profile.aadhaar=profile.aadhaar.replace(/\s/g,'');
  if(profile.pan) profile.pan=profile.pan.toUpperCase();
  const error=validateApplication(profile);if(error){setMessage(error);return;}
  if(!confirmed){setMessage('Review the details and tick the confirmation below.');return;}
  setBusy(true);try{if(saveOnly){await saveProfileInExtension(profile);setMessage('Details sent directly to the extension. Complete its passphrase setup or unlock to save them permanently. No file upload needed.');}else{await prepareApplication(profile,portal?.url,serviceName);setMessage('Official portal opened. Sign in or open its application form, then click “Fill reviewed details” on that page.');}}catch(e){setMessage(e.message);}finally{setBusy(false);}
 }
 return <section className="max-w-4xl mx-auto p-5 space-y-5 text-gray-900 dark:text-gray-100">
  <button onClick={onBack} className="text-brand-600 underline">← Back to document checks</button>
  <h1 className="text-2xl font-bold">Review your application details</h1>
  <p>{serviceName}: review and edit the extracted values, open the official portal, then fill its form with one click.</p>
  <p className="text-sm text-amber-700 dark:text-amber-300">Changes here prepare your application; they do not correct the original documents or clear document mismatches. Missing information stays blank.</p>
  <ExtensionGuide />
  <div className="rounded border p-3 text-sm space-y-2">
   <p>{loadingIds?'Unlocking your encrypted Aadhaar/PAN numbers…':'Full Aadhaar/PAN numbers are loaded only for your signed-in review. Normal document views remain masked.'}</p>
   {idError&&<p role="alert">{idError}</p>}
   <button type="button" onClick={()=>setShowIds(v=>!v)} className="underline">{showIds?'Hide Aadhaar/PAN':'Show Aadhaar/PAN'}</button>
  </div>
  <div className="space-y-6">{groups.map(group=><fieldset key={group} className="space-y-3"><legend className="text-lg font-bold">{group}</legend><div className="grid sm:grid-cols-2 gap-4">{fields.filter(f=>groupOf(f)===group).map(f=><label key={f.key} className="block rounded-lg border p-3 space-y-2">
   <span className="font-semibold block">{f.label}</span>
   {f.conflict&&<><span className="text-amber-700 text-sm block">Different values found — select one or enter a correction.</span><select aria-label={`Choose ${f.label}`} value="" onChange={e=>update(f.key,e.target.value)} className="w-full border rounded p-2 dark:bg-gray-800"><option value="">Choose extracted value</option>{f.choices.map(c=><option key={c.value} value={c.value}>{['aadhaar','pan'].includes(f.key)&&!showIds?'•••• '+c.value.slice(-4):c.value} — {c.source}</option>)}</select></>}
   <input aria-label={f.label} autoComplete="off" type={['aadhaar','pan'].includes(f.key)&&!showIds?'password':f.key==='dob'?'date':'text'} value={values[f.key]||''} onChange={e=>update(f.key,e.target.value)} className="w-full border rounded p-2 dark:bg-gray-800" />
   <span className="text-xs block text-gray-500">{f.masked?'Full number unavailable: re-scan the document or enter it here for this extension transfer.':f.choices.map(c=>c.source).filter((v,i,a)=>a.indexOf(v)===i).join(', ')||'Optional — enter if required'}</span>
   {!f.supported&&<span className="text-xs block">Document detail — copy this value manually if the official form asks for it.</span>}
  </label>)}</div></fieldset>)}</div>
  <label className="flex gap-3"><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)} />I have reviewed these details and want to use them on the official application form.</label>
  <p className="text-sm">Prepared autofill details expire after 30 minutes and are cleared when the browser session ends. Existing form values are preserved. Review before submitting; login, OTP and CAPTCHA stay manual.</p>
  <button disabled={busy||loadingIds||!confirmed} onClick={()=>open(true)} className="rounded bg-indigo-600 text-white px-5 py-3 disabled:opacity-50">{busy?'Please wait…':'Save details directly to extension'}</button>
  <p className="text-sm">Save once to reuse later: the extension opens and encrypts your profile with your passphrase. You can edit or delete it there. No JSON file is required.</p>
  {portal?.url?<button disabled={busy||loadingIds||!confirmed} onClick={()=>open(false)} className="rounded bg-brand-600 text-white px-5 py-3 disabled:opacity-50">{busy?'Opening…':`Open ${portal.name||'official portal'} & prepare autofill`}</button>:<p>No official portal is configured for this service.</p>}
  {message&&<p role="status" className="border rounded p-3">{message}</p>}

 </section>;
}
