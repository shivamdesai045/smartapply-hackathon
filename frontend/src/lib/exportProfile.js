import "./crypto.js";
import "./profile-io.js";

const ProfileIO = typeof globalThis !== "undefined" && globalThis.SahayakProfileIO
  ? globalThis.SahayakProfileIO
  : (typeof window !== "undefined" ? window.SahayakProfileIO : null);

const INDIAN_STATES = [
  "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat",
  "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh",
  "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
  "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh",
  "Uttarakhand", "West Bengal", "Delhi", "Chandigarh", "Puducherry", "Jammu and Kashmir", "Ladakh"
];

export function parseIndianAddress(addr) {
  if (!addr || typeof addr !== "string") return {};
  const res = { address: addr.trim(), city: "", district: "", state: "", pin: "" };

  const pinMatch = addr.match(/\b([1-9]\d{5})\b/);
  if (pinMatch) res.pin = pinMatch[1];

  const statePrefixMatch = addr.match(/(?:State|State\/UT)\s*[:\-]?\s*([A-Za-z ]+?)(?:,|$|\n)/i);
  if (statePrefixMatch && statePrefixMatch[1]) {
    res.state = statePrefixMatch[1].trim();
  } else {
    for (const st of INDIAN_STATES) {
      if (new RegExp("\\b" + st + "\\b", "i").test(addr)) {
        res.state = st;
        break;
      }
    }
  }

  const distMatch = addr.match(/(?:District|Distric|Dist)\s*[:\-]?\s*([A-Za-z ]+?)(?:,|$|\n)/i);
  if (distMatch && distMatch[1]) {
    res.district = distMatch[1].trim();
  }

  const vtcMatch = addr.match(/(?:Village|VTC|Town|City)\s*[:\-]?\s*([A-Za-z ]+?)(?:,|$|\n)/i);
  const poMatch = addr.match(/(?:Post|PO)\s*[:\-]?\s*([A-Za-z ]+?)(?:,|$|\n)/i);
  const talukaMatch = addr.match(/(?:Taluka|Tehsil|Sub District|Sub Disrict)\s*[:\-]?\s*([A-Za-z ]+?)(?:,|$|\n)/i);

  if (vtcMatch && vtcMatch[1]) {
    res.city = vtcMatch[1].trim();
  } else if (poMatch && poMatch[1]) {
    res.city = poMatch[1].trim();
  } else if (talukaMatch && talukaMatch[1]) {
    res.city = talukaMatch[1].trim();
  }

  if ((!res.city || !res.district) && res.state) {
    const parts = addr.split(/[,;\n]+/).map((p) => p.trim().replace(/\b[1-9]\d{5}\b/, "").trim()).filter(Boolean);
    const stateIdx = parts.findIndex((p) => new RegExp("\\b" + res.state + "\\b", "i").test(p));
    if (stateIdx > 0) {
      const candidate = parts[stateIdx - 1];
      if (!/street|road|nagar|colony|flat|house|block|sector|lane|floor/i.test(candidate)) {
        if (!res.district) res.district = candidate;
        if (!res.city) res.city = candidate;
      }
    }
  }

  return res;
}

/**
 * Extracts a candidate corrected profile from verification report data.
 * Adheres strictly to the invariant: Aadhaar and PAN are NEVER included.
 */
export function deriveCorrectedProfile(report) {
  if (!report) return {};
  const { documents = [], issues = [] } = report;

  let fullName = "";
  let dob = "";
  let address = "";
  let fatherName = "";
  let motherName = "";
  let mobile = "";
  let email = "";
  let state = "";
  let district = "";
  let city = "";
  let pin = "";

  const docMap = {};
  documents.forEach((d) => {
    if (d.chosenOption) {
      docMap[d.chosenOption] = d;
    }
  });

  // Base values from first available document
  for (const doc of documents) {
    if (doc.docName && !fullName) fullName = doc.docName.trim();
    if (doc.docDob && !dob) dob = doc.docDob.trim();
    if (doc.docAddress && !address) address = doc.docAddress.trim();
    if (!fatherName && (doc.fatherName || doc.docFatherName || doc.docMeta?.father_name)) {
      fatherName = (doc.fatherName || doc.docFatherName || doc.docMeta?.father_name).trim();
    }
    if (!motherName && (doc.motherName || doc.docMotherName || doc.docMeta?.mother_name)) {
      motherName = (doc.motherName || doc.docMotherName || doc.docMeta?.mother_name).trim();
    }
  }

  if (!fatherName && address) {
    const parentMatch = address.match(/(?:S\/O|C\/O|Father(?:'s)?\s*Name)\s*[:\-]?\s*([A-Za-z ]+?)(?:,|$|\n)/i);
    if (parentMatch && parentMatch[1]) {
      fatherName = parentMatch[1].trim();
    }
  }

  // Override with user decisions on mismatches
  issues.forEach((issue) => {
    const field = (issue.field || "").toLowerCase();
    const [docA, docB] = issue.documents || [];
    let authoritativeDoc = null;

    if (issue.decision === "doc_a_correct") authoritativeDoc = docMap[docA];
    else if (issue.decision === "doc_b_correct") authoritativeDoc = docMap[docB];

    if (authoritativeDoc) {
      if (field === "name" && authoritativeDoc.docName) fullName = authoritativeDoc.docName.trim();
      if (field === "dob" && authoritativeDoc.docDob) dob = authoritativeDoc.docDob.trim();
      if (field === "address" && authoritativeDoc.docAddress) address = authoritativeDoc.docAddress.trim();
    }
  });

  // Automatically parse sub-fields (City, District, State, PIN) from the address string
  if (address) {
    const parsed = parseIndianAddress(address);
    if (parsed.city) city = parsed.city;
    if (parsed.district) district = parsed.district;
    if (parsed.state) state = parsed.state;
    if (parsed.pin) pin = parsed.pin;
  }

  const profile = {
    fullName,
    fatherName,
    motherName,
    dob,
    gender: "",
    mobile,
    email,
    address,
    city,
    district,
    state,
    pin
  };

  const cleanProfile = {};
  Object.keys(profile).forEach((k) => {
    if (profile[k]) cleanProfile[k] = profile[k];
  });

  return cleanProfile;
}

/**
 * Builds export JSON text using SahayakProfileIO.buildExport.
 * Strictly guarantees Aadhaar and PAN are excluded.
 */
export async function createExportFile(profile, passphrase) {
  const io = ProfileIO || (typeof globalThis !== "undefined" ? globalThis.SahayakProfileIO : null);
  if (!io) {
    throw new Error("SahayakProfileIO is not loaded.");
  }
  const cleanPass = passphrase && passphrase.trim().length > 0 ? passphrase.trim() : null;
  if (cleanPass && cleanPass.length < 8) {
    throw new Error("File passphrase must be at least 8 characters long (or left empty for unprotected file).");
  }
  return io.buildExport(profile, cleanPass);
}

/**
 * Triggers browser download of sahayak-details.json.
 */
export function downloadDetailsJson(jsonText, filename = "sahayak-details.json") {
  const blob = new Blob([jsonText], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

