/*
 * Sahayak OCR review UI compatibility repair.
 * Run from SmartApply-frontend/SmartApply-frontend (next to package.json).
 * Doesn't change backend, uploaded files, or auto-comparison rules.
 */
const fs = require('fs');
const path = require('path');

const target = path.resolve('src/pages/Checklist.jsx');
const pkg = path.resolve('package.json');
if (!fs.existsSync(pkg) || !fs.existsSync(target)) {
  throw new Error('Run from the FRONTEND folder containing package.json and src/pages/Checklist.jsx');
}
let code = fs.readFileSync(target, 'utf8');
const marker = 'SAHAYAK_OCR_CANDIDATE_REVIEW_V1';
if (code.includes(marker)) {
  console.log('OCR review compatibility fix already installed. No changes made.');
  process.exit(0);
}

function applyOnce(regex, replacement, purpose) {
  const matches = [...code.matchAll(new RegExp(regex.source, regex.flags.includes('g') ? regex.flags : regex.flags + 'g'))];
  if (matches.length !== 1) {
    throw new Error(`${purpose}: expected exactly one code match, found ${matches.length}. No files changed.`);
  }
  code = code.replace(regex, replacement);
}

// Candidate OCR values are intentionally excluded from top-level DB fields by
// smartapply_docai.bridge when they require human confirmation. Read structured
// fields ONLY for preview/edit; never write them to the database automatically.
applyOnce(
  /  const ocrInfo = lastOcr \|\| \(reqData\.uploaded \? \{[\s\S]*?\} : null\);\r?\n\s*const foundNothing = [^\r\n]+;/,
  `  // SAHAYAK_OCR_CANDIDATE_REVIEW_V1: display provisional fields without silently confirming them.\n  const ocrRaw = lastOcr || (reqData.uploaded ? {\n    name: reqData.docName,\n    dob: reqData.docDob,\n    address: reqData.docAddress,\n    doc_number: reqData.docNumber ? { type: "ID", number: reqData.docNumber } : null,\n  } : null);\n  const candidateNumber = ocrRaw?.fields?.doc_number;\n  const ocrInfo = ocrRaw ? {\n    ...ocrRaw,\n    name: ocrRaw.name || ocrRaw.fields?.name?.value || null,\n    dob: ocrRaw.dob || ocrRaw.fields?.dob?.value || null,\n    address: ocrRaw.address || ocrRaw.fields?.address?.value || null,\n    doc_number: (ocrRaw.doc_number && ocrRaw.doc_number.number)\n      ? ocrRaw.doc_number\n      : candidateNumber?.number\n        ? { type: candidateNumber.type || "ID", number: candidateNumber.number }\n        : null,\n  } : null;\n  const foundNothing = Boolean(ocrInfo && !ocrInfo.name && !ocrInfo.dob && !ocrInfo.address && !ocrInfo.doc_number);\n  const reviewFields = Array.isArray(ocrRaw?.needsReview) ? ocrRaw.needsReview : [];\n  const ocrWarnings = Array.isArray(ocrRaw?.warnings) ? ocrRaw.warnings : [];\n  const engineMissing = ocrWarnings.some(w => /tesseract_missing|TesseractNotFoundError|TesseractError/i.test(String(w)));\n  const timeBudgetExceeded = ocrWarnings.some(w => /time_budget_exceeded/i.test(String(w)));`,
  'OCR display normalization'
);

// Show meaningful failures rather than reporting a false "cannot read" when
// engine isn't installed or time budget is exhausted.
applyOnce(
  /\{!notSupported && foundNothing && "Couldn't automatically read identity details from this document\."\}/,
  `{!notSupported && foundNothing && (\n              engineMissing\n                ? "OCR is unavailable: Tesseract is missing or failed. Check the backend installation."\n                : timeBudgetExceeded\n                  ? "OCR did not finish within its time limit. Try a clearer, cropped photo or rescan."\n                  : "No usable identity fields were found. Check the image quality and selected document type, then rescan."\n            )}`,
  'OCR empty/error message'
);

// Indicate that these fields are provisional, not confirmed. No special styling libs.
applyOnce(
  /\{!notSupported && !foundNothing && \(\s*<>\s*<span className="font-semibold text-brand-700 dark:text-brand-400">OCR Extracted: <\/span>/,
  `{!notSupported && !foundNothing && (\n              <>\n                <span className="font-semibold text-brand-700 dark:text-brand-400">\n                  {reviewFields.length ? "OCR Candidate — Confirm before matching: " : "OCR Extracted: "}\n                </span>`,
  'OCR provisional label'
);

// Prepopulate the existing user-editable form with candidate OCR values so a
// user can validate against the Eye preview, then explicitly press Save.
applyOnce(
  /function OcrEditForm\(\{ serviceName, sessionId, variant, requirement, reqData, onSaved \}\) \{\s*const \[name, setName\] = useState\(reqData\.docName \|\| ""\);\s*const \[dob, setDob\] = useState\(reqData\.docDob \|\| ""\);\s*const \[address, setAddress\] = useState\(reqData\.docAddress \|\| ""\);\s*const \[docNumber, setDocNumber\] = useState\(reqData\.docNumber \|\| ""\);/,
  `function OcrEditForm({ serviceName, sessionId, variant, requirement, reqData, initialOcr, onSaved }) {\n  const [name, setName] = useState(initialOcr?.name || reqData.docName || "");\n  const [dob, setDob] = useState(initialOcr?.fields?.dob?.precision === "year" ? "" : (initialOcr?.dob || reqData.docDob || ""));\n  const [address, setAddress] = useState(initialOcr?.address || reqData.docAddress || "");\n  const isAadhaarDocument = /aadhaar|aadhar/i.test(reqData.chosenOption || "");\n  const [docNumber, setDocNumber] = useState(isAadhaarDocument ? "" : (initialOcr?.doc_number?.number || reqData.docNumber || ""));`,
  'OCR edit form initial fields'
);

// Aadhaar is displayed masked; do not persist a manually entered full UID.
applyOnce(
  /docName: name, docDob: dob, docAddress: address, docNumber: docNumber,/,
  'docName: name, docDob: dob, docAddress: address, docNumber: isAadhaarDocument ? "" : docNumber,',
  'Privacy-safe Aadhaar save'
);
applyOnce(
  /<input value=\{docNumber\} onChange=\{\(e\) => setDocNumber\(e\.target\.value\)\} placeholder="ID \/ Doc Number"/,
  '<input value={docNumber} disabled={isAadhaarDocument} onChange={(e) => setDocNumber(e.target.value)} placeholder={isAadhaarDocument ? "Aadhaar number not stored" : "ID / Doc Number"}',
  'Privacy-safe Aadhaar editor'
);

applyOnce(
  /requirement=\{reqData\.requirement\} reqData=\{reqData\}\s*onSaved=/,
  'requirement={reqData.requirement} reqData={reqData} initialOcr={ocrInfo}\n            onSaved=',
  'OCR editor wiring'
);

const backup = target + '.before-ocr-review-' + new Date().toISOString().replace(/[:.]/g, '-') + '.bak';
fs.copyFileSync(target, backup);
fs.writeFileSync(target, code, 'utf8');
console.log('OCR candidate review UI fixed.');
console.log('Backup:', path.basename(backup));
console.log('Backend/database/automatic matching untouched.');
console.log('Next: npm.cmd run build');
