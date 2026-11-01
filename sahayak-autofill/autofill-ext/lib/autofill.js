// Injected into the web page (app.js). Must stay self-contained: it cannot use outside variables.
// sahayakAutofill(profile, { dryRun, overwrite })
//   dryRun    -> fills nothing, returns { report: [...] } describing every field on the page
//   overwrite -> also replace values already typed in the form (default: only fill empty fields)
// It never clicks Submit.
function sahayakAutofill(p, opts) {
  opts = opts || {};
  p = Object.assign({}, p || {});
  if (p.address && typeof p.address === 'string') {
    if (!p.pin) {
      const pinM = p.address.match(/\b([1-9]\d{5})\b/);
      if (pinM) p.pin = pinM[1];
    }
    if (!p.state) {
      const stM = p.address.match(/(?:State|State\/UT)\s*[:\-]?\s*([A-Za-z ]+?)(?:,|$|\n)/i);
      if (stM && stM[1]) p.state = stM[1].trim();
      else {
        const STATES = ['Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh', 'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka', 'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu', 'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal', 'Delhi', 'Chandigarh', 'Puducherry', 'Jammu and Kashmir', 'Ladakh'];
        for (const st of STATES) {
          if (new RegExp('\\b' + st + '\\b', 'i').test(p.address)) { p.state = st; break; }
        }
      }
    }
    if (!p.district) {
      const distM = p.address.match(/(?:District|Distric|Dist)\s*[:\-]?\s*([A-Za-z ]+?)(?:,|$|\n)/i);
      if (distM && distM[1]) p.district = distM[1].trim();
    }
    if (!p.city) {
      const vtcM = p.address.match(/(?:Village|VTC|Town|City)\s*[:\-]?\s*([A-Za-z ]+?)(?:,|$|\n)/i);
      const poM = p.address.match(/(?:Post|PO)\s*[:\-]?\s*([A-Za-z ]+?)(?:,|$|\n)/i);
      const talukaM = p.address.match(/(?:Taluka|Tehsil|Sub District|Sub Disrict)\s*[:\-]?\s*([A-Za-z ]+?)(?:,|$|\n)/i);
      if (vtcM && vtcM[1]) p.city = vtcM[1].trim();
      else if (poM && poM[1]) p.city = poM[1].trim();
      else if (talukaM && talukaM[1]) p.city = talukaM[1].trim();
    }
  }
  const dryRun = !!opts.dryRun, overwrite = !!opts.overwrite;
  const norm = (s) => (s || '').replace(/([a-z])([A-Z])/g, '$1 $2').toLowerCase().replace(/[^a-z0-9\u0900-\u097f ]+/g, ' ').replace(/\s+/g, ' ').trim();
  const has = (str, term) => new RegExp('(^| )' + term + '( |$)').test(str);
  const hasAny = (str, arr) => arr.some((t) => has(str, t));
  const digits = (s) => (s || '').replace(/\D/g, '');

  const NOT_PERSON = ['father', 'mother', 'spouse', 'husband', 'wife', 'guardian', 'parent', 'user', 'username', 'login', 'school', 'college', 'institution', 'institute', 'university', 'company', 'bank', 'branch', 'board', 'nominee', 'account', 'file', 'document', 'district', 'state', 'city', 'village', 'post', 'office', 'relation', 'witness', 'mobile', 'email', 'phone'];
  const OCC = ['occupation', 'mobile', 'phone', 'income', 'education', 'aadhaar', 'aadhar', 'email', 'age', 'profession', 'qualification', 'pan'];
  const RULES = [
    { key: 'aadhaar', label: 'Aadhaar number', terms: ['aadhaar', 'aadhar', 'aadhaar number', 'aadhar number', 'aadhaar no', 'aadhar no', 'uid', 'uidai', 'आधार'], exclude: ['name', 'virtual', 'vid', 'father', 'mother'] },
    { key: 'pan', label: 'PAN', terms: ['pan', 'pan number', 'pan no', 'permanent account number'], exclude: ['name', 'aadhaar', 'aadhar', 'father', 'mother'] },
    { key: 'mobile', label: 'Mobile number', terms: ['mobile', 'mobile number', 'mobile no', 'phone', 'phone number', 'phone no', 'contact number', 'contact no', 'cell', 'मोबाइल'], exclude: ['father', 'mother', 'guardian', 'parent', 'alternate', 'alternative', 'emergency', 'landline', 'office', 'otp', 'name'] },
    { key: 'email', label: 'Email', terms: ['email', 'e mail', 'email id', 'email address', 'mail id'], exclude: ['father', 'mother', 'alternate', 'alternative', 'otp'] },
    { key: 'pin', label: 'PIN code', terms: ['pin', 'pincode', 'pin code', 'postal code', 'zip', 'zip code', 'पिन'], exclude: ['father', 'mother'] },
    { key: 'dob', label: 'Date of birth', terms: ['dob', 'date of birth', 'birth date', 'birthdate', 'birth day', 'जन्म तिथि'], exclude: ['father', 'mother', 'spouse', 'guardian', 'place'] },
    { key: 'gender', label: 'Gender', terms: ['gender', 'sex', 'लिंग'], exclude: [] },
    { key: 'fatherName', label: "Father's name", terms: ['father', 'father name', 'fathers name', 'father s name', 'name of father', 'father husband name', 'father or husband name', 'father guardian name'], exclude: OCC },
    { key: 'motherName', label: "Mother's name", terms: ['mother', 'mother name', 'mothers name', 'mother s name', 'name of mother'], exclude: OCC },
    { key: 'address', label: 'Address', terms: ['address', 'residential address', 'permanent address', 'correspondence address', 'present address', 'street', 'पता'], exclude: ['email', 'mail', 'ip', 'web', 'url', 'bank', 'office', 'proof', 'type', 'line 2', 'line2', 'address 2'] },
    { key: 'city', label: 'City / village', terms: ['city', 'village', 'town', 'city village', 'city town', 'locality'], exclude: ['district', 'state', 'father', 'mother', 'bank', 'office', 'birth'] },
    { key: 'district', label: 'District', terms: ['district', 'जिला'], exclude: ['birth', 'office', 'bank'] },
    { key: 'state', label: 'State', terms: ['state', 'province', 'राज्य'], exclude: ['birth', 'office', 'bank'] },
    { key: 'name', label: 'Name', terms: ['name', 'full name', 'candidate name', 'applicant name', 'name of applicant', 'name of candidate', 'student name', 'your name', 'नाम'], exclude: NOT_PERSON }
  ];
  const MANUAL = ['captcha', 'otp', 'one time password', 'security code', 'verification code', 'कैप्चा'];
  const GENDER_WORDS = {
    Male: ['male', 'm', 'man', 'boy', 'पुरुष'],
    Female: ['female', 'f', 'woman', 'girl', 'महिला'],
    Other: ['other', 'others', 'transgender', 'third gender', 'o', 't']
  };

  // ---------- reading the field's label ----------
  const describe = (el) => {
    const bits = [el.name, el.id, el.placeholder, el.getAttribute('aria-label'), el.title];
    if (el.labels) for (const l of el.labels) bits.push(l.textContent);
    const by = el.getAttribute('aria-labelledby');
    if (by) by.split(/\s+/).forEach((id) => { const n = document.getElementById(id); if (n) bits.push(n.textContent); });
    return norm(bits.filter(Boolean).join(' '));
  };
  // Many government forms use table cells instead of <label>: read the text next to the field.
  const nearby = (el) => {
    const bits = [];
    const cell = el.closest('td, th');
    if (cell) {
      if (cell.previousElementSibling) bits.push(cell.previousElementSibling.textContent);
      else if (cell.parentElement && cell.parentElement.previousElementSibling) bits.push(cell.parentElement.previousElementSibling.textContent);
    }
    const par = el.parentElement;
    if (par && par.previousElementSibling) bits.push(par.previousElementSibling.textContent);
    let n = el.previousSibling;
    while (n && n.nodeType === 3 && !n.textContent.trim()) n = n.previousSibling;
    if (n) bits.push(n.textContent);
    const grp = el.closest('.form-group, .mb-3, .field, .row, li, p, div');
    if (grp) { const lab = grp.querySelector('label'); if (lab && !lab.contains(el)) bits.push(lab.textContent); }
    return norm(bits.map((b) => (b || '').slice(0, 60)).join(' '));
  };
  const visible = (el) => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
  const findRule = (desc) => (desc ? RULES.find((r) => hasAny(desc, r.terms) && !hasAny(desc, r.exclude || [])) : null);

  // ---------- setting values ----------
  const fire = (el, names) => names.forEach((n) => el.dispatchEvent(new Event(n, { bubbles: true })));
  const setText = (el, v) => {
    const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, v);
    fire(el, ['input', 'change', 'blur']);
  };
  const mark = (el) => { el.style.outline = '2px solid #4F46E5'; el.style.outlineOffset = '1px'; el.title = 'Filled by Sahayak. Please check.'; };
  const fmtDate = (el, iso) => {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(iso || '')) return '';
    const [y, m, d] = iso.split('-');
    if (el.type === 'date') return iso;
    const ph = (el.placeholder || '').toLowerCase();
    const sep = ph.includes('-') ? '-' : ph.includes('.') ? '.' : '/';
    if (/^y{2,4}[-\/.]/.test(ph)) return [y, m, d].join(sep);
    if (/^m{1,2}[-\/.]/.test(ph)) return [m, d, y].join(sep);
    return [d, m, y].join(sep);
  };
  const realOptions = (sel) => Array.from(sel.options).filter((o) => o.value !== '' && !/^\s*(--|select|choose|please|none)/i.test(o.textContent));
  const selectEmpty = (sel) => { const o = sel.options[sel.selectedIndex]; return !o || !sel.value || /^\s*(--|select|choose|please)/i.test(o.textContent); };
  const pickText = (sel, wanted) => {
    const w = norm(wanted); if (!w) return null;
    const opts = realOptions(sel);
    return opts.find((o) => norm(o.textContent) === w || norm(o.value) === w) ||
      opts.find((o) => { const t = norm(o.textContent); return t.length >= 3 && (t.startsWith(w) || w.startsWith(t)); }) || null;
  };
  const pickGender = (opts, g) => {
    const words = GENDER_WORDS[g] || [];
    return opts.find((o) => words.includes(norm(o.textContent)) || words.includes(norm(o.value))) || null;
  };
  const pickDobPart = (sel, iso) => {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(iso || '')) return null;
    const [y, m, d] = iso.split('-'); const opts = realOptions(sel);
    const MON = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];
    const num = (o) => parseInt(o.value, 10) || parseInt(o.textContent, 10);
    if (opts.some((o) => /^(19|20)\d\d$/.test(o.textContent.trim()))) return opts.find((o) => num(o) === +y) || null;           // year list
    if (opts.length >= 12 && opts.length <= 13) return opts.find((o) => num(o) === +m || norm(o.textContent).slice(0, 3) === MON[+m - 1]) || null; // month list
    if (opts.length >= 28 && opts.length <= 32) return opts.find((o) => num(o) === +d) || null;                                 // day list
    return null;
  };
  const textFor = (key, el, desc) => {
    switch (key) {
      case 'aadhaar': { const d = digits(p.aadhaar); return !d ? '' : el.maxLength === 14 ? `${d.slice(0, 4)} ${d.slice(4, 8)} ${d.slice(8)}` : d; }
      case 'pan': return (p.pan || '').toUpperCase().replace(/\s/g, '');
      case 'mobile': { const d = digits(p.mobile); return d.length > 10 ? d.slice(-10) : d; }
      case 'pin': return digits(p.pin);
      case 'dob': return fmtDate(el, p.dob);
      case 'address': return (p.address || '').replace(/\s+/g, ' ').trim();
      case 'name': {
        const parts = (p.fullName || '').trim().split(/\s+/).filter(Boolean);
        if (has(desc, 'first') || has(desc, 'given')) return parts[0] || '';
        if (has(desc, 'last') || has(desc, 'surname') || has(desc, 'family')) return parts.length > 1 ? parts[parts.length - 1] : '';
        if (has(desc, 'middle')) return parts.length > 2 ? parts.slice(1, -1).join(' ') : '';
        return parts.join(' ');
      }
      default: return p[key] || '';
    }
  };
  const PKEY = { name: 'fullName' };

  // ---------- main loop ----------
  const filled = [], skipped = [], noOption = [], noValue = [], report = [], aadhaarBoxes = [], doneRadios = {};
  document.querySelectorAll('input, textarea, select').forEach((el) => {
    const tag = el.tagName.toLowerCase(), type = (el.type || tag).toLowerCase();
    if (['hidden', 'submit', 'button', 'reset', 'image', 'color', 'range'].includes(type) || !visible(el)) return;
    const prim = describe(el);
    const manual = hasAny(prim, MANUAL);
    let rule = manual ? null : findRule(prim);
    let desc = prim;
    if (!rule && !manual) { const nb = nearby(el); rule = findRule(nb); if (rule) desc = prim + ' ' + nb; }
    if (!rule && !manual) { if (type === 'email') rule = RULES.find((r) => r.key === 'email'); else if (type === 'tel') rule = RULES.find((r) => r.key === 'mobile'); }
    const label = (prim || nearby(el) || '(no label)').slice(0, 50);
    const rep = (state, extra) => report.push(Object.assign({ state, rule: rule ? rule.label : null, label, kind: tag === 'select' ? 'dropdown' : type }, extra || {}));

    if (manual) { if (dryRun) rep('manual'); return; }
    if (['checkbox', 'file', 'password'].includes(type)) { if (dryRun) rep('unsupported'); return; }

    // gender radio buttons: decided by the option labels, not by the field name
    if (type === 'radio') {
      const gname = el.name || el.id;
      if (doneRadios[gname]) return; doneRadios[gname] = true;
      const group = Array.from(document.querySelectorAll('input[type=radio]')).filter((r) => (r.name || r.id) === gname);
      const opts = group.map((r) => ({ el: r, textContent: ((r.labels && r.labels[0] && r.labels[0].textContent) || (r.nextSibling && r.nextSibling.textContent) || '') + ' ', value: r.value }));
      const isGender = pickGender(opts, 'Male') && pickGender(opts, 'Female');
      if (!isGender) { if (dryRun) report.push({ state: 'unknown', rule: null, label: gname, kind: 'radio' }); return; }
      const already = group.some((r) => r.checked);
      const target = pickGender(opts, p.gender);
      if (dryRun) { report.push({ state: already ? 'filled' : !p.gender ? 'no_value' : target ? 'will_fill' : 'no_option', rule: 'Gender', label: gname, kind: 'radio' }); return; }
      if (!p.gender) { noValue.push('Gender'); return; }
      if (already && !overwrite) { skipped.push('Gender'); return; }
      if (!target) { noOption.push('Gender'); return; }
      target.el.click(); mark(target.el.parentElement || target.el); filled.push('Gender'); return;
    }

    if (!rule) { if (dryRun) rep(el.disabled || el.readOnly ? 'readonly' : 'unknown'); return; }
    const isDobReadonly = rule.key === 'dob' && el.readOnly && tag !== 'select';   // date pickers are usually read-only boxes
    if ((el.disabled || (el.readOnly && !isDobReadonly))) { if (dryRun) rep('readonly'); return; }

    // dropdowns
    if (tag === 'select') {
      let opt = null;
      if (rule.key === 'gender') opt = pickGender(realOptions(el), p.gender);
      else if (rule.key === 'dob') opt = pickDobPart(el, p.dob);
      else if (['state', 'district', 'city'].includes(rule.key)) opt = pickText(el, p[rule.key]);
      else { if (dryRun) rep('unsupported'); return; }
      const have = rule.key === 'dob' ? !!p.dob : rule.key === 'gender' ? !!p.gender : !!p[rule.key];
      if (dryRun) { rep(selectEmpty(el) || overwrite ? (!have ? 'no_value' : opt ? 'will_fill' : 'no_option') : 'filled'); return; }
      if (!have) { noValue.push(rule.label); return; }
      if (!selectEmpty(el) && !overwrite) { skipped.push(rule.label); return; }
      if (!opt) { noOption.push(rule.label + (rule.key === 'district' ? ' (choose State first, then press Fill again)' : '')); return; }
      el.value = opt.value; fire(el, ['input', 'change']); mark(el); filled.push(rule.label); return;
    }

    // text-like boxes
    const pk = PKEY[rule.key] || rule.key;
    const hasData = rule.key === 'gender' ? false : !!(rule.key === 'dob' ? p.dob : p[pk]);
    if (rule.key === 'gender') { if (dryRun) rep('unknown'); return; }
    if (rule.key === 'aadhaar' && el.maxLength === 4) { aadhaarBoxes.push(el); return; }   // Aadhaar split into 3 boxes of 4
    if (dryRun) { rep(!hasData ? 'no_value' : el.value && el.value.trim() && !overwrite ? 'filled' : 'will_fill', isDobReadonly ? { note: 'read-only date box (will try)' } : {}); return; }
    if (!hasData) { noValue.push(rule.label); return; }
    const value = textFor(rule.key, el, desc);
    if (!value) return;
    if (el.value && el.value.trim() && !overwrite) { skipped.push(rule.label); return; }
    setText(el, String(value)); mark(el); filled.push(rule.label);
  });

  if (dryRun) {
    if (aadhaarBoxes.length === 3) report.push({ state: digits(p.aadhaar).length === 12 ? 'will_fill' : 'no_value', rule: 'Aadhaar number', label: 'Aadhaar in 3 boxes', kind: 'text' });
    return { report };
  }
  if (aadhaarBoxes.length === 3 && digits(p.aadhaar).length === 12 && (overwrite || aadhaarBoxes.every((b) => !b.value))) {
    const d = digits(p.aadhaar); aadhaarBoxes.forEach((b, i) => { setText(b, d.slice(i * 4, i * 4 + 4)); mark(b); }); filled.push('Aadhaar number');
  }
  return { filled, skipped, noOption, noValue };
}
if (typeof module !== 'undefined' && module.exports) module.exports = sahayakAutofill;
