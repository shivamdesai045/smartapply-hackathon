// Sahayak details file: build (website) and read + check (extension).
// File format: { schema:"sahayak-profile", version:1, ... }  plain => { profile }   protected => { encrypted:true, kdf, iterations, salt, iv, ct }
(function (root) {
  const getCrypto = () => ((typeof module !== 'undefined' && module.exports) ? require('./crypto.js') : ((root && root.SahayakCrypto) || (typeof globalThis !== 'undefined' && globalThis.SahayakCrypto)));
  const SCHEMA = 'sahayak-profile', VERSION = 1, MAX_FILE = 100000;
  const FIELDS = ['fullName', 'fatherName', 'motherName', 'dob', 'gender', 'mobile', 'email', 'aadhaar', 'pan', 'address', 'city', 'district', 'state', 'pin'];
  const NEVER_EXPORT = ['aadhaar', 'pan'];   // ID numbers are typed in the extension, never put in a file or QR
  const INDIAN_STATES = [
    'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh', 'Goa', 'Gujarat',
    'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka', 'Kerala', 'Madhya Pradesh',
    'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland', 'Odisha', 'Punjab',
    'Rajasthan', 'Sikkim', 'Tamil Nadu', 'Telangana', 'Tripura', 'Uttar Pradesh',
    'Uttarakhand', 'West Bengal', 'Delhi', 'Chandigarh', 'Puducherry', 'Jammu and Kashmir', 'Ladakh'
  ];

  const fail = (code, msg) => Object.assign(new Error(msg), { code });

  function parseAddressParts(addr) {
    if (!addr || typeof addr !== 'string') return {};
    const res = {};
    const pinMatch = addr.match(/\b([1-9]\d{5})\b/);
    if (pinMatch) res.pin = pinMatch[1];

    const statePrefix = addr.match(/(?:State|State\/UT)\s*[:\-]?\s*([A-Za-z ]+?)(?:,|$|\n)/i);
    if (statePrefix && statePrefix[1]) res.state = statePrefix[1].trim();
    else {
      for (const st of INDIAN_STATES) {
        if (new RegExp('\\b' + st + '\\b', 'i').test(addr)) { res.state = st; break; }
      }
    }

    const distMatch = addr.match(/(?:District|Distric|Dist)\s*[:\-]?\s*([A-Za-z ]+?)(?:,|$|\n)/i);
    if (distMatch && distMatch[1]) res.district = distMatch[1].trim();

    const vtcMatch = addr.match(/(?:Village|VTC|Town|City)\s*[:\-]?\s*([A-Za-z ]+?)(?:,|$|\n)/i);
    const poMatch = addr.match(/(?:Post|PO)\s*[:\-]?\s*([A-Za-z ]+?)(?:,|$|\n)/i);
    const talukaMatch = addr.match(/(?:Taluka|Tehsil|Sub District|Sub Disrict)\s*[:\-]?\s*([A-Za-z ]+?)(?:,|$|\n)/i);
    if (vtcMatch && vtcMatch[1]) res.city = vtcMatch[1].trim();
    else if (poMatch && poMatch[1]) res.city = poMatch[1].trim();
    else if (talukaMatch && talukaMatch[1]) res.city = talukaMatch[1].trim();

    return res;
  }

  // Keeps only known text fields and drops anything that does not look right. Returns { profile, warnings }.
  function clean(input) {
    const out = {}, warnings = [];
    const drop = (k, why) => warnings.push(`${k}: ${why} (skipped)`);
    FIELDS.forEach((k) => {
      let v = input && input[k];
      if (v === undefined || v === null || v === '') return;
      if (typeof v !== 'string') return drop(k, 'not text');
      v = v.trim().slice(0, 300);
      if (!v) return;
      if (k === 'dob') { const d = new Date(v + 'T00:00:00Z'); if (!/^\d{4}-\d{2}-\d{2}$/.test(v) || isNaN(d) || d.toISOString().slice(0, 10) !== v) return drop(k, 'must be a real date as YYYY-MM-DD'); }
      else if (k === 'gender') { if (!['Male', 'Female', 'Other'].includes(v)) return drop(k, 'must be Male, Female or Other'); }
      else if (k === 'mobile') { v = v.replace(/\D/g, ''); if (v.length > 10) v = v.slice(-10); if (!/^[6-9]\d{9}$/.test(v)) return drop(k, 'must be a 10-digit mobile number'); }
      else if (k === 'pin') { v = v.replace(/\D/g, ''); if (!/^[1-9]\d{5}$/.test(v)) return drop(k, 'must be 6 digits'); }
      else if (k === 'email') { if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v)) return drop(k, 'not a valid email'); }
      else if (k === 'aadhaar') { v = v.replace(/\D/g, ''); if (!/^[2-9]\d{11}$/.test(v)) return drop(k, 'must be 12 digits'); }
      else if (k === 'pan') { v = v.toUpperCase().replace(/\s/g, ''); if (!/^[A-Z]{5}\d{4}[A-Z]$/.test(v)) return drop(k, 'format is ABCPE1234F'); }
      out[k] = v;
    });

    // Intelligent sub-field derivation: if address has city/district/state/pin and they were left empty
    if (out.address) {
      const p = parseAddressParts(out.address);
      if (!out.pin && p.pin) out.pin = p.pin;
      if (!out.state && p.state) out.state = p.state;
      if (!out.district && p.district) out.district = p.district;
      if (!out.city && p.city) out.city = p.city;
    }

    return { profile: out, warnings };
  }

  // Website side: returns the text of the file to download
  async function buildExport(profile, filePassphrase) {
    const safe = {}; Object.keys(profile || {}).forEach((k) => { if (!NEVER_EXPORT.includes(k)) safe[k] = profile[k]; });
    const { profile: p, warnings } = clean(safe);
    if (!Object.keys(p).length) throw fail('EMPTY', 'Nothing to export');
    const Crypto = getCrypto();
    const body = { profile: p, createdAt: new Date().toISOString() };
    const file = filePassphrase
      ? Object.assign({ schema: SCHEMA, version: VERSION, encrypted: true }, await Crypto.encryptWithPassphrase(filePassphrase, body))
      : Object.assign({ schema: SCHEMA, version: VERSION, encrypted: false }, body);
    return { text: JSON.stringify(file, null, 2), warnings };
  }

  // Extension side: reads the file text, returns { profile, warnings }. Throws errors with .code
  async function parseImport(text, filePassphrase) {
    if (typeof text !== 'string' || text.length > MAX_FILE) throw fail('TOO_BIG', 'File is too large to be a Sahayak details file');
    let f; try { f = JSON.parse(text); } catch (e) { throw fail('NOT_JSON', 'This is not a valid details file'); }
    if (!f || f.schema !== SCHEMA) throw fail('WRONG_FILE', 'This is not a Sahayak details file');
    if (f.version !== VERSION) throw fail('VERSION', 'This file was made by a different version of Sahayak');
    let body = f;
    if (f.encrypted) {
      if (!filePassphrase) throw fail('NEED_PASSPHRASE', 'This file is protected. Enter its passphrase');
      const Crypto = getCrypto();
      try { body = await Crypto.decryptWithPassphrase(filePassphrase, f); }
      catch (e) { throw fail('BAD_PASSPHRASE', 'Wrong passphrase, or the file was changed'); }
    }
    const res = clean(body && body.profile);
    if (!Object.keys(res.profile).length) throw fail('EMPTY', 'The file has no usable details');
    return res;
  }

  const api = { FIELDS, clean, buildExport, parseImport, parseAddressParts };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.SahayakProfileIO = api;
})(typeof globalThis !== 'undefined' ? globalThis : (typeof self !== 'undefined' ? self : this));
