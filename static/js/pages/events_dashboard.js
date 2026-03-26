(function(){
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
    function esc(s){ return (s||'').replace(/[&<>"];/g, function(c){ return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',';':'&#59;'}[c]) || c; }); }
    function openShare(code, published, title, eid, tmpl){
        if (window.EPU && window.EPU.share && window.EPU.share.open){
            window.EPU.share.open({ code: code, published: !!published, title: title || '', tmpl: tmpl || null, eid: eid || null });
        }
    }

    // Listen for the shared event emitted by the global share modal and mark the event as shared server-side
    document.addEventListener('epu:shared', function(ev){
        try{ var eid = ev && ev.detail && ev.detail.eid; if (eid) { markShared(eid); } }catch(_e){}
    });
    async function copyToClipboard(text){
        try { if (navigator.clipboard && navigator.clipboard.writeText){ await navigator.clipboard.writeText(text); return true; } } catch(e){}
        try { var ta=document.createElement('textarea'); ta.value=text; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); document.body.removeChild(ta); return true; } catch(e){ return false; }
    }
    function markSharedUI(eid){
        if (!eid) return;
        // Flip share to-do to done for this event card
        document.querySelectorAll('.event-card.v5 [data-event-id="' + eid + '"]').forEach(function(el){
            if (el.classList.contains('share-btn')){
                el.classList.remove('pending');
                el.classList.add('done');
            }
        });
    }
    async function markShared(eid){
        try { if (eid) { await fetch('/events/' + eid + '/mark-shared', { method: 'POST', headers: { 'X-Requested-With':'fetch' } }); } } catch(err){}
        markSharedUI(eid);
    }
    document.addEventListener('click', function(e){
        var copyBtn = e.target.closest('.share-copy');
        if (copyBtn){
            var u = copyBtn.getAttribute('data-url');
            var eid2 = copyBtn.getAttribute('data-eid');
            copyToClipboard(u).then(function(ok){
                if (window.EPU && window.EPU.snackbar){ window.EPU.snackbar.show(ok?'Link copied':'Copy failed'); }
                if (ok) { markShared(eid2); }
            });
            return;
        }
        var shareVia = e.target.closest('.share-via');
        if (shareVia){
            // Treat clicking an external share link as a share action
            var eid3 = shareVia.getAttribute('data-eid');
            markShared(eid3);
            return;
        }
        var shareMore = e.target.closest('.share-more');
        if (shareMore){
            e.preventDefault();
            var u = shareMore.getAttribute('data-url');
            var eid4 = shareMore.getAttribute('data-eid');
            if (navigator.share){
                try {
                    navigator.share({ title: document.title || 'Event', text: 'Check out this event', url: u })
                    .then(function(){ if (window.EPU && window.EPU.snackbar) window.EPU.snackbar.show('Shared'); markShared(eid4); })
                    .catch(function(err){ if (window.EPU && window.EPU.snackbar) window.EPU.snackbar.show('Share cancelled'); });
                } catch(err){
                    // If share throws synchronously, fallback to copy
                    copyToClipboard(u).then(function(ok){ if (window.EPU && window.EPU.snackbar) window.EPU.snackbar.show(ok?'Link copied':'Copy failed'); if (ok) markShared(eid4); });
                }
            } else {
                // Fallback: copy link
                copyToClipboard(u).then(function(ok){ if (window.EPU && window.EPU.snackbar) window.EPU.snackbar.show(ok?'Link copied to clipboard':'Copy failed'); if (ok) markShared(eid4); });
            }
            return;
        }
    });

    // Hydrate progress bars (v5)
    function hydrateProgress(){
        document.querySelectorAll('.event-card.v5 .progress').forEach(function(p){
            var pct = parseInt(p.getAttribute('data-pct') || '0', 10);
            var state = (p.getAttribute('data-state') || 'ok').toLowerCase();
            var bar = p.querySelector('.bar');
            if(!bar) return;
            bar.classList.remove('warn','danger');
            if(state === 'warn') bar.classList.add('warn');
            if(state === 'danger') bar.classList.add('danger');
            requestAnimationFrame(function(){ bar.style.width = Math.max(0, Math.min(100, pct)) + '%'; });
        });
    }
    hydrateProgress();

    // Countdown footer inside date card
    function hydrateCountdown(){
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
    }
    hydrateCountdown();
})();
