(() => {
  const $ = (id) => document.getElementById(id);
  const C = SahayakCrypto, IO = SahayakProfileIO;
  const targetTab = Number(new URLSearchParams(location.search).get('tab')) || null;
  const EXTRA_FIELDS={guardianName:'Guardian name',spouseName:'Spouse name',passportNumber:'Passport number',voterId:'Voter ID',drivingLicenceNumber:'Driving licence number',learnerLicenceNumber:'Learner licence number',birthCertificateNumber:'Birth certificate number',placeOfBirth:'Place of birth',nationality:'Nationality'};
  for(const [prefix,level] of [['tenth','10th'],['twelfth','12th']])for(const [suffix,label] of Object.entries({RollNumber:'Roll / seat number',Board:'Board',School:'School',ExamYear:'Passing year',Percentage:'Percentage',TotalMarks:'Total marks'}))EXTRA_FIELDS[prefix+suffix]=level+' '+label;
  const FIELDS = [...IO.FIELDS,...Object.keys(EXTRA_FIELDS)];
  for(const [id,title] of Object.entries(EXTRA_FIELDS)){const label=document.createElement('label');label.textContent=title;const input=document.createElement('input');input.id=id;input.autocomplete='off';label.append(input);document.querySelector('#appMain .grid').append(label);}

  const IDLE_MS = 5 * 60 * 1000;                                   // auto-lock after 5 minutes without use
  const VAULT_KEY = 'sahayakVault', LEGACY_KEY = 'sahayakAutofill', SESSION_KEY = 'sahayakKey', SYNC_KEY = 'sahayakPendingSync';
  let store = null, vault = null, key = null, lockTimer = null, hasLegacy = false, pendingSync = null;   // store = { current, profiles }, kept only while unlocked

  const newId = () => 'p' + Date.now().toString(36);
  const emptyStore = () => { const id = newId(); return { current: id, profiles: { [id]: { label: 'New person' } } }; };
  const labelFor = (p) => p.fullName || 'New person';
  function normalise() {
    if (!store || !store.profiles || !Object.keys(store.profiles).length) store = emptyStore();
    if (!store.profiles[store.current]) store.current = Object.keys(store.profiles)[0];
  }

  // ---------- form <-> profile ----------
  function readForm() { const p = {}; FIELDS.forEach((k) => { p[k] = $(k).value.trim(); }); p.aadhaar = p.aadhaar.replace(/\D/g, ''); p.pan = p.pan.toUpperCase().replace(/\s/g, ''); return p; }
  function writeForm(p) {
    if (p && p.address) {
      const parts = IO.parseAddressParts(p.address);
      if (!p.city && parts.city) p.city = parts.city;
      if (!p.district && parts.district) p.district = parts.district;
      if (!p.state && parts.state) p.state = parts.state;
      if (!p.pin && parts.pin) p.pin = parts.pin;
    }
    FIELDS.forEach((k) => { $(k).value = (p && p[k]) || ''; });
    hints();
  }
  function renderProfiles() {
    const sel = $('profile'); sel.replaceChildren();
    Object.entries(store.profiles).forEach(([id, p]) => { const o = document.createElement('option'); o.value = id; o.textContent = p.label || 'New person'; sel.appendChild(o); });
    sel.value = store.current;
  }
  function hints() {
    const v = readForm();
    $('h-mobile').textContent = v.mobile && !/^[6-9]\d{9}$/.test(v.mobile) ? 'Should be 10 digits' : '';
    $('h-aadhaar').textContent = v.aadhaar && !/^[2-9]\d{11}$/.test(v.aadhaar) ? 'Should be 12 digits' : '';
    $('h-pan').textContent = v.pan && !/^[A-Z]{5}\d{4}[A-Z]$/.test(v.pan) ? 'Format: ABCPE1234F' : '';
    $('h-pin').textContent = v.pin && !/^[1-9]\d{5}$/.test(v.pin) ? 'Should be 6 digits' : '';
  }

  // ---------- encrypted saving (one save at a time, so an older save never overwrites a newer one) ----------
  let saving = Promise.resolve();
  const persist = () => (saving = saving.then(async () => {
    if (!store || !key) return;
    const p = readForm(); p.label = labelFor(p); store.profiles[store.current] = p;
    vault = await C.sealVault(key, vault, store);
    await chrome.storage.local.set({ [VAULT_KEY]: vault });
    const o = $('profile').selectedOptions[0]; if (o) o.textContent = p.label;
    await touch();
  }).catch(() => {}));

  // ---------- lock / unlock ----------
  async function touch() {
    if (!key) return;
    await chrome.storage.session.set({ [SESSION_KEY]: { jwk: await C.exportKey(key), until: Date.now() + IDLE_MS } });
    chrome.alarms.create('sahayakLock', { delayInMinutes: IDLE_MS / 60000 });
    clearTimeout(lockTimer); lockTimer = setTimeout(() => lock('Locked after 5 minutes without use.'), IDLE_MS);
  }
  async function stillUnlocked() {
    if (!key) return false;
    const s = (await chrome.storage.session.get(SESSION_KEY))[SESSION_KEY];
    return !!(s && s.until > Date.now());
  }
  async function lock(msg) {
    clearTimeout(lockTimer); key = null; store = null;
    await chrome.storage.session.remove(SESSION_KEY); chrome.alarms.clear('sahayakLock');
    FIELDS.forEach((k) => { $(k).value = ''; }); $('out').replaceChildren(); $('importOut').replaceChildren();
    showLock(vault ? 'unlock' : 'setup', msg);
  }
  function showLock(mode, msg) {
    const setup = mode === 'setup';
    $('lock').hidden = false; $('appMain').hidden = true; $('lockBtn').hidden = true;
    $('lockTitle').textContent = setup ? 'Create a passphrase' : 'Unlock';
    $('lockNote').textContent = setup
      ? 'This passphrase protects your saved details and is needed every time you use them. Use at least 8 characters, and a phrase that is hard to guess. If you forget it, delete the saved details and send them again directly from the website.' + (hasLegacy ? ' Your details saved earlier will be encrypted with it.' : '')
      : 'Enter your passphrase to use your saved details.';
    $('confirmRow').hidden = !setup; $('wipeLock').hidden = setup;
    $('unlockBtn').textContent = setup ? 'Create and continue' : 'Unlock'; $('unlockBtn').disabled = false;
    $('lockMsg').textContent = msg || ''; $('pass').value = ''; $('pass2').value = ''; $('pass').focus();
    updateSyncUI(false);
  }
  function showMain() {
    $('lock').hidden = true; $('appMain').hidden = false; $('lockBtn').hidden = false;
    renderProfiles(); writeForm(store.profiles[store.current]);
    updateSyncUI(true);
  }
  function updateSyncUI(unlocked) {
    if (!pendingSync) { $('syncNotice').hidden = true; return; }
    $('syncNotice').hidden = false;
    const name = pendingSync.fullName || 'applicant';
    if (unlocked) {
      $('syncTitle').textContent = `Incoming details for "${name}" from Sahayak website`;
      $('syncDesc').textContent = 'Save and encrypt this profile into your vault?';
      $('syncActions').hidden = false;
    } else {
      $('syncTitle').textContent = `Incoming details for "${name}" from Sahayak website`;
      $('syncDesc').textContent = 'Enter your passphrase below to encrypt and save to your vault.';
      $('syncActions').hidden = true;
    }
  }
  async function applyPendingSync() {
    if (!pendingSync || !key) return;
    const profile={};
    for(const field of FIELDS)if(typeof pendingSync[field]==='string')profile[field]=pendingSync[field].trim();
    const id = newId(); profile.label = profile.fullName || 'Imported from website';
    store.profiles[id] = profile; store.current = id;
    vault = await C.sealVault(key, vault, store);
    await chrome.storage.local.set({ [VAULT_KEY]: vault });
    await chrome.storage.session.remove(SYNC_KEY);
    pendingSync = null; updateSyncUI(true);
    try { chrome.action.setBadgeText({ text: '' }); } catch (_) {}
    renderProfiles(); writeForm(profile);
    $('out').textContent='Details saved and encrypted in this extension. Open a form, then click the extension icon to use them.';
  }
  async function submitLock() {
    const pass = $('pass').value, msg = $('lockMsg'); msg.textContent = '';
    $('unlockBtn').disabled = true;
    try {
      if (!vault) {   // first time
        if (pass.length < 8) { msg.textContent = 'Use at least 8 characters.'; return; }
        if (pass !== $('pass2').value) { msg.textContent = 'The two passphrases do not match.'; return; }
        const legacy = (await chrome.storage.local.get(LEGACY_KEY))[LEGACY_KEY];
        store = legacy && legacy.profiles && Object.keys(legacy.profiles).length ? legacy : emptyStore(); normalise();
        const r = await C.createVault(pass, store); vault = r.vault; key = r.key;
        await chrome.storage.local.set({ [VAULT_KEY]: vault }); await chrome.storage.local.remove(LEGACY_KEY); hasLegacy = false;
      } else {
        let r; try { r = await C.unlockVault(pass, vault); } catch (e) { msg.textContent = 'Wrong passphrase.'; return; }
        key = r.key; store = r.data; normalise();
      }
      if (pendingSync) await applyPendingSync();
      await touch(); showMain();
    } finally { $('unlockBtn').disabled = false; }
  }
  async function wipeAll() {
    if (!confirm('Delete ALL saved details from this browser? This cannot be undone.')) return;
    await chrome.storage.local.remove([VAULT_KEY, LEGACY_KEY]); await chrome.storage.session.remove([SESSION_KEY,SYNC_KEY]); chrome.alarms.clear('sahayakLock');
    pendingSync=null;
    vault = null; key = null; store = null; hasLegacy = false; showLock('setup', '');
  }
  async function init() {
    const res = await chrome.storage.local.get([VAULT_KEY, LEGACY_KEY, SYNC_KEY]);
    vault = res[VAULT_KEY] || null; hasLegacy = !!res[LEGACY_KEY];
    pendingSync = (await chrome.storage.session.get(SYNC_KEY))[SYNC_KEY] || null;
    if (!vault) return showLock('setup', '');
    const s = (await chrome.storage.session.get(SESSION_KEY))[SESSION_KEY];
    if (s && s.until > Date.now()) {   // still unlocked from a few minutes ago
      try { key = await C.importKey(s.jwk); store = await C.decryptWithKey(key, vault); normalise(); if(pendingSync) await applyPendingSync(); await touch(); return showMain(); }
      catch (e) { key = null; store = null; await chrome.storage.session.remove(SESSION_KEY); }
    }
    showLock('unlock', '');
  }

  // ---------- messages on screen ----------
  const say = (text, cls, box) => { const p = document.createElement('p'); p.textContent = text; if (cls) p.className = cls; (box || $('out')).appendChild(p); return p; };
  const list = (items, box) => { const ul = document.createElement('ul'); items.slice(0, 14).forEach((t) => { const li = document.createElement('li'); li.textContent = t; ul.appendChild(li); }); (box || $('out')).appendChild(ul); };

  // ---------- import the details file from the website ----------
  async function runImport() {
    const box = $('importOut'); box.replaceChildren();
    if (!(await stillUnlocked())) return lock('Locked. Unlock to import.');
    const f = $('importFile').files[0];
    if (!f) return say('Choose a details file first.', 'warn', box);
    if (f.size > 100000) return say('That file is too large to be a Sahayak details file.', 'err', box);
    try {
      const { profile, warnings } = await IO.parseImport(await f.text(), $('filePass').value);
      const id = newId(); profile.label = profile.fullName || 'Imported person';
      store.profiles[id] = profile; store.current = id;
      renderProfiles(); writeForm(profile); await persist();
      $('filePassRow').hidden = true; $('filePass').value = ''; $('importFile').value = '';
      say(`Imported ${Object.keys(profile).length - 1} details as "${profile.label}".`, 'good', box);
      say('Aadhaar and PAN are not in the file. Type them below if the form needs them. Check everything before filling.', 'note', box);
      if (warnings.length) { say('Skipped:', 'warn', box); list(warnings, box); }
    } catch (e) {
      if (e.code === 'NEED_PASSPHRASE') { $('filePassRow').hidden = false; $('filePass').focus(); say('This file is protected. Enter its passphrase above, then press Import again.', 'warn', box); }
      else say(e.message || 'Could not read that file.', 'err', box);
    }
  }

  // ---------- run on the page ----------
  async function run(dryRun) {
    $('out').replaceChildren();
    if (!(await stillUnlocked())) return lock('Locked. Unlock to use your saved details.');
    if (!targetTab) { say('Click the Sahayak icon on the form page to open this window.', 'err'); return; }
    await persist(); await touch();
    let res;
    try { res = await chrome.scripting.executeScript({ target: { tabId: targetTab, allFrames: true }, func: sahayakAutofill, args: [readForm(), { dryRun, overwrite: $('overwrite').checked }] }); }
    catch (e) { say('Could not reach that page. Browser pages (chrome://) and the Web Store cannot be filled. Click the icon on the form page again.', 'err'); return; }
    const all = res.map((r) => r.result).filter(Boolean);
    if (dryRun) return showScan([].concat(...all.map((r) => r.report || [])));
    const sum = (k) => [...new Set([].concat(...all.map((r) => r[k] || [])))];
    const filled = sum('filled');
    say(filled.length ? `Filled ${filled.length}: ${filled.join(', ')}.` : 'Nothing was filled on this page.', filled.length ? 'good' : 'warn');
    if (sum('skipped').length) { say('Left as is (already has a value):', 'grp'); list(sum('skipped')); }
    if (sum('noOption').length) { say('Dropdown option not found. Pick it yourself:', 'grp warn'); list(sum('noOption')); }
    if (sum('noValue').length) { say('Not saved above (empty):', 'grp warn'); list(sum('noValue')); }
    if (!filled.length) say('Press "Check this page" to see what Sahayak found on the page.');
  }
  function showScan(rows) {
    if (!rows.length) { say('No form fields found. If the form is behind a login or inside another tab, open it first and click the icon on that tab.', 'warn'); return; }
    say(`Found ${rows.length} fields on this page.`);
    [['will_fill', 'Can fill', 'good', (r) => `${r.rule}${r.note ? ' (' + r.note + ')' : ''}  [${r.label}]`],
     ['filled', 'Already has a value (left as is)', '', (r) => r.rule || r.label],
     ['no_value', 'Matched, but you have not saved this detail', 'warn', (r) => r.rule],
     ['no_option', 'Dropdown has no matching option', 'warn', (r) => `${r.rule} [${r.label}]`],
     ['unsupported', 'Not supported, do these yourself', 'warn', (r) => `${r.kind}: ${r.label}`],
     ['manual', 'You must enter these (captcha / OTP)', 'warn', (r) => r.label],
     ['readonly', 'Read-only or disabled', 'warn', (r) => r.label],
     ['unknown', 'Not recognised', '', (r) => `${r.kind}: ${r.label}`]].forEach(([state, title, cls, fmt]) => {
      const items = rows.filter((r) => r.state === state); if (!items.length) return;
      say(`${title}: ${items.length}`, 'grp ' + cls); list(items.map(fmt));
    });
  }

  // ---------- wiring ----------
  FIELDS.forEach((k) => { $(k).addEventListener('input', () => { hints(); persist(); }); $(k).addEventListener('change', persist); });
  $('address').addEventListener('input', () => {
    const addr = $('address').value.trim();
    if (addr) {
      const parts = IO.parseAddressParts(addr);
      if (!$('city').value && parts.city) $('city').value = parts.city;
      if (!$('district').value && parts.district) $('district').value = parts.district;
      if (!$('state').value && parts.state) $('state').value = parts.state;
      if (!$('pin').value && parts.pin) $('pin').value = parts.pin;
    }
  });
  $('profile').addEventListener('change', () => { store.current = $('profile').value; writeForm(store.profiles[store.current]); persist(); });
  $('newProfile').addEventListener('click', () => { const id = newId(); store.profiles[id] = { label: 'New person' }; store.current = id; renderProfiles(); writeForm(store.profiles[id]); persist(); $('fullName').focus(); });
  $('delProfile').addEventListener('click', () => {
    if (!confirm('Delete this saved person?')) return;
    delete store.profiles[store.current]; normalise(); renderProfiles(); writeForm(store.profiles[store.current]); persist();
  });
  $('wipe').addEventListener('click', wipeAll); $('wipeLock').addEventListener('click', wipeAll);
  $('fill').addEventListener('click', () => run(false));
  $('scan').addEventListener('click', () => run(true));
  $('importBtn').addEventListener('click', runImport);
  $('acceptSyncBtn').addEventListener('click', async () => {
    if (pendingSync && key) {
      await applyPendingSync();
      say('Saved and encrypted into your vault!', 'good', $('importOut'));
    }
  });
  $('discardSyncBtn').addEventListener('click', async () => {
    await chrome.storage.session.remove(SYNC_KEY);
    pendingSync = null;
    updateSyncUI(true);
    try { chrome.action.setBadgeText({ text: '' }); } catch (_) {}
  });
  $('lockBtn').addEventListener('click', () => lock(''));
  $('unlockBtn').addEventListener('click', submitLock);
  ['pass', 'pass2'].forEach((id) => $(id).addEventListener('keydown', (e) => { if (e.key === 'Enter') submitLock(); }));
  $('showIds').addEventListener('click',()=>{const reveal=$('aadhaar').type==='password';$('aadhaar').type=$('pan').type=reveal?'text':'password';$('showIds').textContent=reveal?'Hide Aadhaar/PAN':'Show Aadhaar/PAN';});
  init();
})();
