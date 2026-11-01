# Sahayak website: export button

`export-demo.html` shows the export step. Open it by double-clicking (no server needed) and press **Export file**.

## Use it in your real website (any stack)
1. Copy `lib/crypto.js` and `lib/profile-io.js` into your site and load them with `<script>` tags (or `require` them in Node/bundlers, they export the same functions).
2. When you have the corrected details, call:

```js
const { text, warnings } = await SahayakProfileIO.buildExport(correctedProfile, optionalFilePassphrase);
// then download `text` as sahayak-details.json (see download() in export-demo.js)
```

`correctedProfile` uses these keys: fullName, fatherName, motherName, dob (YYYY-MM-DD), gender (Male/Female/Other), mobile, email, address, city, district, state, pin.
Unknown keys are dropped, bad values are skipped (listed in `warnings`), and aadhaar/pan are always left out.

The files in `lib/` must stay identical to the ones in the extension (`autofill-ext/lib/`), because the extension reads exactly this format.
