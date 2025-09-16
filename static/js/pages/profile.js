(function(){
  const prefsBtn = document.getElementById('btn-email-prefs');
  const logoutBtn = document.getElementById('btn-logout');
  const dataRoot = document.getElementById('email-prefs-data');
  let currentShareEventId = null;

  // Handle Gallery open without form wrappers
  document.addEventListener('click', async function(e){
    var gb = e.target.closest('[data-gallery-select]');
    if (gb){
      e.preventDefault();
      var eid = gb.getAttribute('data-event-id');
      if (!eid) return;
      try {
        var res = await fetch('/gallery/select', {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-Requested-With': 'fetch' },
          body: 'event_id=' + encodeURIComponent(eid)
        });
        if (res.ok) { window.location.href = '/gallery'; }
        else { if (window.EPU && window.EPU.snackbar) window.EPU.snackbar.show('Failed to open gallery'); }
      } catch(err){ if (window.EPU && window.EPU.snackbar) window.EPU.snackbar.show('Network error'); }
    }
  });

  const defaults = {
    marketing: dataRoot && dataRoot.dataset.marketing === '1',
    product: dataRoot && dataRoot.dataset.product === '1',
    reminders: dataRoot && dataRoot.dataset.reminders === '1',
  };
  const csrf = dataRoot ? dataRoot.dataset.csrf : '';
  function esc(s){ return (s||'').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[c])); }
  function openShare(code, published, title, eid, tmpl){
    // Remember the current event id and delegate to the centralized share modal
    var url = window.location.origin + '/e/' + (code || '');
    currentShareEventId = eid || null;
    if (window.EPU && window.EPU.share && window.EPU.share.open){
      window.EPU.share.open({ code: code, published: !!published, title: title || '', tmpl: tmpl || null, eid: eid || null });
    }
  }
  document.addEventListener('click', function(e){
    var shareBtn = e.target.closest('.share-btn');
    if (shareBtn){
      e.preventDefault();
      var code = shareBtn.getAttribute('data-code');
      var eid = shareBtn.getAttribute('data-event-id');
      var pub = shareBtn.getAttribute('data-published') === '1';
      var title = shareBtn.getAttribute('data-title') || 'My event';
      currentShareEventId = eid || null;
      openShare(code, pub, title);
    }
    var copyBtn = e.target.closest('.share-copy');
    if (copyBtn){
      var url = copyBtn.getAttribute('data-url') || '';
      var ta = document.createElement('textarea');
      ta.value = url; document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy'); } catch(_err){}
      document.body.removeChild(ta);
      if (window.EPU && window.EPU.toast){ window.EPU.toast('Link copied'); } else if (window.EPU && window.EPU.snackbar) { window.EPU.snackbar.show('Link copied'); }
      if (currentShareEventId) { try { fetch('/events/' + currentShareEventId + '/mark-shared', { method: 'POST', headers: { 'X-Requested-With':'fetch' } }); } catch(_e){} }
    }
    var shareLink = e.target.closest('a.share-link');
    if (shareLink){
      if (currentShareEventId) { try { fetch('/events/' + currentShareEventId + '/mark-shared', { method: 'POST', headers: { 'X-Requested-With':'fetch' } }); } catch(_e){} }
  }
  });

  // When the centralized share modal emits an event, mark the event as shared server-side
  document.addEventListener('epu:shared', function(ev){
    var eid = (ev && ev.detail && ev.detail.eid) || currentShareEventId;
    if (eid){
      try { fetch('/events/' + eid + '/mark-shared', { method: 'POST', headers: { 'X-Requested-With':'fetch' } }); } catch(_e){}
    }
  });

  if (logoutBtn){
    logoutBtn.addEventListener('click', function(){
      const body = '<p class="muted">Are you sure you want to log out?</p>';
      window.EPU && window.EPU.modal && window.EPU.modal.show({
        title: 'Log out',
        body,
        actions: [
          { label: 'Cancel', role: 'cancel' },
          { label: 'Log out', danger: true, onClick: function(){ window.location.href = '/logout'; } }
        ]
      });
    });
  }

  if (prefsBtn){
    prefsBtn.addEventListener('click', function(){
      const body = `
        <div class="modal-section">\n
          <form method="post" action="/profile/email-preferences" class="form">\n
            <input type="hidden" name="csrf_token" value="${csrf}" />\n
            <div class="kv-label">Choose which emails you want to receive</div>\n
            <label class="checkbox-row">\n
              <input class="checkbox-field" type="checkbox" name="marketing" value="1" ${defaults.marketing ? 'checked' : ''} />\n
              <span>Marketing emails (occasional offers and tips)</span>\n
            </label>\n
            <label class="checkbox-row">\n
              <input class="checkbox-field" type="checkbox" name="product" value="1" ${defaults.product ? 'checked' : ''} />\n
              <span>Product updates (new features and improvements)</span>\n
            </label>\n
            <label class="checkbox-row">\n
              <input class="checkbox-field" type="checkbox" name="reminders" value="1" ${defaults.reminders ? 'checked' : ''} />\n
              <span>Event reminders and notifications</span>\n
            </label>\n
            <div class=\"btn-row\">\n
              <button class=\"btn primary\" type=\"submit\">Save Preferences</button>\n
            </div>\n
          </form>\n
        </div>\n
        <div class="modal-section" style="margin-top:12px;">\n
          <form method="post" action="/profile/email-preferences/unsubscribe">\n
            <input type="hidden" name="csrf_token" value="${csrf}" />\n
            <button class=\"btn danger block\" style=\"width:100%\" type=\"submit\">Unsubscribe from all emails</button>\n
          </form>\n
        </div>\n
      `;
      window.EPU && window.EPU.modal && window.EPU.modal.show({ title: 'Email Preferences', body, wide: false, fit: true, actions: [], noDefaultClose: true });
    });
  }
})();
