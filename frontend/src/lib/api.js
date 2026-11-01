const API_BASE = "http://localhost:5000";

function handleLoginRequired(msg) {
  if (typeof window !== "undefined") {
    window.dispatchEvent(
      new CustomEvent("sahayak:login_required", {
        detail: {
          message: msg || "Please log in to continue.",
          nextPath: window.location.pathname + window.location.search,
        },
      })
    );
  }
}

async function request(url, options = {}) {
  const opts = {
    ...options,
    credentials: "include",
    headers: {
      ...(options.headers || {}),
    },
  };

  const res = await fetch(url, opts);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    if (res.status === 401 && body.code === "LOGIN_REQUIRED") {
      handleLoginRequired(body.error);
    }
    const err = new Error(body.error || `Request failed with status ${res.status}`);
    err.status = res.status;
    err.code = body.code;
    throw err;
  }
  return res.json();
}

export async function fetchSession() {
  return request(`${API_BASE}/api/session`);
}

export async function deleteSessionData(sessionId) {
  return request(`${API_BASE}/api/session/data`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
}

export async function fetchServices() {
  return request(`${API_BASE}/api/services`);
}

export async function fetchChecklistVariants(serviceName) {
  return request(`${API_BASE}/api/checklist/${encodeURIComponent(serviceName)}/variants`);
}

export async function fetchChecklist(serviceName, variant = "adult") {
  return request(`${API_BASE}/api/checklist/${encodeURIComponent(serviceName)}?variant=${encodeURIComponent(variant)}`);
}

export async function fetchChecklistStatus(serviceName, sessionId, variant) {
  const url = `${API_BASE}/api/checklist/${encodeURIComponent(
    serviceName
  )}/status?session_id=${encodeURIComponent(sessionId)}&variant=${encodeURIComponent(
    variant
  )}`;
  return request(url);
}

export async function uploadChecklistFile(
  serviceName,
  sessionId,
  variant,
  requirement,
  chosenOption,
  file
) {
  const formData = new FormData();
  formData.append("session_id", sessionId);
  formData.append("variant", variant);
  formData.append("requirement", requirement);
  formData.append("chosen_option", chosenOption);
  formData.append("file", file);

  const url = `${API_BASE}/api/checklist/${encodeURIComponent(serviceName)}/upload`;
  return request(url, {
    method: "POST",
    body: formData,
  });
}

export async function rescanDocument(serviceName, sessionId, variant, requirement) {
  const url = `${API_BASE}/api/checklist/${encodeURIComponent(serviceName)}/rescan`;
  return request(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      variant,
      requirement,
    }),
  });
}

export async function skipRequirement(serviceName, sessionId, variant, requirement, skipped = true) {
  const url = `${API_BASE}/api/checklist/${encodeURIComponent(serviceName)}/skip`;
  return request(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      variant,
      requirement,
      skipped,
    }),
  });
}

export async function updateChecklistFields(
  serviceName,
  sessionId,
  variant,
  requirement,
  { docName, docDob, docAddress, docNumber }
) {
  const url = `${API_BASE}/api/checklist/${encodeURIComponent(serviceName)}/update-fields`;
  return request(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      variant,
      requirement,
      doc_name: docName || null,
      doc_dob: docDob || null,
      doc_address: docAddress || null,
      doc_number: docNumber || null,
    }),
  });
}

export function getChecklistFileUrl(serviceName, sessionId, variant, requirement, download = false) {
  const dlParam = download ? "&download=1" : "";
  return `${API_BASE}/api/checklist/${encodeURIComponent(
    serviceName
  )}/file?session_id=${encodeURIComponent(sessionId)}&variant=${encodeURIComponent(
    variant
  )}&requirement=${encodeURIComponent(requirement)}${dlParam}`;
}

export async function fetchFileBlob(fileUrl) {
  const res = await fetch(fileUrl, { credentials: "include" });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    if (res.status === 401 && body.code === "LOGIN_REQUIRED") {
      handleLoginRequired(body.error);
    }
    throw new Error(body.error || "Failed to load document file");
  }
  return res.blob();
}

export async function fetchChecklistMismatches(serviceName, sessionId, variant) {
  const url = `${API_BASE}/api/checklist/${encodeURIComponent(
    serviceName
  )}/mismatches?session_id=${encodeURIComponent(sessionId)}&variant=${encodeURIComponent(
    variant
  )}`;
  return request(url);
}

export async function postMismatchDecision(
  serviceName,
  sessionId,
  variant,
  field,
  documents,
  decision,
  incorrectDocument = null
) {
  const url = `${API_BASE}/api/checklist/${encodeURIComponent(serviceName)}/mismatch-decision`;
  return request(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, variant, field, documents, decision, incorrect_document: incorrectDocument }),
  });
}

export async function fetchChecklistDiagnostics(serviceName, sessionId, variant) {
  const url = `${API_BASE}/api/checklist/${encodeURIComponent(
    serviceName
  )}/diagnostics?session_id=${encodeURIComponent(sessionId)}&variant=${encodeURIComponent(
    variant
  )}&dev=true`;
  return request(url, {
    headers: { "X-Dev-Mode": "true" },
  });
}

export async function fetchCorrectionGuidancePair(docA, docB, field) {
  const url = `${API_BASE}/api/correction-guidance-pair?doc_a=${encodeURIComponent(
    docA
  )}&doc_b=${encodeURIComponent(docB)}&field=${encodeURIComponent(field)}`;
  return request(url);
}

export async function translateText(text, targetLanguage) {
  const url = `${API_BASE}/api/translate`;
  return request(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, target_language: targetLanguage }),
  });
}

// =======================
// MY DOCUMENTS & CORRECTION TRACKING
// =======================

export async function fetchMyDocuments() {
  return request(`${API_BASE}/api/documents`);
}

export async function deleteDocument(docId) {
  return request(`${API_BASE}/api/documents/${docId}`, {
    method: "DELETE",
  });
}

export async function deleteAllDocuments() {
  return request(`${API_BASE}/api/documents`, {
    method: "DELETE",
  });
}

export async function fetchCorrectionSteps(serviceName, variant = "adult") {
  const url = `${API_BASE}/api/checklist/${encodeURIComponent(
    serviceName
  )}/correction-steps?variant=${encodeURIComponent(variant)}`;
  return request(url);
}

export async function saveCorrectionStep(serviceName, variant, issueKey, stepIndex, completed = true) {
  const url = `${API_BASE}/api/checklist/${encodeURIComponent(serviceName)}/correction-steps`;
  return request(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      variant,
      issue_key: issueKey,
      step_index: stepIndex,
      completed,
    }),
  });
}

export async function fetchVerificationReport(serviceName, variant = "adult") {
  const url = `${API_BASE}/api/report/${encodeURIComponent(
    serviceName
  )}?variant=${encodeURIComponent(variant)}`;
  return request(url);
}

export async function sendChatMessage(payload) {
  const url = `${API_BASE}/api/chat`;
  return request(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

// =======================
// AUTHENTICATION
// =======================

export async function registerUser(data) {
  const url = `${API_BASE}/api/auth/register`;
  return request(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function loginUser(email, password) {
  const url = `${API_BASE}/api/auth/login`;
  return request(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

export async function logoutUser() {
  const url = `${API_BASE}/api/auth/logout`;
  return request(url, {
    method: "POST",
  });
}

export async function fetchMe() {
  const url = `${API_BASE}/api/auth/me`;
  try {
    const res = await fetch(url, { credentials: "include" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}
