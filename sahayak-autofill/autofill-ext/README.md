# Sahayak AutoFill (prototype v0.2)

Import your corrected details from the Sahayak website, keep them encrypted in your browser, and fill them into a form page.
It fills text boxes, dropdowns (gender, state, district, DOB day/month/year), gender radio buttons, Aadhaar split into 3 boxes, and read-only date-picker boxes.
It never clicks Submit and does not touch captcha or OTP. Desktop Chrome and Edge only.

## Install (Chrome or Edge)
1. Unzip. Open `chrome://extensions` (or `edge://extensions`), turn on **Developer mode**, click **Load unpacked**, pick the `autofill-ext` folder.
2. The install warning "read and change data on all websites" is because it must run on any government portal. Use it only for testing.

## Use
1. **First time:** click the Sahayak icon. Create a passphrase (8+ characters). Your details are encrypted with it. If you forget it nothing can be recovered: delete and import again.
2. **Import:** on the Sahayak website press **Export**, then in the extension window choose that file and press **Import file** (enter the file passphrase if you set one). It is added as a new saved person. Aadhaar and PAN are never in the file: type them in yourself.
3. Open the government form page, click the Sahayak icon on that tab, and enter your passphrase if asked.
4. Press **Check this page** first. It fills nothing and lists what it can fill, and what you must do yourself.
5. Press **Fill this page**. Filled fields get a blue outline. Check each one, then submit yourself.
6. The extension locks itself after 5 minutes without use (or press **Lock**). Multi-step forms or dropdowns that load after another dropdown (state then district) may need a second Fill.

## Website part
See `../website-export/` (export button and file format).

## Security notes
- Saved details are encrypted (AES-256-GCM, key from your passphrase with PBKDF2, 250,000 rounds). A weak passphrase can still be guessed, so use a phrase.
- While unlocked, the key is kept in browser memory (cleared on lock, after 5 idle minutes, or when the browser closes). The details are never sent anywhere.
- The permission "all websites" is kept so government forms inside frames work. Before a public release, restrict it to the portals you support.
- Details saved by the older v0.1 are encrypted automatically the first time you create a passphrase.

## Test pages (included)
`test-form.html` (simple) and `test-form-gov-style.html` (tables with no labels, dropdowns, radio, split Aadhaar, read-only date, captcha).
Serve them: `python -m http.server 8000` inside this folder, then open `http://localhost:8000/test-form-gov-style.html`.
(Opening them as file:// needs "Allow access to file URLs" in the extension's details.)

## Good to know
- Only EMPTY fields are filled, unless you tick "Replace values already in the form".
- Fields inside shadow DOM or closed widgets, and non-standard date pickers, may not work. "Check this page" shows what was found.
- Rules for matching fields are in `lib/autofill.js`. Encryption is in `lib/crypto.js`, the details file format in `lib/profile-io.js`.
