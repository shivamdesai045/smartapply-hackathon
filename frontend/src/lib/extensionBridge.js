/**
 * Extension Bridge for direct 1-click sync between Sahayak website and extension.
 * Eliminates the need to download or manually browse JSON files.
 */

// Check if Sahayak extension is installed
export function isExtensionInstalled() {
  if (typeof document === "undefined") return false;
  return document.documentElement.hasAttribute("data-sahayak-extension");
}

// Ping the extension with a fallback timeout
export function pingExtension(timeoutMs = 600) {
  return new Promise((resolve) => {
    if (typeof window === "undefined") return resolve(false);

    if (document.documentElement.hasAttribute("data-sahayak-extension")) {
      return resolve(true);
    }

    let resolved = false;
    const timer = setTimeout(() => {
      if (!resolved) {
        resolved = true;
        window.removeEventListener("message", handler);
        resolve(document.documentElement.hasAttribute("data-sahayak-extension"));
      }
    }, timeoutMs);

    function handler(e) {
      if (e.data && e.data.type === "SAHAYAK_EXT_PONG") {
        if (!resolved) {
          resolved = true;
          clearTimeout(timer);
          window.removeEventListener("message", handler);
          resolve(true);
        }
      }
    }

    window.addEventListener("message", handler);
    window.postMessage({ type: "SAHAYAK_EXT_PING" }, "*");
  });
}

// Send profile directly to extension
export function sendProfileToExtension(profile, timeoutMs = 2500) {
  return new Promise((resolve, reject) => {
    if (typeof window === "undefined") {
      return reject(new Error("Cannot sync outside of a browser window."));
    }

    // Deep clean: Ensure Aadhaar and PAN are never sent
    const cleanProfile = Object.assign({}, profile);
    delete cleanProfile.aadhaar;
    delete cleanProfile.pan;

    let finished = false;
    const timer = setTimeout(() => {
      if (!finished) {
        finished = true;
        window.removeEventListener("message", handler);
        reject(new Error("Sync timed out. Ensure the Sahayak extension is enabled."));
      }
    }, timeoutMs);

    function handler(e) {
      if (e.data && e.data.type === "SAHAYAK_DIRECT_SYNC_RES") {
        if (!finished) {
          finished = true;
          clearTimeout(timer);
          window.removeEventListener("message", handler);
          if (e.data.success) {
            resolve({ success: true });
          } else {
            reject(new Error(e.data.error || "Extension rejected the sync request."));
          }
        }
      }
    }

    window.addEventListener("message", handler);
    window.postMessage({ type: "SAHAYAK_DIRECT_SYNC", profile: cleanProfile }, "*");
  });
}

