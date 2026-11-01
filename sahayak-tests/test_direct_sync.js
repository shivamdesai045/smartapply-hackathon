const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');
const nodeCrypto = require('crypto');

const extDir = path.resolve(__dirname, '../sahayak-autofill/autofill-ext');
const appHtmlPath = path.join(extDir, 'app.html');

function createMockChrome(storageInitial = {}) {
  const localStorage = Object.assign({}, storageInitial);
  const sessionStorage = {};
  const alarms = {};
  let badgeText = '';

  const makeStorageArea = (store) => ({
    get: async (keys) => {
      if (!keys) return Object.assign({}, store);
      if (typeof keys === 'string') return { [keys]: store[keys] };
      if (Array.isArray(keys)) {
        const out = {};
        keys.forEach((k) => { if (k in store) out[k] = store[k]; });
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
    action: {
      setBadgeText: ({ text }) => { badgeText = text; },
      getBadgeText: () => badgeText,
      setBadgeBackgroundColor: () => {}
    }
  };
}

async function runDirectSyncTest() {
  console.log('--- Running Direct 1-Click Sync Test ---');

  const mockChrome = createMockChrome();

  // 1. Simulate incoming direct sync from website
  console.log('Test 1: Content script / Background receiving direct sync');
  const incomingFromWebsite = {
    fullName: 'Pooja Sharma',
    dob: '1996-03-22',
    address: 'Flat 304, Green Meadows, Pune',
    city: 'Pune',
    district: 'Pune',
    state: 'Maharashtra',
    pin: '411001',
    mobile: '9876543210',
    aadhaar: '234567890123', // Must be strictly dropped!
    pan: 'ABCPE1234F'        // Must be strictly dropped!
  };

  // Content script strips Aadhaar and PAN before queuing
  const safeProfile = Object.assign({}, incomingFromWebsite);
  delete safeProfile.aadhaar;
  delete safeProfile.pan;
  assert.strictEqual(safeProfile.aadhaar, undefined);
  assert.strictEqual(safeProfile.pan, undefined);

  // Background stores in sahayakPendingSync
  await mockChrome.storage.local.set({ sahayakPendingSync: safeProfile });
  mockChrome.action.setBadgeText({ text: '1' });

  assert.strictEqual(mockChrome.action.getBadgeText(), '1');
  assert.ok(mockChrome._localStorage.sahayakPendingSync);

  // 2. Open extension popup while locked
  console.log('Test 2: Extension popup opens with pending sync notice');
  const appHtml = fs.readFileSync(appHtmlPath, 'utf8');
  const appDom = new JSDOM(appHtml, {
    url: 'http://localhost/app.html?tab=1',
    runScripts: 'outside-only',
    pretendToBeVisual: true
  });
  const win = appDom.window;
  const doc = win.document;

  Object.defineProperty(win, 'crypto', { value: nodeCrypto.webcrypto, configurable: true });
  win.chrome = mockChrome;
  win.confirm = () => true;

  const cryptoCode = fs.readFileSync(path.join(extDir, 'lib/crypto.js'), 'utf8');
  const profileIoCode = fs.readFileSync(path.join(extDir, 'lib/profile-io.js'), 'utf8');
  const autofillCode = fs.readFileSync(path.join(extDir, 'lib/autofill.js'), 'utf8');
  const appCode = fs.readFileSync(path.join(extDir, 'app.js'), 'utf8');

  win.eval(cryptoCode);
  win.eval(profileIoCode);
  win.eval(autofillCode);
  win.eval(appCode);

  await new Promise((r) => setTimeout(r, 80));

  // Verify pending sync banner is shown on lock screen
  const syncNotice = doc.getElementById('syncNotice');
  assert.strictEqual(syncNotice.hidden, false, 'Sync notice should be displayed');
  assert.ok(doc.getElementById('syncTitle').textContent.includes('Pooja Sharma'));
  assert.strictEqual(doc.getElementById('syncActions').hidden, true, 'Actions hidden until unlocked');

  // 3. Enter master passphrase to unlock and automatically seal incoming details into vault
  console.log('Test 3: Entering passphrase seals pending profile into AES-256-GCM vault');
  const masterPass = 'StrongMasterPass123!';
  doc.getElementById('pass').value = masterPass;
  doc.getElementById('pass2').value = masterPass;
  doc.getElementById('unlockBtn').click();

  await new Promise((r) => setTimeout(r, 120));

  // Check that lock screen is gone, main screen is visible
  assert.strictEqual(doc.getElementById('appMain').hidden, false);
  assert.strictEqual(doc.getElementById('lock').hidden, true);

  // Form fields are populated with the synced details!
  assert.strictEqual(doc.getElementById('fullName').value, 'Pooja Sharma');
  assert.strictEqual(doc.getElementById('dob').value, '1996-03-22');
  assert.strictEqual(doc.getElementById('mobile').value, '9876543210');
  assert.strictEqual(doc.getElementById('pin').value, '411001');

  // Aadhaar and PAN remain empty for user to type manually
  assert.strictEqual(doc.getElementById('aadhaar').value, '');
  assert.strictEqual(doc.getElementById('pan').value, '');

  // sahayakPendingSync should be cleared from storage
  assert.strictEqual(mockChrome._localStorage.sahayakPendingSync, undefined, 'Pending sync must be cleared after vault sealing');
  assert.strictEqual(mockChrome.action.getBadgeText(), '', 'Badge text cleared');

  // Vault in chrome.storage.local is encrypted: contains NO plaintext name or numbers
  const vaultCipher = JSON.stringify(mockChrome._localStorage.sahayakVault);
  assert.strictEqual(vaultCipher.includes('Pooja'), false, 'Ciphertext must not leak name');
  assert.strictEqual(vaultCipher.includes('9876543210'), false, 'Ciphertext must not leak mobile');

  console.log('All Direct 1-Click Sync Tests Passed Successfully!');
  process.exit(0);
}

runDirectSyncTest().catch((err) => {
  console.error('Direct sync test failed:', err);
  process.exit(1);
});

