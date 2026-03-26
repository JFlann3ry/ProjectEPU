// event_details.js — gallery-select, copy helpers, lock-date modal, countdown
// Event code is read from the #lock-date-form data-event-code attribute.
document.addEventListener('DOMContentLoaded', function(){
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

    // Share handling delegated globally via base.html (window.EPU.share)
    async function copyToClipboard(text){
        try { if (navigator.clipboard && navigator.clipboard.writeText){ await navigator.clipboard.writeText(text); return true; } } catch(e){}
        try { var ta=document.createElement('textarea'); ta.value=text; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); document.body.removeChild(ta); return true; } catch(e){ return false; }
    }
    document.addEventListener('click', function(e){
        var copyBtn = e.target.closest('.share-copy');
        if (copyBtn){
            var u = copyBtn.getAttribute('data-url');
            copyToClipboard(u).then(function(ok){ if (window.EPU && window.EPU.snackbar){ window.EPU.snackbar.show(ok?'Link copied':'Copy failed', { hideAction: true }); } });
            return;
        }
    });
    // Copy helpers using global snackbar
    async function copyFrom(inputEl, message){
        try {
            if (!inputEl) return;
            if (navigator.clipboard && navigator.clipboard.writeText){
                await navigator.clipboard.writeText(inputEl.value);
            } else {
                var prev = inputEl.getAttribute('readonly');
                inputEl.removeAttribute('readonly');
                inputEl.select();
                document.execCommand('copy');
                if (prev !== null) inputEl.setAttribute('readonly', '');
            }
            if (window.EPU && window.EPU.snackbar){ window.EPU.snackbar.show(message || 'Copied', { hideAction: true }); }
        } catch (e) {
            if (window.EPU && window.EPU.snackbar){ window.EPU.snackbar.show('Copy failed', { hideAction: true }); }
        }
    }
    var linkInput = document.getElementById('guest-link');
    if (linkInput){ linkInput.addEventListener('click', function(){ copyFrom(linkInput, 'Link copied to clipboard'); }); }
    var copyGuestBtn = document.getElementById('copy-guest-link-btn');
    if (copyGuestBtn && linkInput){ copyGuestBtn.addEventListener('click', function(){ copyFrom(linkInput, 'Link copied to clipboard'); }); }
    var codeInput = document.getElementById('event-code');
    if (codeInput){ codeInput.addEventListener('click', function(){ copyFrom(codeInput, 'Code copied to clipboard'); }); }
    var passInput = document.getElementById('event-pass');
    if (passInput){ passInput.addEventListener('click', function(){ copyFrom(passInput, 'Password copied to clipboard'); }); }
    var copyShareBtn = document.getElementById('copy-share');
    if (copyShareBtn){
        copyShareBtn.addEventListener('click', function(){
            var lockForm = document.getElementById('lock-date-form');
            var eventCode = (lockForm && lockForm.dataset && lockForm.dataset.eventCode) || '';
            var tmp = document.createElement('input');
            tmp.style.position='fixed'; tmp.style.left='-9999px';
            tmp.value = window.location.origin + '/e/' + eventCode;
            document.body.appendChild(tmp);
            copyFrom(tmp, 'Share link');
            document.body.removeChild(tmp);
        });
    }

    // Lock date confirmation via shared modal
    var openLock = document.getElementById('open-lock');
    var lockForm = document.getElementById('lock-date-form');
    if (openLock && lockForm && window.EPU && window.EPU.modal){
        openLock.addEventListener('click', function(){
            window.EPU.modal.show({
                title: 'Lock Event Date?',
                body: '<p class="muted">This will finalise your event. The date cannot be changed after locking. Are you sure you want to continue?</p>',
                actions: [
                    { label: 'Cancel', role: 'cancel', onClick: function(hide){ hide(); } },
                    { label: 'Yes, lock date', danger: true, onClick: function(){ lockForm.submit(); } }
                ]
            });
        });
    }

    // Countdown footer inside date card
    (function hydrateCountdown(){
        var now = new Date();
        document.querySelectorAll('.event-card.v5 .date-foot[data-date]').forEach(function(el){
            var iso = el.getAttribute('data-date');
            if(!iso) return;
            var dt = new Date(iso);
            if(isNaN(dt)) return;
            var diffMs = dt.setHours(0,0,0,0) - (new Date(now)).setHours(0,0,0,0);
            var days = Math.round(diffMs / 86400000);
            if (days > 0){
                el.textContent = days + ' days';
                el.title = days + ' day' + (days===1?'':'s') + ' to go';
            } else if (days === 0){
                el.textContent = 'Today';
                el.title = 'Event is today';
            } else {
                var past = Math.abs(days);
                el.textContent = past + ' days ago';
                el.title = past + ' day' + (past===1?'':'s') + ' ago';
            }
        });
    })();
});
