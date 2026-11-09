import fs from 'node:fs';
import assert from 'node:assert/strict';
const m=await import('data:text/javascript;base64,'+Buffer.from(fs.readFileSync('frontend/src/lib/applicationProfile.js','utf8')).toString('base64'));
const fields=m.buildApplicationFields({documents:[{chosenOption:'Aadhaar Card',docName:'Synthetic Example',docDob:'2002-08-19',docNumber:{number:'XXXX XXXX 1234'},doc_fields:{gender:{value:'Male'}}},{chosenOption:'10th Marksheet',docName:'Synthetic Other',doc_fields:{doc_number:{value:'X123456'},board:{value:'CBSE'},exam_year:{value:'2018'}}}]});
assert.equal(fields.find(f=>f.key==='fullName').conflict,true);assert.equal(fields.find(f=>f.key==='fullName').value,'');
assert.equal(fields.find(f=>f.key==='aadhaar').value,'');assert.equal(fields.find(f=>f.key==='aadhaar').masked,true);
assert.equal(fields.find(f=>f.key==='tenthRollNumber').value,'X123456');assert.equal(fields.find(f=>f.key==='tenthBoard').value,'CBSE');
assert.match(m.validateApplication({fullName:'Synthetic Example',dob:'2002-02-31'}),/valid/);
assert.equal(m.validateApplication({fullName:'Synthetic Example',dob:'2002-08-19'}),'');
const parent=m.buildApplicationFields({documents:[{requirement:'Father identity',chosenOption:'PAN Card',docName:'Parent Example'}]});assert.equal(parent.find(f=>f.key==='fullName').value,'');
console.log('PASS: conflicts, masked Aadhaar, academic mapping, invalid DOB, parent document isolation');

const ids=m.buildApplicationFields({documents:[{chosenOption:'PAN Card',docNumber:'PAN: abcde1234f'},{chosenOption:'Aadhaar Card',docNumber:'Aadhaar: XXXX XXXX 1234'}]});
assert.equal(ids.find(f=>f.key==='pan').value,'ABCDE1234F');
assert.equal(ids.find(f=>f.key==='aadhaar').value,'');
assert.equal(ids.find(f=>f.key==='aadhaar').masked,true);
const nested=m.buildApplicationFields({documents:[{chosenOption:'PAN Card',doc_fields:{doc_number:{value:{type:'PAN',number:'ABCDE1234F'}}}}]});
assert.equal(nested.find(f=>f.key==='pan').value,'ABCDE1234F');
console.log('PASS: legacy and nested PAN transfers; masked Aadhaar never reconstructed');
