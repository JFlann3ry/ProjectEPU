// Auxiliary gallery page module
// Handles: album-selector loader, pager nav, delete-confirm modal focus trap,
// create-album modal focus trap.
// Runs alongside the main gallery.js type="module".

// Populate album selector for this event and wire change handler
(function(){
    try{
        var metaEl = document.getElementById('gallery-data');
        if(!metaEl) return;
        var meta = {};
        try{ meta = JSON.parse(metaEl.textContent || '{}'); }catch(e){}
        var eventId = meta.event_id || null;
        if(!eventId) return;
        var sel = document.getElementById('album-filter');
        if(!sel) return;
        fetch('/events/' + encodeURIComponent(eventId) + '/albums')
            .then(function(r){ if(!r.ok) return null; return r.json(); })
            .then(function(j){
                if(!j || !Array.isArray(j.items)) return null;
                j.items.forEach(function(a){
                    try{
                        var opt = document.createElement('option');
                        opt.value = a.id;
                        opt.textContent = a.name + (a.count ? (' (' + a.count + ')') : '');
                        sel.appendChild(opt);
                    }catch(e){}
                });
                try{
                    var u = new URL(window.location.href);
                    return u.searchParams.get('album_id');
                }catch(e){ return null; }
            })
            .then(function(cur){ if(cur) sel.value = cur; })
            .catch(function(){ /* ignore */ })
            .finally(function(){ try{ if (eventId && typeof applyServerOrder === 'function') applyServerOrder(eventId); }catch(e){} });
        sel.addEventListener('change', function(){
            var v = sel.value;
            var u = new URL(window.location.href);
            if(v) u.searchParams.set('album_id', v);
            else u.searchParams.delete('album_id');
            window.location.href = u.toString();
        });
    }catch(e){ }
})();

// Pager controls: adjust URL offset preserving current query params
(function(){
    try{
        var btnPrev = document.getElementById('pager-prev');
        var btnNext = document.getElementById('pager-next');
        function navToOffset(val){
            try{
                var u = new URL(window.location.href);
                if (val === null || val === '' || typeof val === 'undefined') return;
                var n = parseInt(val, 10);
                if (!isFinite(n) || n < 0) n = 0;
                u.searchParams.set('offset', String(n));
                // Preserve existing limit if present; otherwise allow backend default
                window.location.href = u.toString();
            }catch(e){}
        }
        if (btnPrev){ btnPrev.addEventListener('click', function(){ var v = this.getAttribute('data-prev'); if (v !== null && v !== '') navToOffset(v); }); }
        if (btnNext){ btnNext.addEventListener('click', function(){ var v = this.getAttribute('data-next'); if (v !== null && v !== '') navToOffset(v); }); }
    }catch(e){}
})();

// Delete modal: basic focus trap and ESC to close, with focus restore
(function(){
    try{
        var modal = document.getElementById('delete-confirm'); if (!modal) return;
        var cancelBtn = document.getElementById('del-cancel');
        var lastActive = null;
        function isOpen(){ return modal && modal.style.display !== 'none'; }
        function getFocusables(){ return Array.prototype.slice.call(modal.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')).filter(function(el){ return !el.hasAttribute('disabled') && el.offsetParent !== null; }); }
        function openTrap(){ try { lastActive = document.activeElement; var f = getFocusables(); if (f && f.length) f[0].focus(); } catch(e){} }
        function closeTrap(){ try { if (lastActive && lastActive.focus) lastActive.focus(); } catch(e){} }
        // Hook into existing open path by watching style changes when Delete clicked
        var observer = new MutationObserver(function(){ if (isOpen()) openTrap(); });
        observer.observe(modal, { attributes: true, attributeFilter: ['style'] });
        // Trap Tab within modal
        modal.addEventListener('keydown', function(e){
            if (!isOpen()) return;
            if (e.key === 'Escape'){ e.preventDefault(); modal.style.display = 'none'; closeTrap(); return; }
            if (e.key === 'Tab'){
                var f = getFocusables(); if (!f.length) return;
                var first = f[0], last = f[f.length - 1];
                if (e.shiftKey && document.activeElement === first){ e.preventDefault(); last.focus(); }
                else if (!e.shiftKey && document.activeElement === last){ e.preventDefault(); first.focus(); }
            }
        });
        if (cancelBtn){ cancelBtn.addEventListener('click', function(){ try { modal.style.display='none'; closeTrap(); } catch(e){} }); }
    }catch(e){}
})();

// Create-album modal: focus trap and ESC to close, with focus restore
(function(){
    try{
        var modal = document.getElementById('create-album-modal'); if (!modal) return;
        var cancelBtn = document.getElementById('create-album-cancel');
        var formEl = document.getElementById('create-album-form');
        var nameInput = document.getElementById('create-album-name');
        var lastActive = null;
        function isOpen(){ return modal && modal.style.display !== 'none'; }
        function getFocusables(){
            return Array.prototype.slice.call(modal.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'))
                .filter(function(el){ return !el.hasAttribute('disabled') && el.offsetParent !== null; });
        }
        function openTrap(){
            try {
                lastActive = document.activeElement;
                var f = getFocusables();
                if (nameInput && nameInput.offsetParent !== null && nameInput.focus) nameInput.focus();
                else if (f && f.length) f[0].focus();
                document.body.classList.add('modal-open');
                modal.setAttribute('aria-hidden','false');
            } catch(e){}
        }
        function closeTrap(){
            try {
                document.body.classList.remove('modal-open');
                modal.setAttribute('aria-hidden','true');
                if (lastActive && lastActive.focus) lastActive.focus();
            } catch(e){}
        }
        var observer = new MutationObserver(function(){ if (isOpen()) openTrap(); });
        observer.observe(modal, { attributes: true, attributeFilter: ['style'] });
        modal.addEventListener('keydown', function(e){
            if (!isOpen()) return;
            if (e.key === 'Escape'){ e.preventDefault(); modal.style.display = 'none'; closeTrap(); return; }
            if (e.key === 'Tab'){
                var f = getFocusables(); if (!f.length) return;
                var first = f[0], last = f[f.length - 1];
                if (e.shiftKey && document.activeElement === first){ e.preventDefault(); last.focus(); }
                else if (!e.shiftKey && document.activeElement === last){ e.preventDefault(); first.focus(); }
            }
        });
        if (cancelBtn){ cancelBtn.addEventListener('click', function(){ try { modal.style.display='none'; closeTrap(); } catch(e){} }); }
        if (formEl){ formEl.addEventListener('submit', function(){ try { closeTrap(); } catch(e){} }); }
    }catch(e){}
})();
