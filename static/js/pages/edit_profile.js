// Edit profile: delete account modal, email prefs form, and export cooldown
(function(){
    // Ensure an ARIA live region exists for status updates
    (function(){
        var lr = document.getElementById('aria-live-toast');
        if (!lr) {
            lr = document.createElement('div');
            lr.id = 'aria-live-toast';
            lr.setAttribute('aria-live', 'polite');
            lr.setAttribute('aria-atomic', 'true');
            lr.style.position = 'absolute';
            lr.style.width = '1px';
            lr.style.height = '1px';
            lr.style.margin = '-1px';
            lr.style.border = '0';
            lr.style.padding = '0';
            lr.style.clip = 'rect(0 0 0 0)';
            lr.style.overflow = 'hidden';
            document.body.appendChild(lr);
        }
    })();
    const liveRegion = document.getElementById('aria-live-toast');

    // Insert snackbar container
    if (!document.getElementById('site-snackbar')){
        const sb = document.createElement('div');
        sb.id = 'site-snackbar';
        document.body.appendChild(sb);
    }

    // Delete account modal
    const delBtn = document.getElementById('btn-delete-account');
    if (delBtn) {
        delBtn.addEventListener('click', function(){
            if (window.EPU && window.EPU.modal) {
                window.EPU.modal.show({
                    title: 'Delete account?',
                    body: '<div class="preview-body"><p>This will permanently delete your account and data. This cannot be undone.</p></div>',
                    actions: [
                        { label: 'Cancel', role: 'cancel' },
                        { label: 'Delete account', danger: true, onClick: function(){ window.location.href = '/account/delete'; } }
                    ]
                });
            } else if (confirm('This will permanently delete your account and data. Continue?')) {
                window.location.href = '/account/delete';
            }
        });
    }

    // Email prefs UX: live summary, enable save on change, confirm unsubscribe
    const prefsForm = document.getElementById('email-prefs-form');
    const saveBtn = document.getElementById('prefs-save');
    const statusEl = document.getElementById('prefs-status');
    const unsubBtn = document.getElementById('prefs-unsub');
    const csrfInput = prefsForm ? prefsForm.querySelector('input[name="csrf_token"]') : null;

    function setSaveEnabled(enabled) {
        if (!saveBtn) return;
        saveBtn.disabled = !enabled;
    }

    function setStatus(msg, type) {
        // Update screen-reader live region
        if (liveRegion) liveRegion.textContent = msg || '';
        // Show transient snackbar for visual confirmation
        if (msg) {
            const kind = type === 'error' ? 'error' : 'success';
            try { showSnackbar(msg, kind); } catch (e) { /* no-op if snackbar missing */ }
        }
    }

    function showSnackbar(msg, type, ms){
        const el = document.getElementById('site-snackbar');
        if (!el) return;
        el.className = '';
        el.textContent = msg;
        if (type) el.classList.add(type);
        el.classList.add('show');
        const timeout = ms || 3500;
        setTimeout(()=>{ el.classList.remove('show'); el.className = ''; }, timeout);
    }

    async function postFormData(url, formData) {
        // Let fetch follow redirects; we just care about ok/not ok
        const res = await fetch(url, {
            method: 'POST',
            body: formData,
            credentials: 'same-origin'
        });
        // Treat 2xx and 3xx as success since server may redirect after save
        if (res.ok || (res.status >= 300 && res.status < 400)) {
            return true;
        }
        return false;
    }

    // Track pristine state
    let original = '';
    if (prefsForm) {
        original = Array.from(prefsForm.querySelectorAll('input[type="checkbox"]')).map(b => (b.name+':'+(b.checked?'1':'0'))).join('|');
        setSaveEnabled(false);
        prefsForm.addEventListener('change', () => {
            const current = Array.from(prefsForm.querySelectorAll('input[type="checkbox"]')).map(b => (b.name+':'+(b.checked?'1':'0'))).join('|');
            setSaveEnabled(current !== original);
        });
        prefsForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!saveBtn) return;
            setStatus('Saving…');
            saveBtn.disabled = true;
            const fd = new FormData(prefsForm);
            // Ensure unchecked boxes are sent as 0 so backend can clear them if required
            ['marketing','product','reminders'].forEach(name => {
                if (!fd.has(name)) fd.append(name, '0');
            });
            const ok = await postFormData(prefsForm.action, fd).catch(() => false);
            if (ok) {
                setStatus('Preferences saved');
                original = Array.from(prefsForm.querySelectorAll('input[type="checkbox"]')).map(b => (b.name+':'+(b.checked?'1':'0'))).join('|');
                setSaveEnabled(false);
            } else {
                setStatus('Save failed. Please try again.', 'error');
                setSaveEnabled(true);
            }
        });
    }

    if (unsubBtn && prefsForm) {
        unsubBtn.addEventListener('click', async () => {
            // Immediately send unsubscribe request and show transient snackbar
            setStatus('Unsubscribing…');
            unsubBtn.disabled = true;
            const fd = new FormData();
            if (csrfInput) fd.append('csrf_token', csrfInput.value);
            const ok = await postFormData('/profile/email-preferences/unsubscribe', fd).catch(() => false);
            if (ok) {
                // Uncheck all locally
                prefsForm.querySelectorAll('input[type="checkbox"]').forEach(b => { b.checked = false; });
                original = Array.from(prefsForm.querySelectorAll('input[type="checkbox"]')).map(b => (b.name+':0')).join('|');
                setSaveEnabled(false);
                setStatus('You have been unsubscribed from all emails');
                showSnackbar('You have been unsubscribed', 'success');
            } else {
                setStatus('Unsubscribe failed. Please try again.', 'error');
                showSnackbar('Unsubscribe failed', 'error');
            }
            unsubBtn.disabled = false;
        });
    }

    // Export cooldown countdown and AJAX-ish UX
    const exportForm = document.getElementById('export-form');
    const requestBtn = document.getElementById('btn-request-export');
    const cooldownWrap = document.getElementById('export-cooldown');
    const cooldownTimer = document.getElementById('cooldown-timer');
    const cdAttr = exportForm ? exportForm.getAttribute('data-cooldown-seconds') : '0';
    let remaining = parseInt(cdAttr || '0', 10) || 0;

    function tickCooldown(){
        if (!cooldownTimer) return;
        if (remaining <= 0){
            cooldownWrap && (cooldownWrap.style.display='none');
            requestBtn && (requestBtn.disabled=false);
            return;
        }
        const h = Math.floor(remaining/3600);
        const m = Math.floor((remaining%3600)/60);
        const s = remaining%60;
        const parts = [];
        if (h>0) parts.push(h+'h');
        if (m>0) parts.push(m+'m');
        parts.push(s+'s');
        cooldownTimer.textContent = parts.join(' ');
        remaining -= 1;
        setTimeout(tickCooldown, 1000);
    }

    if (remaining > 0) tickCooldown();
    if (exportForm && requestBtn){
        exportForm.addEventListener('submit', function(e){
            // We let the form submit normally (server builds and redirects with message), but add quick UX
            requestBtn.disabled = true;
            requestBtn.textContent = 'Requesting…';
        });
    }
})();
