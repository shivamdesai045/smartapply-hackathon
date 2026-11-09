const API_BASE = import.meta.env.VITE_API_BASE ?? "";

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

  const controller = new AbortController();
  const cancel = () => controller.abort();
  options.signal?.addEventListener("abort", cancel, { once: true });
  if (options.signal?.aborted) controller.abort();
  const timer = setTimeout(cancel, 230000);
  try {
    const res = await fetch(url, { ...opts, signal: controller.signal });
    const body = await res.json().catch(error => {
      if (error.name === "AbortError") throw error;
      if (res.ok) throw error;
      return {};
    });
    if (!res.ok) {
      if (res.status === 401 && body.code === "LOGIN_REQUIRED") handleLoginRequired(body.error);
      const err = new Error(body.error || `Request failed with status ${res.status}`);
      err.status = res.status;
      err.code = body.code;
      throw err;
    }
    return body;
  } catch (error) {
    if (error.name === "AbortError" && !options.signal?.aborted) {
      throw new Error("Document processing timed out. Please try one clear image or a two-page PDF.");
    }
    throw error;
  } finally {
    clearTimeout(timer);
    options.signal?.removeEventListener("abort", cancel);
  }
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

// Serialize document reads on this memory-limited CPU; failed jobs never stall the queue.
const waitingDocuments = [];
let activeDocument = null;
function updateQueuePositions() {
  waitingDocuments.forEach((entry, i) => entry.onProgress?.(`Queued — ${i + (activeDocument ? 1 : 0)} document(s) ahead`));
}
function runNextDocument() {
  if (activeDocument || !waitingDocuments.length) return;
  const entry = waitingDocuments.shift();
  activeDocument = entry;
  entry.onProgress?.("Reading document...");
  updateQueuePositions();
  const started = Date.now();
  const ticker = setInterval(() => entry.onProgress?.(`Reading document — ${Math.floor((Date.now() - started) / 1000)}s`), 1000);
  Promise.resolve().then(entry.task).then(entry.resolve, entry.reject).finally(() => {
    clearInterval(ticker);
    entry.signal?.removeEventListener("abort", entry.cancel);
    activeDocument = null;
    runNextDocument();
    updateQueuePositions();
  });
}
function queueDocument(task, onProgress, signal) {
  if (signal?.aborted) return Promise.reject(new DOMException("Cancelled", "AbortError"));
  return new Promise((resolve, reject) => {
    const entry = { task, onProgress, signal, resolve, reject };
    entry.cancel = () => {
      const index = waitingDocuments.indexOf(entry);
      if (index < 0) return; // Active requests observe the same signal in request().
      waitingDocuments.splice(index, 1);
      signal.removeEventListener("abort", entry.cancel);
      reject(new DOMException("Cancelled", "AbortError"));
      updateQueuePositions();
    };
    signal?.addEventListener("abort", entry.cancel, { once: true });
    waitingDocuments.push(entry);
    onProgress?.(activeDocument ? `Queued — ${waitingDocuments.length} document(s) ahead` : "Starting document...");
    runNextDocument();
  });
}

async function waitForDocumentJob(accepted, onProgress, signal) {
  if (!accepted.job_id) return accepted; // Compatible with synchronous servers.
  const url = `${API_BASE}/api/ocr/jobs/${encodeURIComponent(accepted.job_id)}`;
  const cancel = () => { request(url, { method: "DELETE" }).catch(() => {}); };
  signal?.addEventListener("abort", cancel, { once: true });
  const delay = () => new Promise((resolve, reject) => {
    const abort = () => {
      clearTimeout(timer);
      signal?.removeEventListener("abort", abort);
      reject(new DOMException("Cancelled", "AbortError"));
    };
    const timer = setTimeout(() => { signal?.removeEventListener("abort", abort); resolve(); }, 1000);
    signal?.addEventListener("abort", abort, { once: true });
    if (signal?.aborted) abort();
  });
  try {
    if (signal?.aborted) { cancel(); throw new DOMException("Cancelled", "AbortError"); }
    const deadline = Date.now() + 15 * 60 * 1000;
    while (Date.now() < deadline) {
      const status = await request(url, { signal });
      if (status.status === "completed") return status.result;
      if (status.status === "failed") {
        const error = new Error(status.result?.error || "Document processing failed.");
        error.code = status.result?.code;
        throw error;
      }
      if (status.status === "cancelled") throw new DOMException("Cancelled", "AbortError");
      onProgress?.(status.status === "queued"
        ? `Queued — ${status.ahead} document(s) ahead`
        : `Reading document — ${status.processing_seconds ?? status.elapsed_seconds}s${status.queue_seconds >= 1 ? ` (waited ${status.queue_seconds}s in queue)` : ""}`);
      await delay();
    }
    cancel();
    throw new Error("Document processing is taking too long. Please check the backend and retry.");
  } finally {
    signal?.removeEventListener("abort", cancel);
  }
}

export async function resumeDocumentJob(service, session_id, variant, requirement, onProgress, signal) {
  const query = new URLSearchParams({ service, session_id, variant, requirement });
  const active = await request(`${API_BASE}/api/ocr/jobs/active?${query}`, { signal });
  return active.job_id ? waitForDocumentJob(active, onProgress, signal) : null;
}

export async function uploadChecklistFile(
  serviceName,
  sessionId,
  variant,
  requirement,
  chosenOption,
  file,
  password = "",
  onProgress,
  signal
) {
  const formData = new FormData();
  formData.append("session_id", sessionId);
  formData.append("variant", variant);
  formData.append("requirement", requirement);
  formData.append("chosen_option", chosenOption);
  for (const selectedFile of (Array.isArray(file) ? file : [file])) {
    formData.append("file", selectedFile);
  }
  if (password) formData.append("password", password);

  const url = `${API_BASE}/api/checklist/${encodeURIComponent(serviceName)}/upload`;
  return queueDocument(() => request(url, {
    method: "POST",
    headers: { Prefer: "respond-async" },
    body: formData,
    signal,
  }), onProgress, signal).then(result => waitForDocumentJob(result, onProgress, signal));
}

export async function rescanDocument(serviceName, sessionId, variant, requirement, password = "", onProgress, signal) {
  const url = `${API_BASE}/api/checklist/${encodeURIComponent(serviceName)}/rescan`;
  return queueDocument(() => request(url, {
    method: "POST",
    signal,
    headers: { "Content-Type": "application/json", Prefer: "respond-async" },
    body: JSON.stringify({
      session_id: sessionId,
      variant,
      requirement,
      ...(password ? { password } : {}),
    }),
  }), onProgress, signal).then(result => waitForDocumentJob(result, onProgress, signal));
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
  { docName, docDob, docAddress, docNumber, docFields }
) {
  const url = `${API_BASE}/api/checklist/${encodeURIComponent(serviceName)}/update-fields`;
  return request(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      variant,
      requirement,
      ...(docFields ? {doc_fields: docFields} : {}),
      doc_name: docFields ? undefined : docName || null,
      doc_dob: docFields ? undefined : docDob || null,
      doc_address: docFields ? undefined : docAddress || null,
      doc_number: docFields ? undefined : docNumber || null,
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

export function fetchReviewedIds(service,variant='adult') {
 return request(`${API_BASE}/api/checklist/${encodeURIComponent(service)}/reviewed-ids`,{
  method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({variant,confirmed:true})
 });
}
