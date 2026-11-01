// Sahayak content script - bridges communication between web pages and the extension
(() => {
  // Signal presence by attribute on html root and postMessage
  function announce() {
    try {
      document.documentElement.setAttribute('data-sahayak-extension', '0.2.0');
      window.postMessage({ type: 'SAHAYAK_EXT_PONG', installed: true, version: '0.2.0' }, '*');
    } catch (_) {}
  }

  announce();
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', announce);
  }

  window.addEventListener('message', async (event) => {
    if (event.source !== window || !event.data || typeof event.data !== 'object') return;

    if (event.data.type === 'SAHAYAK_EXT_PING') {
      announce();
      return;
    }

    if (event.data.type === 'SAHAYAK_DIRECT_SYNC') {
      const incoming = event.data.profile;
      if (!incoming || typeof incoming !== 'object') {
        window.postMessage({ type: 'SAHAYAK_DIRECT_SYNC_RES', success: false, error: 'No profile provided' }, '*');
        return;
      }

      // Security invariant: Strip Aadhaar and PAN before passing into extension
      const safe = Object.assign({}, incoming);
      delete safe.aadhaar;
      delete safe.pan;

      try {
        const res = await chrome.runtime.sendMessage({
          action: 'QUEUE_DIRECT_SYNC',
          profile: safe
        });
        window.postMessage({
          type: 'SAHAYAK_DIRECT_SYNC_RES',
          success: !!(res && res.success),
          error: res && res.error
        }, '*');
      } catch (err) {
        window.postMessage({
          type: 'SAHAYAK_DIRECT_SYNC_RES',
          success: false,
          error: err.message || 'Could not communicate with extension service worker'
        }, '*');
      }
    }
  });
})();

