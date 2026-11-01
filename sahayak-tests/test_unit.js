const assert = require('assert');
const fs = require('fs');
const path = require('path');

// Verify byte-identical copies
const extCryptoPath = path.resolve(__dirname, '../sahayak-autofill/autofill-ext/lib/crypto.js');
const webCryptoPath = path.resolve(__dirname, '../sahayak-autofill/website-export/lib/crypto.js');
const extProfileIoPath = path.resolve(__dirname, '../sahayak-autofill/autofill-ext/lib/profile-io.js');
const webProfileIoPath = path.resolve(__dirname, '../sahayak-autofill/website-export/lib/profile-io.js');

const extCryptoBuf = fs.readFileSync(extCryptoPath);
const webCryptoBuf = fs.readFileSync(webCryptoPath);
assert.strictEqual(extCryptoBuf.equals(webCryptoBuf), true, 'crypto.js must stay byte-identical between autofill-ext and website-export');

const extProfileIoBuf = fs.readFileSync(extProfileIoPath);
const webProfileIoBuf = fs.readFileSync(webProfileIoPath);
assert.strictEqual(extProfileIoBuf.equals(webProfileIoBuf), true, 'profile-io.js must stay byte-identical between autofill-ext and website-export');

const Crypto = require(extCryptoPath);
const ProfileIO = require(extProfileIoPath);

async function runUnitTests() {
  console.log('--- Running Unit Tests for crypto.js and profile-io.js ---');

  // Test 1: Vault create and unlock
  console.log('Test 1: Vault create and unlock');
  const sampleData = { fullName: 'Ramesh Kumar', state: 'Maharashtra' };
  const pass = 'SecretPassphrase123!';
  const { key, vault } = await Crypto.createVault(pass, sampleData);
  assert.ok(vault.salt, 'Vault must have salt');
  assert.ok(vault.iv, 'Vault must have iv');
  assert.ok(vault.ct, 'Vault must have ct');
  assert.strictEqual(vault.iterations, 250000, 'Iterations should be 250,000');

  const unlocked = await Crypto.unlockVault(pass, vault);
  assert.deepStrictEqual(unlocked.data, sampleData, 'Unlocked vault data must match original');

  // Test 2: Wrong passphrase rejected
  console.log('Test 2: Wrong passphrase rejected');
  await assert.rejects(
    async () => Crypto.unlockVault('WrongPassphrase!', vault),
    /operation failed|MAC|decrypt|tag/i,
    'Unlocking with wrong passphrase must fail'
  );

  // Test 3: Tampered data rejected
  console.log('Test 3: Tampered data rejected');
  const tamperedVault = Object.assign({}, vault);
  // Modify last character of ciphertext
  const lastChar = tamperedVault.ct.slice(-1);
  tamperedVault.ct = tamperedVault.ct.slice(0, -1) + (lastChar === 'A' ? 'B' : 'A');
  await assert.rejects(
    async () => Crypto.unlockVault(pass, tamperedVault),
    /operation failed|MAC|decrypt|tag/i,
    'Unlocking tampered ciphertext must fail'
  );

  // Test 4: Tampered iteration count rejected
  console.log('Test 4: Tampered iteration count rejected');
  const lowIterVault = Object.assign({}, vault, { iterations: 99999 });
  await assert.rejects(
    async () => Crypto.unlockVault(pass, lowIterVault),
    /Unsupported file settings/,
    'Iterations below 100,000 must be rejected'
  );
  const highIterVault = Object.assign({}, vault, { iterations: 1000001 });
  await assert.rejects(
    async () => Crypto.unlockVault(pass, highIterVault),
    /Unsupported file settings/,
    'Iterations above 1,000,000 must be rejected'
  );

  // Test 5: Re-seal uses a new IV
  console.log('Test 5: Re-seal uses a new IV');
  const updatedData = { fullName: 'Ramesh Kumar', state: 'Gujarat' };
  const sealed1 = await Crypto.sealVault(key, vault, updatedData);
  const sealed2 = await Crypto.sealVault(key, vault, updatedData);
  assert.notStrictEqual(sealed1.iv, vault.iv, 'Sealed vault must have a fresh IV');
  assert.notStrictEqual(sealed1.iv, sealed2.iv, 'Two seals of the same vault must have different IVs');
  const unlockedSealed = await Crypto.decryptWithKey(key, sealed1);
  assert.deepStrictEqual(unlockedSealed, updatedData, 'Decrypted sealed vault must match updated data');

  // Test 6: Export/Import Plain round-trip
  console.log('Test 6: Plain export/import round trip');
  const profileInput = {
    fullName: 'Priya Sharma',
    fatherName: 'Rajesh Sharma',
    motherName: 'Sunita Sharma',
    dob: '1995-05-15',
    gender: 'Female',
    mobile: '9876543210',
    email: 'priya@example.com',
    aadhaar: '234567890123',
    pan: 'ABCPE1234F',
    address: '123 MG Road',
    city: 'Pune',
    district: 'Pune',
    state: 'Maharashtra',
    pin: '411001'
  };

  const plainExport = await ProfileIO.buildExport(profileInput);
  assert.strictEqual(plainExport.warnings.length, 0, 'Valid profile should have no warnings');
  const plainParsed = JSON.parse(plainExport.text);
  assert.strictEqual(plainParsed.schema, 'sahayak-profile');
  assert.strictEqual(plainParsed.version, 1);
  assert.strictEqual(plainParsed.encrypted, false);
  assert.strictEqual(plainParsed.profile.fullName, 'Priya Sharma');

  // Test 7: Exported text contains no Aadhaar or PAN
  console.log('Test 7: Exported text contains no Aadhaar or PAN');
  assert.strictEqual(plainParsed.profile.aadhaar, undefined, 'Aadhaar must not be in export profile');
  assert.strictEqual(plainParsed.profile.pan, undefined, 'PAN must not be in export profile');
  assert.strictEqual(plainExport.text.includes('234567890123'), false, 'Export text must not contain Aadhaar number');
  assert.strictEqual(plainExport.text.includes('ABCPE1234F'), false, 'Export text must not contain PAN');

  const importedPlain = await ProfileIO.parseImport(plainExport.text);
  assert.strictEqual(importedPlain.profile.fullName, 'Priya Sharma');
  assert.strictEqual(importedPlain.profile.aadhaar, undefined);
  assert.strictEqual(importedPlain.profile.pan, undefined);

  // Test 8: Protected export/import round-trip
  console.log('Test 8: Protected export/import round trip');
  const filePass = 'FilePassphrase456!';
  const protectedExport = await ProfileIO.buildExport(profileInput, filePass);
  const protJson = JSON.parse(protectedExport.text);
  assert.strictEqual(protJson.encrypted, true);
  assert.strictEqual(protJson.kdf, 'PBKDF2-SHA256');
  assert.ok(protJson.salt && protJson.iv && protJson.ct);
  // Protected text must also never leak Aadhaar or PAN
  assert.strictEqual(protectedExport.text.includes('234567890123'), false);
  assert.strictEqual(protectedExport.text.includes('ABCPE1234F'), false);

  // Parse protected without passphrase
  await assert.rejects(
    async () => ProfileIO.parseImport(protectedExport.text),
    (err) => err.code === 'NEED_PASSPHRASE',
    'Protected file without passphrase must throw NEED_PASSPHRASE'
  );

  // Parse protected with wrong passphrase
  await assert.rejects(
    async () => ProfileIO.parseImport(protectedExport.text, 'WrongFilePass!'),
    (err) => err.code === 'BAD_PASSPHRASE',
    'Protected file with wrong passphrase must throw BAD_PASSPHRASE'
  );

  // Parse protected with correct passphrase
  const importedProt = await ProfileIO.parseImport(protectedExport.text, filePass);
  assert.strictEqual(importedProt.profile.fullName, 'Priya Sharma');
  assert.strictEqual(importedProt.profile.mobile, '9876543210');
  assert.strictEqual(importedProt.profile.pin, '411001');

  // Test 9: Unknown keys dropped
  console.log('Test 9: Unknown keys dropped');
  const withUnknown = {
    fullName: 'Test User',
    hobbies: ['coding', 'music'],
    secretQuestion: 'Favorite food',
    admin: true
  };
  const exportUnknown = await ProfileIO.buildExport(withUnknown);
  const parsedUnknown = JSON.parse(exportUnknown.text);
  assert.strictEqual(parsedUnknown.profile.hobbies, undefined);
  assert.strictEqual(parsedUnknown.profile.secretQuestion, undefined);
  assert.strictEqual(parsedUnknown.profile.admin, undefined);
  assert.strictEqual(parsedUnknown.profile.fullName, 'Test User');

  // Test 10: Invalid dob/mobile/pin/gender/email skipped with warning
  console.log('Test 10: Invalid fields skipped with warnings');
  const invalidProfile = {
    fullName: 'Valid Name',
    dob: '1990-02-31',        // Invalid calendar date
    mobile: '1234567890',      // Does not start with 6-9
    pin: '012345',            // Starts with 0
    gender: 'Robot',          // Invalid gender
    email: 'not-an-email'      // Invalid email format
  };
  const exportInvalid = await ProfileIO.buildExport(invalidProfile);
  assert.strictEqual(exportInvalid.profile, undefined);
  const parsedInvalid = JSON.parse(exportInvalid.text).profile;
  assert.strictEqual(parsedInvalid.fullName, 'Valid Name');
  assert.strictEqual(parsedInvalid.dob, undefined);
  assert.strictEqual(parsedInvalid.mobile, undefined);
  assert.strictEqual(parsedInvalid.pin, undefined);
  assert.strictEqual(parsedInvalid.gender, undefined);
  assert.strictEqual(parsedInvalid.email, undefined);

  assert.ok(exportInvalid.warnings.some((w) => w.includes('dob: must be a real date')), 'Warning for dob missing');
  assert.ok(exportInvalid.warnings.some((w) => w.includes('mobile: must be a 10-digit mobile number')), 'Warning for mobile missing');
  assert.ok(exportInvalid.warnings.some((w) => w.includes('pin: must be 6 digits')), 'Warning for pin missing');
  assert.ok(exportInvalid.warnings.some((w) => w.includes('gender: must be Male, Female or Other')), 'Warning for gender missing');
  assert.ok(exportInvalid.warnings.some((w) => w.includes('email: not a valid email')), 'Warning for email missing');

  // Test 11: Schema, version, oversized, empty rejections
  console.log('Test 11: Schema, version, oversized, empty rejections');
  // Wrong schema
  await assert.rejects(
    async () => ProfileIO.parseImport(JSON.stringify({ schema: 'other-schema', version: 1, profile: { fullName: 'A' } })),
    (err) => err.code === 'WRONG_FILE'
  );
  // Wrong version
  await assert.rejects(
    async () => ProfileIO.parseImport(JSON.stringify({ schema: 'sahayak-profile', version: 2, profile: { fullName: 'A' } })),
    (err) => err.code === 'VERSION'
  );
  // Oversized file (>100,000 bytes)
  const hugeText = ' '.repeat(100005);
  await assert.rejects(
    async () => ProfileIO.parseImport(hugeText),
    (err) => err.code === 'TOO_BIG'
  );
  // Empty profile in buildExport
  await assert.rejects(
    async () => ProfileIO.buildExport({}),
    (err) => err.code === 'EMPTY'
  );
  // Empty profile in parseImport
  await assert.rejects(
    async () => ProfileIO.parseImport(JSON.stringify({ schema: 'sahayak-profile', version: 1, profile: {} })),
    (err) => err.code === 'EMPTY'
  );

  console.log('All Unit Tests Passed Successfully!');
}

runUnitTests().catch((err) => {
  console.error('Unit tests failed:', err);
  process.exit(1);
});

