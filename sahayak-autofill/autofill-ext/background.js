// Clicking the toolbar icon opens the Sahayak window and remembers which tab to fill.
chrome.action.onClicked.addListener((tab) => {
  chrome.windows.create({ url: chrome.runtime.getURL('app.html') + '?tab=' + tab.id, type: 'popup', width: 480, height: 800 });
});

// Auto-lock: after the idle time the saved unlock key is removed, so the next use asks for the passphrase again.
chrome.alarms.onAlarm.addListener((a) => { if (a.name === 'sahayakLock') chrome.storage.session.remove('sahayakKey'); });

// Direct Sync receiver from website content script
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg && msg.action === 'QUEUE_DIRECT_SYNC') {
    const profile = msg.profile || {};
    delete profile.aadhaar;
    delete profile.pan;
    chrome.storage.local.set({ sahayakPendingSync: profile }).then(() => {
      try {
        chrome.action.setBadgeText({ text: '1' });
        chrome.action.setBadgeBackgroundColor({ color: '#4F46E5' });
      } catch (_) {}
      sendResponse({ success: true });
    }).catch((err) => {
      sendResponse({ success: false, error: err.message });
    });
    return true;
  }
});
