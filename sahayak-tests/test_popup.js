const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');
const nodeCrypto = require('crypto');

const extDir = path.resolve(__dirname, '../sahayak-autofill/autofill-ext');
const appHtmlPath = path.join(extDir, 'app.html');
const testFormHtmlPath = path.join(extDir, 'test-form.html');
const ProfileIO = require(path.join(extDir, 'lib/profile-io.js'));

function createMockChrome(storageInitial = {}) {
  const localStorage = Object.assign({}, storageInitial);
  const sessionStorage = {};
  const alarms = {};

  const makeStorageArea = (store) => ({
    get: async (keys) => {
      if (!keys) return Object.assign({}, store);
      if (typeof keys === 'string') return { [keys]: store[keys] };
      if (Array.isArray(keys)) {
        const out = {};
        keys.forEach((k) => { if (k in store) out[k] = store[k]; });
        return out;
      }
      if (typeof keys === 'object') {
        const out = Object.assign({}, keys);
        Object.keys(keys).forEach((k) => { if (k in store) out[k] = store[k]; });
        return out;
      }
      return {};
    },
    set: async (items) => {
      Object.assign(store, items);
    },
    remove: async (keys) => {
      const arr = Array.isArray(keys) ? keys : [keys];
      arr.forEach((k) => delete store[k]);
    }
  });

  return {
    _localStorage: localStorage,
    _sessionStorage: sessionStorage,
    _alarms: alarms,
    storage: {
      local: makeStorageArea(localStorage),
      session: makeStorageArea(sessionStorage)
    },
    alarms: {
      create: (name, info) => { alarms[name] = info; },
      clear: (name) => { delete alarms[name]; },
      onAlarm: { addListener: () => {} }
    },
    runtime: {
      getURL: (p) => p
    },
    windows: {
      create: () => {}
    },
    action: {
      onClicked: { addListener: () => {} }
    }
  };
}

async function runPopupLifecycleTest() {
  console.log('--- Running Complete Popup Lifecycle Test ---');

  // Load test-form.html in a second JSDOM instance
  const formHtml = fs.readFileSync(testFormHtmlPath, 'utf8');
  const formDom = new JSDOM(formHtml, {
    url: 'http://localhost/test-form.html',
    runScripts: 'dangerously'
  });
  const formWin = formDom.window;
  const formDoc = formWin.document;

  // Mock getClientRects on elements in the test form page
  formWin.Element.prototype.getClientRects = function () {
    return [{ x: 0, y: 0, width: 100, height: 30, top: 0, right: 100, bottom: 30, left: 0 }];
  };

  const mockChrome = createMockChrome();

  // Implement scripting.executeScript to execute the function in formWin's context
  mockChrome.scripting = {
    executeScript: async ({ target, func, args }) => {
      // In real Chrome, func is serialized and executed in the target page's context
      const injectedFn = formWin.eval('(' + func.toString() + ')');
      const result = injectedFn.apply(formWin, args);
      return [{ frameId: 0, result }];
    }
  };

  // Load app.html in primary JSDOM instance
  const appHtml = fs.readFileSync(appHtmlPath, 'utf8');
  const appDom = new JSDOM(appHtml, {
    url: 'http://localhost/app.html?tab=1',
    runScripts: 'outside-only',
    pretendToBeVisual: true
  });
  const appWin = appDom.window;
  const appDoc = appWin.document;

  // Provide Web Crypto and Chrome mock
  Object.defineProperty(appWin, 'crypto', {
    value: nodeCrypto.webcrypto,
    configurable: true
  });
  appWin.chrome = mockChrome;
  appWin.confirm = () => true;

  // Read scripts
  const cryptoCode = fs.readFileSync(path.join(extDir, 'lib/crypto.js'), 'utf8');
  const profileIoCode = fs.readFileSync(path.join(extDir, 'lib/profile-io.js'), 'utf8');
  const autofillCode = fs.readFileSync(path.join(extDir, 'lib/autofill.js'), 'utf8');
  const appCode = fs.readFileSync(path.join(extDir, 'app.js'), 'utf8');

  // Run scripts in order
  appWin.eval(cryptoCode);
  appWin.eval(profileIoCode);
  appWin.eval(autofillCode);
  appWin.eval(appCode);

  // Give any pending async init a moment
  await new Promise((r) => setTimeout(r, 300));

  // Step 1: First-run create passphrase (too short and mismatch checks)
  console.log('Step 1: First-run create passphrase validation');
  assert.strictEqual(appDoc.getElementById('lock').hidden, false, 'Lock section must be visible on first run');
  assert.strictEqual(appDoc.getElementById('appMain').hidden, true, 'App main must be hidden');
  assert.strictEqual(appDoc.getElementById('lockTitle').textContent, 'Create a passphrase');

  // Short passphrase
  appDoc.getElementById('pass').value = 'short';
  appDoc.getElementById('pass2').value = 'short';
  appDoc.getElementById('unlockBtn').click();
  await new Promise((r) => setTimeout(r, 20));
  assert.strictEqual(appDoc.getElementById('lockMsg').textContent, 'Use at least 8 characters.');

  // Mismatch passphrase
  appDoc.getElementById('pass').value = 'Passphrase123!';
  appDoc.getElementById('pass2').value = 'MismatchPass123!';
  appDoc.getElementById('unlockBtn').click();
  await new Promise((r) => setTimeout(r, 20));
  assert.strictEqual(appDoc.getElementById('lockMsg').textContent, 'The two passphrases do not match.');

  // Successful passphrase creation
  const masterPass = 'MasterPassphrase123!';
  appDoc.getElementById('pass').value = masterPass;
  appDoc.getElementById('pass2').value = masterPass;
  appDoc.getElementById('unlockBtn').click();
  await new Promise((r) => setTimeout(r, 100));

  assert.strictEqual(appDoc.getElementById('lock').hidden, true, 'Lock section should hide on unlock');
  assert.strictEqual(appDoc.getElementById('appMain').hidden, false, 'App main should display on unlock');
  assert.ok(mockChrome._localStorage.sahayakVault, 'Vault must be created in chrome.storage.local');

  // Step 2: Import protected file flow
  console.log('Step 2: Import protected file flow');
  const sampleProfile = {
    fullName: 'Arjun Mehta',
    fatherName: 'Sanjay Mehta',
    motherName: 'Kavita Mehta',
    dob: '1992-08-20',
    gender: 'Male',
    mobile: '9876543210',
    email: 'arjun@example.com',
    aadhaar: '234567890123', // Will be stripped by buildExport
    pan: 'ABCPE1234F',       // Will be stripped by buildExport
    address: '45 Lake View Residency',
    city: 'Pune',
    district: 'Pune',
    state: 'Maharashtra',
    pin: '411001'
  };

  const filePass = 'FilePassphrase789!';
  const protectedExport = await ProfileIO.buildExport(sampleProfile, filePass);

  const fakeFile = {
    name: 'sahayak-details.json',
    size: protectedExport.text.length,
    text: async () => protectedExport.text
  };

  const importFileInput = appDoc.getElementById('importFile');
  Object.defineProperty(importFileInput, 'files', {
    value: [fakeFile],
    configurable: true
  });

  // Attempt import without entering passphrase
  appDoc.getElementById('importBtn').click();
  await new Promise((r) => setTimeout(r, 300));
  assert.strictEqual(appDoc.getElementById('filePassRow').hidden, false, 'filePassRow should become visible');
  assert.ok(appDoc.getElementById('importOut').textContent.includes('This file is protected'), 'Should ask for passphrase');

  // Attempt import with wrong passphrase
  appDoc.getElementById('filePass').value = 'WrongFilePass!';
  appDoc.getElementById('importBtn').click();
  await new Promise((r) => setTimeout(r, 300));
  assert.ok(appDoc.getElementById('importOut').textContent.includes('Wrong passphrase'), 'Should reject wrong passphrase');

  // Attempt import with correct passphrase
  appDoc.getElementById('filePass').value = filePass;
  appDoc.getElementById('importBtn').click();
  await new Promise((r) => setTimeout(r, 100));
  assert.ok(appDoc.getElementById('importOut').textContent.includes('Imported'), 'Should successfully import');
  assert.strictEqual(appDoc.getElementById('fullName').value, 'Arjun Mehta');
  assert.strictEqual(appDoc.getElementById('mobile').value, '9876543210');
  // Aadhaar and PAN are never in the file
  assert.strictEqual(appDoc.getElementById('aadhaar').value, '');
  assert.strictEqual(appDoc.getElementById('pan').value, '');

  // User manually types Aadhaar and PAN into the extension
  appDoc.getElementById('aadhaar').value = '234567890123';
  appDoc.getElementById('aadhaar').dispatchEvent(new appWin.Event('input'));
  appDoc.getElementById('aadhaar').dispatchEvent(new appWin.Event('change'));

  appDoc.getElementById('pan').value = 'ABCPE1234F';
  appDoc.getElementById('pan').dispatchEvent(new appWin.Event('input'));
  appDoc.getElementById('pan').dispatchEvent(new appWin.Event('change'));
  await new Promise((r) => setTimeout(r, 100));

  // Step 3: Stored data is unreadable in storage.local
  console.log('Step 3: Stored data is unreadable in storage.local');
  const vaultInStorage = JSON.stringify(mockChrome._localStorage.sahayakVault);
  assert.strictEqual(vaultInStorage.includes('Arjun'), false, 'Name must not appear in vault ciphertext');
  assert.strictEqual(vaultInStorage.includes('9876543210'), false, 'Mobile must not appear in vault ciphertext');
  assert.strictEqual(vaultInStorage.includes('234567890123'), false, 'Aadhaar must not appear in vault ciphertext');
  assert.strictEqual(vaultInStorage.includes('ABCPE1234F'), false, 'PAN must not appear in vault ciphertext');

  // Step 4: "Check this page" (dryRun)
  console.log('Step 4: Check this page (scan)');
  appDoc.getElementById('scan').click();
  await new Promise((r) => setTimeout(r, 100));
  const scanOut = appDoc.getElementById('out').textContent;
  assert.ok(scanOut.includes('Found') && scanOut.includes('fields on this page'), 'Scan output must show found fields');

  // Step 5: "Fill this page"
  console.log('Step 5: Fill this page');
  appDoc.getElementById('fill').click();
  await new Promise((r) => setTimeout(r, 100));
  const fillOut = appDoc.getElementById('out').textContent;
  assert.ok(fillOut.includes('Filled'), 'Fill output must report filled count');

  // Verify fields in test-form.html
  assert.strictEqual(formDoc.getElementById('a').value, 'Arjun Mehta', 'Applicant Name should be filled');
  assert.strictEqual(formDoc.getElementById('b').value, 'Sanjay Mehta', "Father's Name should be filled");
  assert.strictEqual(formDoc.getElementById('m').value, 'Kavita Mehta', "Mother's Name should be filled");
  assert.strictEqual(formDoc.getElementById('c').value, '1992-08-20', 'DOB should be filled');
  assert.strictEqual(formDoc.getElementById('g').value, 'Male', 'Gender should be filled');
  assert.strictEqual(formDoc.getElementById('mo').value, '9876543210', 'Mobile should be filled');
  assert.strictEqual(formDoc.getElementById('em').value, 'arjun@example.com', 'Email should be filled');
  assert.strictEqual(formDoc.getElementById('d').value, '234567890123', 'Aadhaar should be filled');
  assert.strictEqual(formDoc.getElementById('e').value, 'ABCPE1234F', 'PAN should be filled');
  assert.strictEqual(formDoc.getElementById('ad').value, '45 Lake View Residency', 'Address should be filled');
  assert.strictEqual(formDoc.getElementById('s').value, 'Maharashtra', 'State should be filled');
  assert.strictEqual(formDoc.getElementById('di').value, 'Pune', 'District should be filled');
  assert.strictEqual(formDoc.getElementById('h').value, '411001', 'PIN should be filled');
  // Check that User Name is left completely EMPTY
  assert.strictEqual(formDoc.getElementById('j').value, '', 'User Name MUST remain empty');

  // Step 6: Lock clears the form
  console.log('Step 6: Lock clears the form');
  appDoc.getElementById('lockBtn').click();
  await new Promise((r) => setTimeout(r, 300));
  assert.strictEqual(appDoc.getElementById('lock').hidden, false, 'Lock screen should be visible');
  assert.strictEqual(appDoc.getElementById('appMain').hidden, true, 'App main should be hidden');
  assert.strictEqual(appDoc.getElementById('fullName').value, '', 'Form field fullName must be cleared on lock');
  assert.strictEqual(appDoc.getElementById('mobile').value, '', 'Form field mobile must be cleared on lock');

  // Step 7: Wrong then right passphrase on unlock
  console.log('Step 7: Wrong then right passphrase on unlock');
  appDoc.getElementById('pass').value = 'WrongPassword!';
  appDoc.getElementById('unlockBtn').click();
  await new Promise((r) => setTimeout(r, 300));
  assert.strictEqual(appDoc.getElementById('lockMsg').textContent, 'Wrong passphrase.');

  appDoc.getElementById('pass').value = masterPass;
  appDoc.getElementById('unlockBtn').click();
  await new Promise((r) => setTimeout(r, 100));
  assert.strictEqual(appDoc.getElementById('appMain').hidden, false, 'App main should be visible after correct unlock');
  assert.strictEqual(appDoc.getElementById('fullName').value, 'Arjun Mehta', 'Saved profile restored after unlock');

  // Step 8: Expired session makes Fill ask to unlock
  console.log('Step 8: Expired session makes Fill ask to unlock');
  // Expire session
  mockChrome._sessionStorage.sahayakKey.until = Date.now() - 1000;
  appDoc.getElementById('fill').click();
  await new Promise((r) => setTimeout(r, 300));
  assert.strictEqual(appDoc.getElementById('lock').hidden, false, 'Should revert to lock screen when session expired');
  assert.ok(appDoc.getElementById('lockMsg').textContent.includes('Locked. Unlock to use your saved details.'));

  // Step 9: Reopening within 5 minutes stays unlocked, otherwise asks
  console.log('Step 9: Reopening within 5 minutes stays unlocked, otherwise asks');
  // Unlock again
  appDoc.getElementById('pass').value = masterPass;
  appDoc.getElementById('unlockBtn').click();
  await new Promise((r) => setTimeout(r, 100));
  assert.strictEqual(appDoc.getElementById('appMain').hidden, false);

  // Simulate new window load within 5 min (fresh DOM instance using same storage)
  const appDomWithin5 = new JSDOM(appHtml, {
    url: 'http://localhost/app.html?tab=1',
    runScripts: 'outside-only',
    pretendToBeVisual: true
  });
  const winWithin5 = appDomWithin5.window;
  Object.defineProperty(winWithin5, 'crypto', { value: nodeCrypto.webcrypto, configurable: true });
  winWithin5.chrome = mockChrome;
  winWithin5.eval(cryptoCode);
  winWithin5.eval(profileIoCode);
  winWithin5.eval(autofillCode);
  winWithin5.eval(appCode);
  await new Promise((r) => setTimeout(r, 100));
  assert.strictEqual(winWithin5.document.getElementById('appMain').hidden, false, 'Reopening within 5 min should be unlocked');

  // Simulate new window load after 5 min expiration
  mockChrome._sessionStorage.sahayakKey.until = Date.now() - 1000;
  const appDomAfter5 = new JSDOM(appHtml, {
    url: 'http://localhost/app.html?tab=1',
    runScripts: 'outside-only',
    pretendToBeVisual: true
  });
  const winAfter5 = appDomAfter5.window;
  Object.defineProperty(winAfter5, 'crypto', { value: nodeCrypto.webcrypto, configurable: true });
  winAfter5.chrome = mockChrome;
  winAfter5.eval(cryptoCode);
  winAfter5.eval(profileIoCode);
  winAfter5.eval(autofillCode);
  winAfter5.eval(appCode);
  await new Promise((r) => setTimeout(r, 100));
  assert.strictEqual(winAfter5.document.getElementById('lock').hidden, false, 'Reopening after 5 min should ask for passphrase');
  assert.strictEqual(winAfter5.document.getElementById('appMain').hidden, true);

  // Step 10: Delete all (wipe)
  console.log('Step 10: Delete all (wipe)');
  appDoc.getElementById('wipe').click();
  await new Promise((r) => setTimeout(r, 300));
  assert.strictEqual(mockChrome._localStorage.sahayakVault, undefined, 'Vault must be deleted from storage.local');
  assert.strictEqual(mockChrome._sessionStorage.sahayakKey, undefined, 'Session key must be deleted');
  assert.strictEqual(appDoc.getElementById('lock').hidden, false, 'Should return to setup screen');
  assert.strictEqual(appDoc.getElementById('lockTitle').textContent, 'Create a passphrase');

  // Step 11: Migration from old plain-text store key "sahayakAutofill"
  console.log('Step 11: Migration from legacy key sahayakAutofill');
  const legacyData = {
    current: 'p_old',
    profiles: {
      p_old: {
        label: 'Legacy User',
        fullName: 'Legacy User',
        mobile: '9876500000',
        city: 'Ahmedabad',
        state: 'Gujarat'
      }
    }
  };
  mockChrome._localStorage.sahayakAutofill = legacyData;

  const appDomMigration = new JSDOM(appHtml, {
    url: 'http://localhost/app.html?tab=1',
    runScripts: 'outside-only',
    pretendToBeVisual: true
  });
  const winMig = appDomMigration.window;
  Object.defineProperty(winMig, 'crypto', { value: nodeCrypto.webcrypto, configurable: true });
  winMig.chrome = mockChrome;
  winMig.eval(cryptoCode);
  winMig.eval(profileIoCode);
  winMig.eval(autofillCode);
  winMig.eval(appCode);
  await new Promise((r) => setTimeout(r, 300));

  assert.strictEqual(winMig.document.getElementById('lockTitle').textContent, 'Create a passphrase');
  assert.ok(winMig.document.getElementById('lockNote').textContent.includes('Your details saved earlier will be encrypted with it'));

  winMig.document.getElementById('pass').value = 'NewPassphrase123!';
  winMig.document.getElementById('pass2').value = 'NewPassphrase123!';
  winMig.document.getElementById('unlockBtn').click();
  await new Promise((r) => setTimeout(r, 100));

  assert.strictEqual(winMig.document.getElementById('appMain').hidden, false);
  assert.strictEqual(winMig.document.getElementById('fullName').value, 'Legacy User');
  assert.strictEqual(winMig.document.getElementById('mobile').value, '9876500000');
  assert.ok(mockChrome._localStorage.sahayakVault, 'New vault should exist');
  assert.strictEqual(mockChrome._localStorage.sahayakAutofill, undefined, 'Legacy key must be removed');

  console.log('All Popup Lifecycle Tests Passed Successfully!');
  process.exit(0);
}

runPopupLifecycleTest().catch((err) => {
  console.error('Popup lifecycle test failed:', err);
  process.exit(1);
});
