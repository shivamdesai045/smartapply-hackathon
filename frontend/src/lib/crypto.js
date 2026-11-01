// Sahayak crypto helpers (Web Crypto only, no libraries). Used by the extension AND the website export.
// Passphrase -> key: PBKDF2-SHA256. Data: AES-256-GCM with a fresh random IV for every save.
(function (root) {
  const cr = (typeof globalThis !== 'undefined' && globalThis.crypto && globalThis.crypto.subtle) ? globalThis.crypto : require('crypto').webcrypto;
  const subtle = cr.subtle, enc = new TextEncoder(), dec = new TextDecoder();
  const ITER = 250000, MIN_ITER = 100000, MAX_ITER = 1000000;   // limits stop a tampered file from freezing the browser

  const rand = (n) => cr.getRandomValues(new Uint8Array(n));
  const b64 = (buf) => { const a = new Uint8Array(buf); let s = ''; for (let i = 0; i < a.length; i++) s += String.fromCharCode(a[i]); return btoa(s); };
  const unb64 = (s) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));
  const checkIter = (n) => { if (!Number.isInteger(n) || n < MIN_ITER || n > MAX_ITER) throw new Error('Unsupported file settings'); };

  async function deriveKey(pass, salt, iterations) {
    const base = await subtle.importKey('raw', enc.encode(pass), 'PBKDF2', false, ['deriveKey']);
    return subtle.deriveKey({ name: 'PBKDF2', salt, iterations, hash: 'SHA-256' }, base, { name: 'AES-GCM', length: 256 }, true, ['encrypt', 'decrypt']);
  }
  async function encryptWithKey(key, obj) {
    const iv = rand(12);
    const ct = await subtle.encrypt({ name: 'AES-GCM', iv }, key, enc.encode(JSON.stringify(obj)));
    return { iv: b64(iv), ct: b64(ct) };
  }
  async function decryptWithKey(key, box) {
    const pt = await subtle.decrypt({ name: 'AES-GCM', iv: unb64(box.iv) }, key, unb64(box.ct));   // throws if key is wrong or data was changed
    return JSON.parse(dec.decode(pt));
  }
  const exportKey = (key) => subtle.exportKey('jwk', key);
  const importKey = (jwk) => subtle.importKey('jwk', jwk, { name: 'AES-GCM' }, true, ['encrypt', 'decrypt']);

  // One-off package protected by a passphrase (used for the exported file)
  async function encryptWithPassphrase(pass, obj) {
    const salt = rand(16), key = await deriveKey(pass, salt, ITER);
    return Object.assign({ kdf: 'PBKDF2-SHA256', iterations: ITER, salt: b64(salt) }, await encryptWithKey(key, obj));
  }
  async function decryptWithPassphrase(pass, pkg) {
    checkIter(pkg.iterations);
    return decryptWithKey(await deriveKey(pass, unb64(pkg.salt), pkg.iterations), pkg);
  }

  // The extension's own vault: derive the key once, then re-encrypt on every save with that key
  async function createVault(pass, obj) {
    const salt = rand(16), key = await deriveKey(pass, salt, ITER);
    const box = await encryptWithKey(key, obj);
    return { key, vault: Object.assign({ v: 1, kdf: 'PBKDF2-SHA256', iterations: ITER, salt: b64(salt) }, box) };
  }
  async function unlockVault(pass, vault) {
    checkIter(vault.iterations);
    const key = await deriveKey(pass, unb64(vault.salt), vault.iterations);
    return { key, data: await decryptWithKey(key, vault) };
  }
  async function sealVault(key, vault, obj) { return Object.assign({}, vault, await encryptWithKey(key, obj)); }

  const api = { encryptWithPassphrase, decryptWithPassphrase, createVault, unlockVault, sealVault, decryptWithKey, exportKey, importKey };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.SahayakCrypto = api;
})(typeof globalThis !== 'undefined' ? globalThis : (typeof self !== 'undefined' ? self : this));
