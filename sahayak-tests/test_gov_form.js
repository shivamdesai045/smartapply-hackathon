const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');

const extDir = path.resolve(__dirname, '../sahayak-autofill/autofill-ext');
const govFormHtmlPath = path.join(extDir, 'test-form-gov-style.html');
const autofillCode = fs.readFileSync(path.join(extDir, 'lib/autofill.js'), 'utf8');

async function runGovFormTests() {
  console.log('--- Running Tests for Gov-Style Form ---');

  const govHtml = fs.readFileSync(govFormHtmlPath, 'utf8');
  const dom = new JSDOM(govHtml, {
    url: 'http://localhost/test-form-gov-style.html',
    runScripts: 'dangerously'
  });
  const win = dom.window;
  const doc = win.document;

  // Mock layout so visible() returns true
  win.Element.prototype.getClientRects = function () {
    return [{ x: 0, y: 0, width: 100, height: 30, top: 0, right: 100, bottom: 30, left: 0 }];
  };

  const sampleProfile = {
    fullName: 'Rajesh Kumar',
    fatherName: 'Mohan Kumar',
    motherName: 'Shanti Devi',
    dob: '1988-11-25',
    gender: 'Male',
    mobile: '9876543210',
    email: 'rajesh@example.com',
    aadhaar: '234567890123',
    pan: 'ABCPE1234F',
    address: 'Flat 101, Shanti Sadan',
    city: 'Nashik',
    state: 'Maharashtra',
    district: 'Nashik',
    pin: '422001'
  };

  // Inject sahayakAutofill into window
  win.eval(autofillCode);

  // Test 1: dryRun scan
  console.log('Gov Form Test 1: dryRun scan');
  const scanResult = win.sahayakAutofill(sampleProfile, { dryRun: true });
  assert.ok(scanResult.report && scanResult.report.length > 0, 'Report must contain scanned fields');

  // Check that captcha and otp are recognized as manual
  const captchaItem = scanResult.report.find((r) => r.label.toLowerCase().includes('captcha'));
  assert.ok(captchaItem, 'Captcha field must be found in report');
  assert.strictEqual(captchaItem.state, 'manual', 'Captcha must be marked as manual');

  const otpItem = scanResult.report.find((r) => r.label.toLowerCase().includes('otp'));
  assert.ok(otpItem, 'OTP field must be found in report');
  assert.strictEqual(otpItem.state, 'manual', 'OTP must be marked as manual');

  // Test 2: Execute actual fill
  console.log('Gov Form Test 2: Execute actual fill');
  const fillResult = win.sahayakAutofill(sampleProfile, { dryRun: false, overwrite: false });

  // Verify Name
  const txtApp = doc.querySelector('input[name=txtApp]');
  assert.strictEqual(txtApp.value, 'Rajesh Kumar', 'txtApp applicant name should be filled');

  // Verify Father's name
  const txtFH = doc.querySelector('input[name=txtFH]');
  assert.strictEqual(txtFH.value, 'Mohan Kumar', 'Father name should be filled');

  // Verify Mother's name
  const txtMo = doc.querySelector('input[name=txtMo]');
  assert.strictEqual(txtMo.value, 'Shanti Devi', 'Mother name should be filled');

  // Verify Gender radio buttons (Male is r1 with value 1)
  const r1 = doc.getElementById('r1');
  const r2 = doc.getElementById('r2');
  assert.strictEqual(r1.checked, true, 'Male radio button should be checked');
  assert.strictEqual(r2.checked, false, 'Female radio button should not be checked');

  // Verify read-only date picker format (placeholder dd/mm/yyyy -> 25/11/1988)
  const dobPicker = doc.getElementById('dobPicker');
  assert.strictEqual(dobPicker.value, '25/11/1988', 'Readonly date picker should be formatted as 25/11/1988');

  // Verify alternate DOB dropdowns (day 25, month 11, year 1988)
  const dd = doc.querySelector('select[name=dd]');
  const mm = doc.querySelector('select[name=mm]');
  const yy = doc.querySelector('select[name=yy]');
  assert.strictEqual(dd.value, '25', 'Day select should be 25');
  assert.strictEqual(mm.value, '11', 'Month select should be 11');
  assert.strictEqual(yy.value, '1988', 'Year select should be 1988');

  // Verify Aadhaar split into 3 boxes (4 digits each)
  const a1 = doc.querySelector('input[name=a1]');
  const a2 = doc.querySelector('input[name=a2]');
  const a3 = doc.querySelector('input[name=a3]');
  assert.strictEqual(a1.value, '2345', 'Aadhaar box 1 should be 2345');
  assert.strictEqual(a2.value, '6789', 'Aadhaar box 2 should be 6789');
  assert.strictEqual(a3.value, '0123', 'Aadhaar box 3 should be 0123');

  // Verify PAN
  const txtPan = doc.querySelector('input[name=txtPan]');
  assert.strictEqual(txtPan.value, 'ABCPE1234F', 'PAN should be ABCPE1234F');

  // Verify Mobile
  const txtMobile = doc.querySelector('input[name=txtMobile]');
  assert.strictEqual(txtMobile.value, '9876543210', 'Mobile should be 9876543210');

  // Verify Email
  const txtMail = doc.querySelector('input[name=txtMail]');
  assert.strictEqual(txtMail.value, 'rajesh@example.com', 'Email should be rajesh@example.com');

  // Verify Address
  const txtAddr = doc.querySelector('textarea[name=txtAddr]');
  assert.strictEqual(txtAddr.value, 'Flat 101, Shanti Sadan', 'Address should be filled');

  // Verify State dropdown selection (Maharashtra -> value 27)
  const ddlState = doc.getElementById('ddlState');
  assert.strictEqual(ddlState.value, '27', 'State dropdown should have value 27 (Maharashtra)');

  // Verify District: since selecting State fired 'change', ddlDist options should now contain Nashik/Pune/Nagpur
  const ddlDist = doc.getElementById('ddlDist');
  assert.ok(ddlDist.options.length > 1, 'District dropdown options should be populated after state change event');

  // Second pass fill for dynamic district cascade
  win.sahayakAutofill(sampleProfile, { dryRun: false, overwrite: false });
  assert.strictEqual(ddlDist.value, 'Nashik', 'District should now be selected as Nashik on second pass');

  // Verify Village/Town & PIN
  const txtCity = doc.querySelector('input[name=txtCity]');
  assert.strictEqual(txtCity.value, 'Nashik', 'City should be Nashik');

  const txtPin = doc.querySelector('input[name=txtPin]');
  assert.strictEqual(txtPin.value, '422001', 'Pincode should be 422001');

  // Verify Captcha and OTP are untouched
  const captchaText = doc.querySelector('input[name=captchaText]');
  assert.strictEqual(captchaText.value, '', 'Captcha must remain untouched');

  const otpBox = doc.querySelector('input[name=otpBox]');
  assert.strictEqual(otpBox.value, '', 'OTP must remain untouched');

  // Test 3: Auto-derivation of sub-address parts from raw address when omitted
  console.log('Gov Form Test 3: Raw address string auto-derivation');
  // Clear address fields
  ddlState.value = '';
  txtCity.value = '';
  txtPin.value = '';
  const rawAddressProfile = {
    fullName: 'Gourav Sathawane',
    address: 'Village-Garada, Taluka-Tirora, Post-Tirora, District-Gondia, VTC: Garada, PO: Tirora, State: Maharashtra 441911'
    // city, district, state, pin are NOT provided!
  };
  win.sahayakAutofill(rawAddressProfile, { dryRun: false, overwrite: true });
  assert.strictEqual(ddlState.value, '27', 'State Maharashtra should be auto-derived from raw address string');
  assert.strictEqual(txtPin.value, '441911', 'PIN 441911 should be auto-derived from raw address string');
  assert.strictEqual(txtCity.value, 'Garada', 'City Garada should be auto-derived from raw address string');

  console.log('All Gov-Style Form Tests Passed Successfully!');
  process.exit(0);
}

runGovFormTests().catch((err) => {
  console.error('Gov form tests failed:', err);
  process.exit(1);
});

