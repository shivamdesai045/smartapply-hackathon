// Review values per application; never reuse another application's saved profile.
export const BASE_FIELDS = {
 fullName: 'Full name', dob: 'Date of birth', gender: 'Gender', fatherName: "Father’s name", motherName: "Mother’s name", guardianName: "Guardian’s name", spouseName: "Spouse’s name", mobile: 'Mobile number', email: 'Email', address: 'Address', city: 'City / village', district: 'District', state: 'State', pin: 'PIN code',
 aadhaar: 'Aadhaar number', pan: 'PAN', passportNumber: 'Passport number', voterId: 'Voter ID', drivingLicenceNumber: 'Driving licence number', learnerLicenceNumber: 'Learner licence number', birthCertificateNumber: 'Birth certificate number'
};
BASE_FIELDS.placeOfBirth='Place of birth'; BASE_FIELDS.nationality='Nationality';
for(const [prefix,label] of [['tenth','10th'],['twelfth','12th']]) for(const [suffix,title] of Object.entries({RollNumber:'Roll / seat number',Board:'Board',School:'School',ExamYear:'Passing year',Percentage:'Percentage',TotalMarks:'Total marks'})) BASE_FIELDS[prefix+suffix]=`${label}: ${title}`;
const MAP = {name:'fullName', full_name:'fullName', dob:'dob', date_of_birth:'dob', father_name:'fatherName',mother_name:'motherName',guardian_name:'guardianName',spouse_name:'spouseName',gender:'gender',mobile_number:'mobile',email:'email',address:'address',city:'city',district:'district',state:'state',pincode:'pin',place_of_birth:'placeOfBirth',nationality:'nationality'};
export function documentIdKey(type='') {
 if (/aadhaar|aadhar/i.test(type)) return 'aadhaar';
 if (/pan/i.test(type)) return 'pan';
 if (/passport/i.test(type)) return 'passportNumber';
 if (/voter/i.test(type)) return 'voterId';
 if (/learn/i.test(type)) return 'learnerLicenceNumber';
 if (/licen/i.test(type)) return 'drivingLicenceNumber';
 if (/birth/i.test(type)) return 'birthCertificateNumber';
 return null;
}
export function buildApplicationFields(report={}) {
 const fields = Object.fromEntries(Object.entries(BASE_FIELDS).map(([key,label])=>[key,{key,label,choices:[],value:'',supported:true}]));
 const add=(key,label,value,source,supported=true)=>{
  if(value==null || typeof value==='object' || !String(value).trim()) return;
  let text=String(value).trim();
  if(key==='fullName')text=text.replace(/\s+/g,' ');
  if(key==='pan')text=text.replace(/^(?:PAN(?:\s*(?:card|number|no\.?))?|Permanent\s+Account\s+Number)\s*[:\-]\s*/i,'').replace(/\s/g,'').toUpperCase();
  if(key==='aadhaar')text=text.replace(/^aadh?aar(?:\s*(?:card|number|no\.?))?\s*[:\-]\s*/i,'').replace(/[ -]/g,'');
  if(key==='dob'){const match=text.match(/^(\d{2})[/-](\d{2})[/-](\d{4})$/);if(match)text=`${match[3]}-${match[2]}-${match[1]}`;}

  const f=fields[key] ||= {key,label,choices:[],value:'',supported};
  if(!f.choices.some(c=>c.value.toLowerCase()===text.toLowerCase())) f.choices.push({value:text,source});
 };
 for(const [index,doc] of (report.documents||[]).entries()) {
  if(doc.skipped) continue;
  const source=doc.chosenOption||doc.requirement||`Document ${index+1}`;
  // Parent/guardian documents must not supply the applicant's identity.
  const parentDocument=/father|mother|parent|guardian/i.test(doc.requirement||'');
  const raw={name:doc.docName,dob:doc.docDob,address:doc.docAddress,doc_number:doc.docNumber,...(doc.doc_fields||{})};
  for(const [key,entry] of Object.entries(raw)) {
   let value=entry && typeof entry==='object'?(entry.value ?? entry.number):entry;
   if(key==='doc_number'&&value&&typeof value==='object')value=value.number;
   if(key==='doc_number'&&typeof value==='string'&&value.startsWith('{')){try{value=JSON.parse(value).number||value;}catch{}}
   let mapped=MAP[key] || (key==='doc_number'?documentIdKey(source):null);
   const education=/12th|hsc|class 12/i.test(source)?'twelfth':/10th|ssc|class 10/i.test(source)?'tenth':null;
   const academic={doc_number:'RollNumber',roll_number:'RollNumber',seat_number:'RollNumber',board:'Board',board_name:'Board',school:'School',school_name:'School',exam_year:'ExamYear',passing_year:'ExamYear',percentage:'Percentage',total_marks:'TotalMarks'};
   if(education&&academic[key]) mapped=education+academic[key];
   // CISCE unique/index IDs are not school roll numbers. Keep their labels distinct.
   if(education&&key==='doc_number'&&(doc.doc_fields?.unique_id?.value||doc.doc_fields?.index_number?.value)) mapped=null;
   if(parentDocument) mapped=null;
   if(mapped) add(mapped,BASE_FIELDS[mapped],value,source);
   else add(`document_${index}_${key}`,`${source}: ${key.replaceAll('_',' ')}`,value,source,false);
  }
 }
 for(const f of Object.values(fields)) {
  f.conflict=f.choices.length>1;
  f.value=f.conflict?'':f.choices[0]?.value||'';
  if((f.key==='aadhaar' && f.value && !/^\d{12}$/.test(f.value.replace(/\s/g,''))) || (f.key==='pan' && /[X*]{4}/i.test(f.value))) { f.value=''; f.masked=true; }
 }
 return Object.values(fields);
}
export function validateApplication(profile) {
 if(!profile.fullName?.trim()) return 'Enter the applicant’s full name.';
 const checks={aadhaar:/^\d{12}$/,pan:/^[A-Z]{5}[0-9]{4}[A-Z]$/,pin:/^[1-9]\d{5}$/,mobile:/^(?:\+91)?[6-9]\d{9}$/,email:/^[^\s@]+@[^\s@]+\.[^\s@]+$/};
 for(const [key,regex] of Object.entries(checks)) if(profile[key]&&!regex.test(profile[key])) return `Check ${BASE_FIELDS[key]}.`;
 if(profile.dob) { const d=new Date(profile.dob+'T00:00:00Z'); if(!/^\d{4}-\d{2}-\d{2}$/.test(profile.dob)||isNaN(d)||d.toISOString().slice(0,10)!==profile.dob||d>new Date()) return 'Enter a valid date of birth as YYYY-MM-DD.'; }
 return '';
}
