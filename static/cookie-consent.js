(function(){
  const KEY = "epu_cookie_consent_v1";
  const TTL_DAYS = 180; // ~6 months
  const banner = document.getElementById("cookie-banner");
  const btnAll = document.getElementById("cookie-accept-all");
  const btnSettings = document.getElementById("cookie-settings");
  const footerSettings = document.getElementById("footer-cookie-settings");

  function nowTs(){ return Math.floor(Date.now() / 1000); }
  function saveConsent(consent){
    const data = { ...consent, ts: nowTs(), ttl: TTL_DAYS * 24 * 3600 };
    try { localStorage.setItem(KEY, JSON.stringify(data)); } catch(e) {}
    try {
      document.cookie = KEY + "=" + encodeURIComponent(JSON.stringify(data)) + "; path=/; max-age=" + (data.ttl) + "; samesite=lax";
    } catch(e) {}
  }
  function readConsent(){
    try {
      const raw = localStorage.getItem(KEY);
      if (!raw) return null;
      const data = JSON.parse(raw);
      if (!data || !data.ts || !data.ttl) return null;
      if (nowTs() - data.ts > data.ttl) return null;
      return data;
    } catch(e) { return null; }
  }
  function showBanner(){ if (banner) banner.style.display = "block"; }
  function hideBanner(){ if (banner) banner.style.display = "none"; }

  function openSettings(){
    // Simple settings modal using shared modal component
    const c = readConsent() || { necessary: true, analytics: false };
    const body = [
      '<form id="cookie-form" class="form" style="margin-top:8px;">',
      '<div class="checkbox-row"><input type="checkbox" id="ck-necessary" checked disabled />',
      '<span>Necessary cookies (always on)</span></div>',
      '<div class="checkbox-row"><input type="checkbox" id="ck-analytics"', c.analytics ? ' checked' : '', ' />',
      '<span>Analytics (helps us improve)</span></div>',
      '</form>'
    ].join("");
    window.EPU.modal.show({
      title: "Cookie settings",
      body: body,
      actions: [
        { label: "Save", onClick: function(close){
          const a = !!document.getElementById("ck-analytics").checked;
          saveConsent({ necessary: true, analytics: a });
          hideBanner();
          close();
          window.EPU.snackbar && window.EPU.snackbar.show("Saved cookie settings", { duration: 2500, hideAction: true });
          applyBlocking();
        } },
        { label: "Cancel", role: "cancel" }
      ]
    });
  }

  function applyBlocking(){
    // Block non-essential scripts (analytics) based on consent
    const c = readConsent();
    const allowAnalytics = !!(c && c.analytics);
    // Find any <script type="text/plain" data-category="analytics"> and execute only if allowed
    document.querySelectorAll('script[type="text/plain"][data-category="analytics"]').forEach(function(s){
      if (!allowAnalytics) return;
      const ns = document.createElement('script');
      ns.text = s.text || "";
      // Copy relevant attributes (like src)
      if (s.src) ns.src = s.src;
      if (s.async) ns.async = true;
      if (s.defer) ns.defer = true;
      s.parentNode && s.parentNode.insertBefore(ns, s);
      s.remove();
    });
  }

  // Wire events
  if (btnAll) btnAll.addEventListener('click', function(){
    saveConsent({ necessary: true, analytics: true });
    hideBanner();
    applyBlocking();
  window.EPU.snackbar && window.EPU.snackbar.show("Thanks! Analytics enabled.", { duration: 2500, hideAction: true });
  });
  if (btnSettings) btnSettings.addEventListener('click', function(){ openSettings(); });
  if (footerSettings) footerSettings.addEventListener('click', function(e){ e.preventDefault(); openSettings(); });

  // Init: show banner if no valid consent found
  const consent = readConsent();
  if (!consent) showBanner();
  // Always (re-)apply blocking on load to respect stored choice
  applyBlocking();
})();
