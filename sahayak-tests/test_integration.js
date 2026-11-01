const assert = require('assert');
const path = require('path');

// Import from frontend lib and extension lib
const { deriveCorrectedProfile, createExportFile } = require('../frontend/src/lib/exportProfile.js');
const extProfileIO = require('../sahayak-autofill/autofill-ext/lib/profile-io.js');

async function runIntegrationTest() {
  console.log('--- Running Integration Test (Website Export -> Extension Import) ---');

  // Simulated realistic verification report produced by backend/app.py
  const sampleReport = {
    service: 'Driving Licence',
    variant: 'adult',
    readinessScore: 85,
    readinessLabel: '85% Needs Attention',
    documents: [
      {
        requirement: 'Identity Proof',
        chosenOption: 'PAN Card',
        uploaded: true,
        docName: 'Suresh Kumar',
        docDob: '1990-04-12',
        docNumber: 'ABCPE1234F' // Must be omitted
      },
      {
        requirement: 'Address Proof',
        chosenOption: 'Aadhaar Card',
        uploaded: true,
        docName: 'Suresh K',
        docDob: '1990-04-12',
        docAddress: 'Flat 202, Gokul Dham, Andheri West, Mumbai, Maharashtra 400058',
        docNumber: '234567890123' // Must be omitted
      }
    ],
    issues: [
      {
        field: 'name',
        documents: ['PAN Card', 'Aadhaar Card'],
        decision: 'doc_a_correct' // User selected PAN Card as authoritative for Name
      }
    ]
  };

  // 1. Derive corrected profile from the report
  const derived = deriveCorrectedProfile(sampleReport);
  console.log('Derived profile:', derived);

  // Invariant assertions: No Aadhaar or PAN ever
  assert.strictEqual(derived.aadhaar, undefined, 'Derived profile must not contain aadhaar');
  assert.strictEqual(derived.pan, undefined, 'Derived profile must not contain pan');
  assert.strictEqual(derived.fullName, 'Suresh Kumar', 'Authoritative name from PAN decision should be used');
  assert.strictEqual(derived.dob, '1990-04-12', 'DOB should be derived');
  assert.strictEqual(derived.pin, '400058', 'PIN should be extracted from address');

  // 2. Export plain details file (no passphrase)
  console.log('Testing plain export -> extension import');
  const plainExport = await createExportFile(derived);
  assert.strictEqual(plainExport.text.includes('ABCPE1234F'), false, 'Export text must not contain PAN');
  assert.strictEqual(plainExport.text.includes('234567890123'), false, 'Export text must not contain Aadhaar');

  // Extension parseImport
  const extParsedPlain = await extProfileIO.parseImport(plainExport.text);
  assert.strictEqual(extParsedPlain.profile.fullName, 'Suresh Kumar');
  assert.strictEqual(extParsedPlain.profile.dob, '1990-04-12');
  assert.strictEqual(extParsedPlain.profile.pin, '400058');
  assert.strictEqual(extParsedPlain.profile.aadhaar, undefined);
  assert.strictEqual(extParsedPlain.profile.pan, undefined);

  // 3. Export protected details file (with passphrase)
  console.log('Testing protected export -> extension import');
  const filePass = 'StrongPassphrase2026!';
  const protExport = await createExportFile(derived, filePass);
  const parsedJson = JSON.parse(protExport.text);
  assert.strictEqual(parsedJson.encrypted, true);

  // Extension parseImport with protected file
  const extParsedProt = await extProfileIO.parseImport(protExport.text, filePass);
  assert.strictEqual(extParsedProt.profile.fullName, 'Suresh Kumar');
  assert.strictEqual(extParsedProt.profile.dob, '1990-04-12');
  assert.strictEqual(extParsedProt.profile.pin, '400058');

  // Wrong passphrase in extension must fail
  await assert.rejects(
    async () => extProfileIO.parseImport(protExport.text, 'WrongPassphrase!'),
    (err) => err.code === 'BAD_PASSPHRASE'
  );

  console.log('Integration Test Passed Successfully!');
  process.exit(0);
}

runIntegrationTest().catch((err) => {
  console.error('Integration test failed:', err);
  process.exit(1);
});

