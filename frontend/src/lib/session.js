import { fetchSession } from "./api";

const KEY = "sahayak_session_id";
let memorySessionId = null;
let initPromise = null;

export async function initSession() {
  if (memorySessionId) {
    return memorySessionId;
  }

  // Prevent multiple concurrent fetchSession calls on startup
  if (initPromise) {
    return initPromise;
  }

  initPromise = (async () => {
    try {
      const data = await fetchSession();
      if (data && data.sessionId) {
        memorySessionId = data.sessionId;
        localStorage.setItem(KEY, data.sessionId);
        return data.sessionId;
      }
    } catch (err) {
      console.warn("Backend session fetch failed, checking local storage:", err);
    } finally {
      initPromise = null;
    }

    const stored = localStorage.getItem(KEY);
    if (stored) {
      memorySessionId = stored;
      return stored;
    }

    return null;
  })();

  return initPromise;
}

export function getSessionId() {
  if (memorySessionId) {
    return memorySessionId;
  }
  const stored = localStorage.getItem(KEY);
  if (stored) {
    memorySessionId = stored;
    return stored;
  }
  return "";
}

export function setSessionId(id) {
  memorySessionId = id || null;
  if (id) {
    localStorage.setItem(KEY, id);
  } else {
    localStorage.removeItem(KEY);
  }
}

export function clearSession() {
  memorySessionId = null;
  localStorage.removeItem(KEY);
}
