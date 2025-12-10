// Rewritten gallery page module
// Provides: lazy-loading thumbnails, infinite scroll that hits /gallery/data, tile aspect ratio handling,
// lightbox, selection helpers, filters wiring, and bulk actions.

/* globals window, document, fetch, URLSearchParams */

const G = (function () {
  'use strict';

  let files = [];
  let currentIndex = -1;
  const DEBUG = !!(window && window.__GALLERY_DEBUG);

  // CSRF helper: read token from meta tag or hidden input on page
  function getCSRFToken() {
    try {
      const meta = document.querySelector('meta[name="csrf-token"]');
      if (meta && meta.content) return meta.content;
    } catch (e) {}
    try {
      const any = document.querySelector('input[name="csrf_token"]');
      if (any && any.value) return any.value;
    } catch (e) {}
    return '';
  }
  // Lazy loader for thumbnails
  const lazyObserver = ('IntersectionObserver' in window) ? new IntersectionObserver((entries, obs) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const img = entry.target;
      try {
        const src = img.dataset && img.dataset.src;
        if (src) img.src = src;
        const srcset = img.dataset && img.dataset.srcset;
        if (srcset) img.setAttribute('srcset', srcset);
        const sizes = img.dataset && img.dataset.sizes;
        if (sizes) img.setAttribute('sizes', sizes);
      } catch (e) {}
      try { obs.unobserve(img); } catch (e) {}
    });
  }, { rootMargin: '400px', threshold: 0.01 }) : { observe() {}, unobserve() {} };

  // Helper: find file object by id
  function getFileById(id) {
    try {
      const n = Number(id);
      if (Number.isFinite(n) && Array.isArray(files)) return files.find(x => x && x.id === n) || null;
      try { if (Array.isArray(window.galleryFiles)) return window.galleryFiles.find(x => x && x.id === n) || null; } catch (e) {}
    } catch (e) {}
    return null;
  }

  // Open "Add to album" modal for selected file IDs
  function openAddToAlbumModal(ids) {
    try {
      if (!Array.isArray(ids) || ids.length === 0) return;
      const dataEl = document.getElementById('gallery-data'); if (!dataEl) return;
      let meta = {};
      try { meta = JSON.parse(dataEl.textContent || '{}'); } catch (e) { meta = {}; }
      const eventId = meta && meta.event_id ? meta.event_id : null;
      if (!eventId) return;

      // Use shared modal when available for consistent styling
      const useShared = !!(window.EPU && window.EPU.modal && typeof window.EPU.modal.show === 'function');
      let listWrap = null;
      let addBtn = null;
      let closeModal = function(){};
      if (useShared){
        const body = '' +
          '<div class="form" id="add-to-album-form" style="max-height:60vh; overflow:auto;">' +
          '  <div class="muted" id="add-album-list">Loading albums…</div>' +
          '</div>';
        window.EPU.modal.show({ title: 'Add selected files to album', body, actions: [
          { label: 'Cancel', role: 'cancel' },
          { label: 'Add', onClick: function(){ /* handled below */ } }
        ]});
        closeModal = function(){ try { window.EPU.modal.hide(); } catch(_){} };
        setTimeout(function(){ try {
          listWrap = document.getElementById('add-album-list');
          const footer = document.querySelector('#modal-root .modal-actions');
          addBtn = footer ? footer.querySelectorAll('button')[1] : null;
          if (addBtn) addBtn.disabled = true;
        } catch(_){} }, 10);
      } else {
        // Legacy inline modal fallback
        let modal = document.getElementById('add-to-album-modal');
        if (modal) modal.remove();
        modal = document.createElement('div'); modal.id = 'add-to-album-modal'; modal.className = 'modal'; modal.setAttribute('role', 'dialog'); modal.setAttribute('aria-modal', 'true'); modal.style.display = 'flex'; modal.style.position = 'fixed'; modal.style.inset = '0'; modal.style.alignItems = 'center'; modal.style.justifyContent = 'center'; modal.style.background = 'rgba(0,0,0,0.5)'; modal.style.zIndex = '1002';
        const content = document.createElement('div'); content.className = 'modal-content'; content.style.maxWidth = '520px'; content.style.padding = '12px'; content.style.boxSizing = 'border-box'; content.style.background = 'rgba(0,0,0,0.85)'; content.style.border = '1px solid var(--color-border)'; content.style.borderRadius = '8px';
        const title = document.createElement('h3'); title.className = 'p-bold'; title.textContent = 'Add selected files to album'; content.appendChild(title);
        listWrap = document.createElement('div'); listWrap.style.marginTop = '8px'; listWrap.textContent = 'Loading albums…'; content.appendChild(listWrap);
        const actions = document.createElement('div'); actions.style.display = 'flex'; actions.style.justifyContent = 'flex-end'; actions.style.gap = '8px'; actions.style.marginTop = '12px';
        const cancelBtn = document.createElement('button'); cancelBtn.type = 'button'; cancelBtn.className = 'btn'; cancelBtn.textContent = 'Cancel';
        addBtn = document.createElement('button'); addBtn.type = 'button'; addBtn.className = 'btn primary'; addBtn.textContent = 'Add'; addBtn.disabled = true;
        actions.appendChild(cancelBtn); actions.appendChild(addBtn); content.appendChild(actions);
        modal.appendChild(content); document.body.appendChild(modal);
        closeModal = function(){ try { modal.remove(); } catch (e) {} };
        cancelBtn.addEventListener('click', closeModal);
      }

      // Fetch albums for this event
      fetch('/events/' + encodeURIComponent(eventId) + '/albums', { credentials: 'same-origin' })
        .then(r => { if (!r.ok) throw new Error('bad'); return r.json(); })
        .then(j => {
          if (!listWrap) return;
          listWrap.innerHTML = '';
          if (!j || !Array.isArray(j.items) || j.items.length === 0) {
            const none = document.createElement('div'); none.className = 'muted'; none.textContent = 'No albums found. Create one first.'; listWrap.appendChild(none);
            const createLink = document.createElement('button'); createLink.type = 'button'; createLink.className = 'btn'; createLink.textContent = 'Create album'; createLink.style.marginTop = '8px';
            createLink.addEventListener('click', function () { try { closeModal(); if (typeof openCreateAlbumModal === 'function') openCreateAlbumModal(); else { var el = document.getElementById('create-album-modal'); if (el) el.style.display = 'flex'; } } catch (e) {} });
            listWrap.appendChild(createLink);
            return;
          }
          const form = document.createElement('div'); form.style.display = 'flex'; form.style.flexDirection = 'column'; form.style.gap = '6px';
          let selectedAlbum = null;
          j.items.forEach(a => {
            try {
              const row = document.createElement('label'); row.style.display = 'flex'; row.style.alignItems = 'center'; row.style.gap = '8px'; row.style.cursor = 'pointer';
              const r = document.createElement('input'); r.type = 'radio'; r.name = 'album'; r.value = String(a.id);
              r.addEventListener('change', function () { selectedAlbum = this.value; if (addBtn) addBtn.disabled = !selectedAlbum; });
              const t = document.createElement('span'); t.textContent = a.name + (a.count ? (' (' + a.count + ')') : '');
              row.appendChild(r); row.appendChild(t); form.appendChild(row);
            } catch (e) {}
          });
          listWrap.appendChild(form);

          const onAdd = function () {
            if (!selectedAlbum) return;
            if (addBtn){ addBtn.disabled = true; addBtn.textContent = 'Adding…'; }
            // Send POST for each file id; run sequentially to avoid DB race concerns
            const promises = ids.map(fid => {
              const fd = new FormData(); fd.append('file_id', String(fid));
              try { const csrf = getCSRFToken(); if (csrf) fd.append('csrf_token', csrf); } catch (e) {}
              return fetch('/events/' + encodeURIComponent(eventId) + '/albums/' + encodeURIComponent(selectedAlbum) + '/add', {
                method: 'POST', body: fd, credentials: 'same-origin'
              }).then(r => r.ok ? r.json().catch(()=>({ok:true})) : Promise.reject(r));
            });
            Promise.all(promises).then(() => {
              try { closeModal(); } catch (e) {}
              try { if (window.EPU && window.EPU.snackbar) window.EPU.snackbar.show('Added to album'); } catch(_){}
              // If an album is currently selected in the filter and matches selectedAlbum, force reload to show files
              try {
                const sel = document.getElementById('album-filter');
                if (sel && sel.value === String(selectedAlbum)) {
                  const u = new URL(window.location.href); u.searchParams.set('album_id', String(selectedAlbum)); window.location.href = u.toString();
                }
              } catch(_){ }
            }).catch(() => {
              try { if (addBtn){ addBtn.disabled = false; addBtn.textContent = 'Add'; } } catch (e) {}
            });
          };
          if (addBtn) addBtn.addEventListener('click', onAdd);
          // Also hook shared modal primary button if used
          if (useShared){
            setTimeout(function(){ try {
              const footer = document.querySelector('#modal-root .modal-actions');
              const primary = footer ? footer.querySelectorAll('button')[1] : null;
              if (primary && primary !== addBtn){ primary.removeEventListener('click', function(){}); primary.addEventListener('click', onAdd); }
            } catch(_){} }, 30);
          }
        })
        .catch(() => {
          if (!listWrap) return; listWrap.innerHTML = ''; const err = document.createElement('div'); err.className = 'muted'; err.textContent = 'Unable to load albums.'; listWrap.appendChild(err);
        });

    } catch (e) { /* ignore */ }
  }

  // Temporary on-screen debug banner for environments where console is not visible
  function showDebugBanner(msg, timeout) {
    try {
      timeout = typeof timeout === 'number' ? timeout : 5000;
      let el = document.getElementById('gallery-debug-banner');
      if (!el) {
        el = document.createElement('div'); el.id = 'gallery-debug-banner';
        el.style.position = 'fixed'; el.style.left = '50%'; el.style.bottom = '16px'; el.style.transform = 'translateX(-50%)';
        el.style.background = 'rgba(0,0,0,0.85)'; el.style.color = 'white'; el.style.padding = '8px 12px'; el.style.borderRadius = '8px'; el.style.zIndex = 10050;
        el.style.fontSize = '13px'; el.style.boxShadow = '0 6px 18px rgba(0,0,0,0.6)'; document.body.appendChild(el);
      }
      el.textContent = String(msg || ''); el.style.display = 'block';
      if (el._timeout) clearTimeout(el._timeout);
      el._timeout = setTimeout(function(){ try { el.style.display = 'none'; } catch(e){} }, timeout);
    } catch (e) { try { console.log('debugBanner', msg); } catch(e){} }
  }

  // expose helper to global scope in case other inline scripts expect it
  try { window.openAddToAlbumModal = openAddToAlbumModal; } catch (e) {}

  // Create Album modal: use shared modal root if available, fallback to inline modal
  function openCreateAlbumModal() {
    try {
      const dataEl = document.getElementById('gallery-data'); if (!dataEl) return;
      let meta = {}; try { meta = JSON.parse(dataEl.textContent || '{}'); } catch (e) {}
      const eventId = meta && meta.event_id ? meta.event_id : null; if (!eventId) return;

      // Preferred: shared modal component from base.html
      if (window.EPU && window.EPU.modal && typeof window.EPU.modal.show === 'function') {
        const body = '' +
          '<form id="create-album-form" class="form">' +
          '  <label for="create-album-name">Album Name</label>' +
          '  <input id="create-album-name" name="name" class="input-field" required maxlength="255">' +
          '  <div class="btn-row" style="margin-top:12px; justify-content:flex-end; gap:8px;">' +
          '    <button type="button" id="create-album-cancel" class="btn sm">Cancel</button>' +
          '    <button type="submit" id="create-album-submit" class="btn sm primary">Create</button>' +
          '  </div>' +
          '</form>';
        window.EPU.modal.show({ title: 'Create album', body, actions: [], raw: true, noDefaultClose: true });
        setTimeout(function(){
          try {
            const form = document.getElementById('create-album-form');
            const nameInput = document.getElementById('create-album-name');
            const cancelBtn = document.getElementById('create-album-cancel');
            const submitBtn = document.getElementById('create-album-submit');
            if (nameInput && nameInput.focus) nameInput.focus();
            if (cancelBtn) cancelBtn.addEventListener('click', function(){ try { window.EPU.modal.hide(); } catch(_){} });
            if (form) form.addEventListener('submit', function(ev){
              ev.preventDefault();
              const name = (nameInput && nameInput.value || '').trim(); if (!name) return;
              if (submitBtn) submitBtn.disabled = true;
              const fd = new FormData(); fd.append('name', name);
              try { const csrf = getCSRFToken(); if (csrf) fd.append('csrf_token', csrf); } catch(e){}
              fetch('/events/' + encodeURIComponent(eventId) + '/albums/create', { method: 'POST', body: fd, credentials: 'same-origin' })
                .then(r => r.ok ? r.json().catch(()=>({ ok: true })) : Promise.reject(r))
                .then(() => {
                  try { if (window.EPU && window.EPU.snackbar) window.EPU.snackbar.show('Album created'); } catch(_){ }
                  // Refresh album selector (if present)
                  try {
                    const sel = document.getElementById('album-filter');
                    if (sel) {
                      fetch('/events/' + encodeURIComponent(eventId) + '/albums', { credentials: 'same-origin' })
                        .then(rr => rr.ok ? rr.json() : null)
                        .then(j => {
                          if (!j || !Array.isArray(j.items)) return;
                          const first = sel.querySelector('option');
                          while (sel.firstChild) sel.removeChild(sel.firstChild);
                          if (first) sel.appendChild(first);
                          j.items.forEach(a => { const opt = document.createElement('option'); opt.value = a.id; opt.textContent = a.name + (a.count ? (' (' + a.count + ')') : ''); sel.appendChild(opt); });
                        })
                        .catch(()=>{});
                    }
                  } catch(_){}
                  try { window.EPU.modal.hide(); } catch(_){}
                })
                .catch(() => { try { if (submitBtn) submitBtn.disabled = false; } catch(_){} });
            });
          } catch(_){}
        }, 10);
        return;
      }

      // Fallback: show inline modal already present in the page and wire the form
      const modal = document.getElementById('create-album-modal'); if (!modal) return;
      const form = document.getElementById('create-album-form'); if (!form) return;
      const nameInput = document.getElementById('create-album-name');
      const cancelBtn = document.getElementById('create-album-cancel');
      const submitBtn = document.getElementById('create-album-submit');
      modal.style.display = 'flex';

      // Basic focus trap
      let lastActive = document.activeElement;
      function getFocusables(){ return Array.prototype.slice.call(modal.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')).filter(function(el){ return !el.hasAttribute('disabled') && el.offsetParent !== null; }); }
      function closeModal(){ try { modal.style.display = 'none'; if (lastActive && lastActive.focus) lastActive.focus(); } catch(e){} }
      try { if (nameInput && nameInput.focus) nameInput.focus(); } catch(e){}
      modal.addEventListener('keydown', function(e){
        try {
          if (e.key === 'Escape') { e.preventDefault(); closeModal(); return; }
          if (e.key === 'Tab') {
            const f = getFocusables(); if (!f.length) return;
            const i = f.indexOf(document.activeElement);
            if (e.shiftKey && (i <= 0)) { e.preventDefault(); f[f.length - 1].focus(); }
            else if (!e.shiftKey && (i === f.length - 1)) { e.preventDefault(); f[0].focus(); }
          }
        } catch(_){}}
      );
      if (cancelBtn) cancelBtn.onclick = function(){ closeModal(); };

      form.onsubmit = function(ev){
        ev.preventDefault();
        const name = (nameInput && nameInput.value || '').trim(); if (!name) return;
        if (submitBtn) submitBtn.disabled = true;
        const fd = new FormData(); fd.append('name', name);
        try { const csrf = getCSRFToken(); if (csrf) fd.append('csrf_token', csrf); } catch(e){}
        fetch('/events/' + encodeURIComponent(eventId) + '/albums/create', { method: 'POST', body: fd, credentials: 'same-origin' })
          .then(r => r.ok ? r.json().catch(()=>({ ok: true })) : Promise.reject(r))
          .then(() => {
            try { if (window.EPU && window.EPU.snackbar) window.EPU.snackbar.show('Album created'); } catch(_){ }
            try {
              const sel = document.getElementById('album-filter');
              if (sel) {
                fetch('/events/' + encodeURIComponent(eventId) + '/albums', { credentials: 'same-origin' })
                  .then(rr => rr.ok ? rr.json() : null)
                  .then(j => {
                    if (!j || !Array.isArray(j.items)) return;
                    const first = sel.querySelector('option');
                    while (sel.firstChild) sel.removeChild(sel.firstChild);
                    if (first) sel.appendChild(first);
                    j.items.forEach(a => { const opt = document.createElement('option'); opt.value = a.id; opt.textContent = a.name + (a.count ? (' (' + a.count + ')') : ''); sel.appendChild(opt); });
                  })
                  .catch(()=>{});
              }
            } catch(_){}
            closeModal();
          })
          .catch(() => { try { if (submitBtn) submitBtn.disabled = false; } catch(_){} });
      };
    } catch (e) { /* ignore */ }
  }
  try { window.openCreateAlbumModal = openCreateAlbumModal; } catch (e) {}

  // Wire selection forms to gather selected ids
  function wireSelection(formId) {
    const form = document.getElementById(formId);
    if (!form) return;
    form.addEventListener('submit', function (e) {
      const raw = Array.from(document.querySelectorAll('.select-chk:checked'));
      let ids = raw.map(chk => chk.getAttribute('data-id'));
      if (formId === 'restore-form') ids = ids.filter(id => { const f = getFileById(id); return f && f.deleted; });
      if (formId === 'delete-form') ids = ids.filter(id => { const f = getFileById(id); return f && !f.deleted; });
      if (ids.length === 0) { e.preventDefault(); return; }
      Array.from(form.querySelectorAll('input[name="file_ids"]')).forEach(i => i.remove());
      ids.forEach(id => { const hidden = document.createElement('input'); hidden.type = 'hidden'; hidden.name = 'file_ids'; hidden.value = id; form.appendChild(hidden); });
    });
  }

  function initFilters() {
    function setParam(key, val, toggle) {
      const url = new URL(window.location.href);
      if (toggle) {
        const cur = url.searchParams.get(key);
        const next = (cur === '1' || cur === 'true') ? '' : '1';
        if (next) url.searchParams.set(key, next); else url.searchParams.delete(key);
      } else {
        if (val) url.searchParams.set(key, val); else url.searchParams.delete(key);
      }
      url.searchParams.delete('offset'); window.location.href = url.toString();
    }
    document.querySelectorAll('.pill-filter').forEach(btn => btn.addEventListener('click', () => { setParam(btn.getAttribute('data-filter'), btn.getAttribute('data-value') || '', btn.hasAttribute('data-toggle')); }));
  }

  // Masonry reflow helpers (grid auto-rows technique)
  function reflowGalleryMasonry() {
    try {
      const gal = document.getElementById('gallery'); if (!gal) return;
      const cs = getComputedStyle(gal);
      const rowHeight = parseFloat(cs.getPropertyValue('grid-auto-rows')) || 8;
      const rowGap = parseFloat(cs.getPropertyValue('row-gap')) || parseFloat(cs.getPropertyValue('grid-row-gap')) || 12;
      const maxTile = parseInt(cs.getPropertyValue('--gallery-max-tile-height')) || 420;
      Array.from(gal.querySelectorAll('.gallery-item, .group-heading')).forEach((child) => {
        try {
          child.style.position = '';
          // Prefer intrinsic dimensions from media to avoid zero-height while images decode.
          let h = 0;
          try {
            const img = child.querySelector && child.querySelector('img.gallery-img');
            const vid = !img && child.querySelector && child.querySelector('video');
            if (img) {
              const iw = img.naturalWidth || img.getAttribute('data-w') || img.width || 0;
              const ih = img.naturalHeight || img.getAttribute('data-h') || img.height || 0;
              if (iw && ih) h = Math.round((child.clientWidth || img.clientWidth || 200) * (ih / iw));
            } else if (vid) {
              const vw = vid.videoWidth || vid.getAttribute('data-w') || vid.clientWidth || 0;
              const vh = vid.videoHeight || vid.getAttribute('data-h') || vid.clientHeight || 0;
              if (vw && vh) h = Math.round((child.clientWidth || vid.clientWidth || 200) * (vh / vw));
            }
          } catch (e) { /* ignore intrinsic calc */ }
          if (!h) h = Math.round(child.getBoundingClientRect().height) || child.offsetHeight || 0;
          // Use measured/intrinsic height directly; only cap the maximum to avoid runaway sizes
          h = Math.min(maxTile, Math.max(h, 0));
          const span = Math.max(1, Math.ceil((h + rowGap) / (rowHeight + rowGap)));
          if (child.classList && child.classList.contains('group-heading')) {
            // Let headings be full-width and auto-height without forcing a row span
            child.style.gridColumn = '1 / -1';
            child.style.gridRowEnd = '';
          } else {
            child.style.gridRowEnd = 'span ' + String(span);
          }
        } catch (e) { /* ignore per-tile */ }
      });
    } catch (e) { /* ignore */ }
  }

  // Column-style masonry renderer: create N columns and append tiles into the shortest column.
  // This gives a denser, Explorer-like layout. We keep grid reflow as a fallback.
  function renderColumnMasonry(desiredCols) {
    try {
      const gal = document.getElementById('gallery'); if (!gal) return;
  // Column-masonry is opt-in. Only run if server/template set data-masonry="columns"
  if (!gal.dataset || gal.dataset.masonry !== 'columns') return;
  // Ensure container has the masonry flag (changes CSS behavior)
  gal.classList.add('masonry-columns');

  // Collect all items (from anywhere inside the gallery) BEFORE removing wrappers.
  // This preserves DOM order and avoids losing children when removing the previous wrapper.
  const items = Array.from(gal.querySelectorAll('.group-heading, .gallery-item'));
  // If there are no items, ensure we don't create empty columns
  if (!items || items.length === 0) return;

  // If there is an existing direct child wrapper, record its column count so we can preserve it
  const existing = gal.querySelector(':scope > .masonry-columns');
  const existingColCount = existing ? (existing.querySelectorAll('.masonry-column') || []).length : 0;
  // Remove the existing wrapper now that we've recorded its column count and collected item nodes
  if (existing) existing.remove();
  // Create new column wrapper
  const wrapper = document.createElement('div'); wrapper.className = 'masonry-columns';
  // Use the largest available width (gallery, parent, or window) to avoid transient small widths
  const availableWidth = Math.max(gal.clientWidth || 0, (gal.parentElement && gal.parentElement.clientWidth) || 0, window.innerWidth || 0);
  // Choose a reasonable target column width to avoid excessive columns on large screens
  const targetColWidth = 300; // px
  const cols = existingColCount > 0 ? existingColCount : Math.max(1, Math.min(5, desiredCols || Math.max(1, Math.floor(availableWidth / targetColWidth))));
  if (DEBUG) console.debug('renderColumnMasonry', { cols, galWidth: gal.clientWidth, parentWidth: (gal.parentElement && gal.parentElement.clientWidth) || 0, winW: window.innerWidth, availableWidth, items: items.length });
  if (DEBUG && cols === 1 && availableWidth > 520) console.warn('renderColumnMasonry chose 1 column despite reasonable width', { availableWidth, cols });
      const columnEls = [];
      for (let i = 0; i < cols; i++) { const c = document.createElement('div'); c.className = 'masonry-column'; wrapper.appendChild(c); columnEls.push(c); }


      // Place items into shortest column (by height) to balance the layout
  // If columns are initially empty (heights all <= 1), use round-robin to avoid placing everything into the first column
  const initHeights = columnEls.map(c => c.scrollHeight || c.getBoundingClientRect().height || 0);
  const allEmpty = initHeights.every(h => h <= 1);
  let rr = 0;
  items.forEach((it) => {
        // For headings, prefer full-width: place as a break element (append to wrapper as its own row)
        if (it.classList && it.classList.contains('group-heading')) {
          // Insert heading directly into wrapper to span full width with natural height
          wrapper.appendChild(it);
          return;
        }
        // Find shortest column or use round-robin if all columns are currently empty
        if (allEmpty) {
          const col = columnEls[rr % columnEls.length]; rr += 1; col.appendChild(it);
        } else {
          let minCol = columnEls[0]; let minH = columnEls[0].scrollHeight || columnEls[0].getBoundingClientRect().height || 0;
          for (let c = 1; c < columnEls.length; c++) {
            const h = columnEls[c].scrollHeight || columnEls[c].getBoundingClientRect().height || 0; if (h < minH) { minH = h; minCol = columnEls[c]; }
          }
          minCol.appendChild(it);
        }
        if (DEBUG) console.debug('placed item into col', { id: (it.getAttribute && it.getAttribute('data-file-id')) || null, colIndex: columnEls.indexOf(minCol) });
      });

      // Clean up any grid-specific inline styles (gridRowEnd / gridColumn) since we're in column mode,
      // and apply intrinsic aspect ratios from data attributes to media elements so columns measure correctly
      items.forEach((it) => {
        try {
          try { it.style.gridRowEnd = ''; } catch(e){}
          try { it.style.gridColumn = ''; } catch(e){}
          const img = it.querySelector && it.querySelector('img.gallery-img');
          const vid = it.querySelector && it.querySelector('video');
          if (img) {
            const dw = parseInt(img.getAttribute('data-w') || img.dataset && img.dataset.w || 0, 10) || 0;
            const dh = parseInt(img.getAttribute('data-h') || img.dataset && img.dataset.h || 0, 10) || 0;
            if (dw && dh) try { img.style.aspectRatio = dw + ' / ' + dh; img.style.width = '100%'; img.style.height = 'auto'; } catch(e){}
          }
          if (vid) {
            const dw = parseInt(vid.getAttribute('data-w') || vid.dataset && vid.dataset.w || 0, 10) || 0;
            const dh = parseInt(vid.getAttribute('data-h') || vid.dataset && vid.dataset.h || 0, 10) || 0;
            if (dw && dh) try { vid.style.aspectRatio = dw + ' / ' + dh; vid.style.width = '100%'; vid.style.height = 'auto'; } catch(e){}
          }
        } catch(e){}
      });

  // constrain wrapper width to avoid horizontal overflow during reflow
  wrapper.style.width = '100%'; wrapper.style.boxSizing = 'border-box';
  gal.appendChild(wrapper);
      if (DEBUG) console.debug('appended wrapper children', { wrapperChildren: wrapper.children.length });
    } catch (e) { /* fall back to grid */ }
  }

  function setTileAspectRatio(img) {
    try {
      if (!img) return; const tile = img.closest('.gallery-item'); if (!tile) return;
      let w = img.naturalWidth || img.width || img.clientWidth; let h = img.naturalHeight || img.height || img.clientHeight;
      if (!w || !h) { const r = img.getBoundingClientRect(); w = r.width; h = r.height; }
      if (w && h) { img.style.aspectRatio = String(w) + ' / ' + String(h); img.style.width = '100%'; img.style.height = 'auto'; img.style.objectFit = 'cover'; }
    } catch (e) { /* ignore */ }
  }

  // small debounce helper used for resize/reflow
  function debounce(fn, wait) {
    let t = null;
    return function () {
      const args = arguments; const ctx = this;
      clearTimeout(t);
      t = setTimeout(function () { try { fn.apply(ctx, args); } catch (e) {} }, wait || 100);
    };
  }

  function setTileHeightFromVideo(video) {
    try { if (!video) return; const tile = video.closest('.gallery-item'); if (!tile) return; const vw = video.videoWidth || video.clientWidth || video.getBoundingClientRect().width; const vh = video.videoHeight || video.clientHeight || video.getBoundingClientRect().height; if (vw && vh) { video.style.aspectRatio = String(vw) + ' / ' + String(vh); video.style.width = '100%'; video.style.height = 'auto'; video.style.objectFit = 'cover'; } } catch (e) {}
  }

  // Lightbox
  function renderLightbox() {
    const img = document.getElementById('lightbox-img'); const vid = document.getElementById('lightbox-video'); if (!img || !vid) return;
    if (!Array.isArray(files) || files.length === 0 || currentIndex < 0 || currentIndex >= files.length) return;
    const f = files[currentIndex]; if (!f) return;
    try { vid.pause(); vid.removeAttribute('src'); if (typeof vid.load === 'function') vid.load(); vid.onended = null; } catch (e) {}
    img.removeAttribute('src'); img.alt = '';
    const lbContent = document.querySelector('.lightbox-content');
    if (f.type === 'image') {
      const hasThumb = !!(f.thumb_url);
      if (lbContent) {
        if (window.__slideshowPlaying === true || hasThumb) lbContent.classList.remove('loading'); else lbContent.classList.add('loading');
      }
      vid.style.display = 'none'; img.style.display = ''; img.alt = f.name || '';
        // If server provided intrinsic dimensions, preserve them for reflow before load
        if (f.width && f.height) { img.setAttribute('data-w', String(f.width)); img.setAttribute('data-h', String(f.height)); img.dataset.w = String(f.width); img.dataset.h = String(f.height); }
        else if (f.thumb_w && f.thumb_h) { img.setAttribute('data-w', String(f.thumb_w)); img.setAttribute('data-h', String(f.thumb_h)); img.dataset.w = String(f.thumb_w); img.dataset.h = String(f.thumb_h); }
      const thumb = f.thumb_url || ''; const fullUrl = f.url || thumb || '';
      if (thumb) img.src = thumb; else if (fullUrl) img.src = fullUrl;
  if (fullUrl && fullUrl !== thumb) { const pre = new Image(); pre.onload = function () { img.src = fullUrl; if (lbContent) lbContent.classList.remove('loading'); }; pre.onerror = function () { if (lbContent) lbContent.classList.remove('loading'); }; pre.src = fullUrl; } else { if (lbContent) lbContent.classList.remove('loading'); }
    } else if (f.type === 'video') {
      if (lbContent) lbContent.classList.remove('loading'); img.style.display = 'none'; vid.style.display = ''; if (f.thumb_url) vid.setAttribute('poster', f.thumb_url); else vid.removeAttribute('poster'); vid.src = f.url || ''; try { vid.load(); } catch (e) {}
    }
        if (f.width && f.height) { vid.setAttribute('data-w', String(f.width)); vid.setAttribute('data-h', String(f.height)); }
  }

  let lastFocusedTile = null;
  function openLightbox(index) { const lb = document.getElementById('lightbox'); if (!lb) return; try { lastFocusedTile = document.activeElement && document.activeElement.classList && document.activeElement.classList.contains('gallery-item') ? document.activeElement : null; } catch (e) { lastFocusedTile = null; } currentIndex = index; renderLightbox(); lb.style.display = 'flex'; try { const c = document.getElementById('lightbox-close'); if (c && c.focus) c.focus(); } catch(e){} }
  function closeLightbox() { const lb = document.getElementById('lightbox'); const vid = document.getElementById('lightbox-video'); try { if (vid) { vid.pause(); vid.removeAttribute('src'); if (typeof vid.load === 'function') vid.load(); vid.onended = null; } } catch (e) {} if (lb) lb.style.display = 'none'; try { if (lastFocusedTile && lastFocusedTile.focus) lastFocusedTile.focus(); } catch(e){} lastFocusedTile = null; }
  function nextSlide() { if (files.length === 0) return; currentIndex = (currentIndex + 1) % files.length; renderLightbox(); }
  function prevSlide() { if (files.length === 0) return; currentIndex = (currentIndex - 1 + files.length) % files.length; renderLightbox(); }

  // Append files received from server -> create tiles using lazy thumbnails
  function appendFiles(items) {
    const gal = document.getElementById('gallery'); if (!gal || !Array.isArray(items) || items.length === 0) return;
    const seen = (window.__gallerySeenIds instanceof Set) ? window.__gallerySeenIds : (window.__gallerySeenIds = new Set(files.map(f => f.id)));
    const unique = [];
    for (const it of items) { if (!it || typeof it.id !== 'number') continue; if (seen.has(it.id)) continue; seen.add(it.id); unique.push(it); }
    if (unique.length === 0) return;
    const startIndex = files.length; files.push(...unique);

    unique.forEach((file, i) => {
      const idx = startIndex + i; const isVideo = file.type === 'video'; const cls = isVideo ? 'gallery-item gallery-large gallery-video-tile gallery-clickable' : 'gallery-item gallery-clickable';
      const tile = document.createElement('div'); tile.className = cls; tile.setAttribute('data-index', String(idx)); tile.setAttribute('data-name', file.name || ''); tile.setAttribute('data-datetime', file.datetime || ''); tile.setAttribute('data-file-id', String(file.id));
      const chk = document.createElement('input'); chk.type = 'checkbox'; chk.className = 'select-chk'; chk.setAttribute('data-id', String(file.id)); tile.appendChild(chk);

      if (file.type === 'image') {
        const img = document.createElement('img'); img.className = 'gallery-img lazy'; img.alt = file.name || ''; img.dataset.src = file.thumb_url || file.url || '';
        if (file.url) img.setAttribute('data-full', file.url);
        if (file.srcset) { img.dataset.srcset = file.srcset; img.dataset.sizes = '(max-width: 640px) 45vw, (max-width: 1024px) 30vw, 20vw'; }
        // Prefer server-provided intrinsic dims so we can size the tile immediately
        if (file.width && file.height) { try { tile.style.aspectRatio = String(file.width) + ' / ' + String(file.height); } catch(e){} img.setAttribute('data-w', String(file.width)); img.setAttribute('data-h', String(file.height)); }
        else if (file.thumb_w && file.thumb_h) { try { tile.style.aspectRatio = String(file.thumb_w) + ' / ' + String(file.thumb_h); } catch(e){} img.setAttribute('data-w', String(file.thumb_w)); img.setAttribute('data-h', String(file.thumb_h)); }
        // Make the image fill the tile to avoid letterboxing/pillarboxing
        img.style.width = '100%'; img.style.height = '100%'; img.style.objectFit = 'cover';
        img.addEventListener('load', function () { try { setTileAspectRatio(img); reflowGalleryMasonry(); } catch (e) {} }, { once: true });
        tile.appendChild(img); lazyObserver.observe(img);
      } else if (file.type === 'video') {
        const v = document.createElement('video'); v.src = file.url || ''; v.className = 'gallery-video'; v.controls = true; v.preload = 'metadata';
        if (file.width && file.height) { try { tile.style.aspectRatio = String(file.width) + ' / ' + String(file.height); } catch(e){} v.setAttribute('data-w', String(file.width)); v.setAttribute('data-h', String(file.height)); }
        v.style.width = '100%'; v.style.height = '100%'; v.style.objectFit = 'cover';
        v.addEventListener('loadedmetadata', function () { try { setTileHeightFromVideo(v); reflowGalleryMasonry(); } catch (e) {} }, { once: true }); tile.appendChild(v);
      }

  if (file.type === 'video') { const badge = document.createElement('div'); badge.className = 'tile-badge video'; badge.title = 'Video'; badge.textContent = '▶'; tile.appendChild(badge); }
  if (file.deleted && !window.__showDeletedMode) { const badge = document.createElement('div'); badge.className = 'tile-badge deleted'; badge.title = 'Deleted'; badge.textContent = 'Deleted'; tile.appendChild(badge); }
  const fav = document.createElement('button'); fav.className = 'fav-btn' + (file.favorite ? ' is-fav' : ''); fav.title = file.favorite ? 'Unfavorite' : 'Favorite'; fav.setAttribute('data-id', String(file.id)); fav.textContent = file.favorite ? '★' : '☆'; tile.appendChild(fav);

      tile.addEventListener('click', (ev) => { const t = ev.target; if (t && (t.tagName === 'INPUT' || t.tagName === 'BUTTON')) return; const fid = parseInt(tile.getAttribute('data-file-id') || '-1', 10); if (isNaN(fid)) return; const realIdx = files.findIndex(f => f && f.id === fid); if (realIdx >= 0) openLightbox(realIdx); });

      // If we currently have a masonry column wrapper, deterministically insert the tile
      // into column = (globalIndex % columnCount) so that appended pages preserve
      // left-to-right / top-to-bottom ordering across infinite-scroll loads.
      const currentWrapper = gal.querySelector(':scope > .masonry-columns');
      if (currentWrapper) {
        const cols = Array.from(currentWrapper.querySelectorAll('.masonry-column'));
        if (cols && cols.length) {
          // Use the global index (startIndex + i) to pick the column deterministically.
          const colIndex = (idx % cols.length + cols.length) % cols.length;
          const targetCol = cols[colIndex];
          targetCol.appendChild(tile);
          if (DEBUG) console.debug('appendFiles inserted into deterministic column', { fileId: file.id, colIndex, colCount: cols.length });
        } else {
          gal.appendChild(tile);
          if (DEBUG) console.debug('appendFiles fallback appended to gallery container', { fileId: file.id });
        }
      } else {
        gal.appendChild(tile);
        if (DEBUG) console.debug('appendFiles no wrapper, appended to gallery', { fileId: file.id });
      }
    });

    // After appended, reflow masonry
    setTimeout(() => { try { reflowGalleryMasonry(); renderColumnMasonry(); } catch (e) {} }, 60);
  }

  // Infinite scroll fetcher
  function initInfiniteScroll() {
    const gal = document.getElementById('gallery'); if (!gal) return;
    // Parse next-offset (template may render empty string when no more pages)
    let nextOffsetRaw = gal.getAttribute('data-next-offset');
    let nextOffset = (nextOffsetRaw === null || nextOffsetRaw === '') ? null : parseInt(nextOffsetRaw, 10);
    const pageSize = parseInt(gal.getAttribute('data-page-size') || '100', 10);
    let loading = false; let done = nextOffset === null; const loader = document.getElementById('gallery-loader');

    function fetchMore() {
      if (loading || done) { try { console.log('[GalleryModule] fetchMore skipped loading=' + loading + ' done=' + done + ' nextOffset=' + nextOffset); } catch(e){}; return; }
      loading = true; if (loader) loader.style.display = 'block';
      try { console.log('[GalleryModule] fetchMore start nextOffset=', nextOffset, 'pageSize=', pageSize); } catch(e){}
      const skeletons = [];
      // Compute start index (current loaded files) so skeletons place consistently with final tiles
      const startIndex = (Array.isArray(files) ? files.length : 0);
      // If there is an existing masonry wrapper, place skeletons into the shortest column
      const curWrapper = gal.querySelector(':scope > .masonry-columns');
      const skeletonCount = Math.min(12, Math.max(6, Math.floor(pageSize / 10)));
      for (let i = 0; i < skeletonCount; i++) {
        const sk = document.createElement('div'); sk.className = 'gallery-item skeleton';
        if (curWrapper) {
          const cols = Array.from(curWrapper.querySelectorAll('.masonry-column'));
          if (cols && cols.length) {
            // Place skeletons deterministically round-robin to match final tile placement
            const colIndex = (startIndex + i) % cols.length;
            cols[colIndex].appendChild(sk);
          } else {
            gal.appendChild(sk);
          }
        } else {
          gal.appendChild(sk);
        }
        skeletons.push(sk);
      }
  const params = new URLSearchParams(window.location.search); params.set('offset', String(nextOffset || 0)); params.set('limit', String(pageSize));
      fetch('/gallery/data?' + params.toString(), { headers: { 'accept': 'application/json' }, credentials: 'same-origin' })
        .then((r) => {
          const ct = (r.headers && r.headers.get) ? (r.headers.get('content-type') || '') : '';
          // If we were redirected to HTML (login) or got a non-JSON response, stop and redirect to login
          if (!r.ok) {
            if (r.status === 401 || r.status === 403 || r.redirected) {
              window.location.href = '/login';
              throw new Error('auth');
            }
            return r.text().then(() => { throw new Error('bad-status'); });
          }
          if (!ct.includes('application/json')) {
            // likely an HTML login page or error page — redirect to login to recover
            window.location.href = '/login';
            throw new Error('not-json');
          }
          return r.json();
        })
        .then((resp) => {
          if (!resp || resp.ok !== true) return; appendFiles(resp.files || []);
          try { console.log('[GalleryModule] fetchMore response files=', (resp.files && resp.files.length) || 0, 'next_offset=', resp.next_offset); } catch(e){}
          if (resp.next_offset != null && resp.next_offset !== '') {
            nextOffset = resp.next_offset; done = false;
          } else {
            nextOffset = null; done = true; const end = document.getElementById('gallery-end'); if (end) end.style.display = 'block';
          }
        })
        .catch(() => {
          /* swallow network/json parse errors after handling redirects */
        })
        .finally(() => { 
          skeletons.forEach(el => el.remove()); 
          loading = false; 
          try { console.log('[GalleryModule] fetchMore finished loading=' + loading + ' done=' + done + ' nextOffset=' + nextOffset); } catch(e){}
          if (loader) loader.style.display = done ? 'none' : 'block'; 
        });
      // collapse detection lives in renderColumnMasonry (it knows wrapper state); nothing to do here
    }

  // Expose a programmatic trigger for tests and boot
  try { window.fetchMoreGallery = fetchMore; } catch (e) {}

    // Keep a fallback scroll listener but also use an IntersectionObserver sentinel which is more reliable
    window.addEventListener('scroll', function () { if (done || loading) return; try { const scrollPos = window.scrollY + window.innerHeight; const nearBottom = document.body.offsetHeight - 400; if (scrollPos >= nearBottom) fetchMore(); } catch(e) {} });

    try {
      // Ensure there's a sentinel element we can observe at the end of the gallery
      let sentinel = document.getElementById('gallery-sentinel');
      if (!sentinel) {
        sentinel = document.createElement('div'); sentinel.id = 'gallery-sentinel'; sentinel.style.width = '100%'; sentinel.style.height = '2px'; sentinel.style.display = 'block';
        const endEl = document.getElementById('gallery-end'); if (endEl && endEl.parentNode) endEl.parentNode.insertBefore(sentinel, endEl); else gal.appendChild(sentinel);
      }
      if ('IntersectionObserver' in window) {
        try { console.log('[GalleryModule] setting up infinite sentinel observer, done=', done, 'nextOffset=', nextOffset); } catch(e){}
        const obs = new IntersectionObserver((entries) => {
          entries.forEach(en => { try { if (en.isIntersecting) { console.log('[GalleryModule] sentinel intersecting'); if (!loading && !done) fetchMore(); } } catch(e) {} });
        }, { root: null, rootMargin: '800px', threshold: 0.01 });
        obs.observe(sentinel);
        try { window._galleryInfiniteObserver = obs; } catch (e) {}
      }
    } catch (e) {}
  }

  // Boot / init
  function boot() {
    try {
      const dataEl = document.getElementById('gallery-data'); const parsed = dataEl ? JSON.parse(dataEl.textContent) : null;
      if (parsed && Array.isArray(parsed)) { window.galleryFiles = parsed; } else if (parsed && parsed.files && Array.isArray(parsed.files)) { window.galleryFiles = parsed.files; window.__gallery_meta = parsed; } else { window.galleryFiles = []; }
      files = Array.isArray(window.galleryFiles) ? window.galleryFiles.slice() : [];
      window.files = files;
      window.__showDeletedMode = !!(dataEl && dataEl.dataset && dataEl.dataset.showDeleted === '1');
  // Diagnostic: confirm module booted and initial file count
  try { console.log('[GalleryModule] booted, files=', files.length); } catch(e){}
    } catch (e) { window.galleryFiles = []; }

  ['delete-form', 'restore-form', 'zip-form'].forEach(wireSelection);
  // Initialize bulk action UI wiring (select counts, enable/disable action buttons)
  try { if (!window.initBulkBar) window.initBulkBar = function() {
      const bulkBar = document.getElementById('bulk-bar');
      const bulkCount = document.getElementById('bulk-count');
      const btnClear = document.getElementById('bb-clear');
      const btnDelete = document.getElementById('bb-delete');
      const btnRestore = document.getElementById('bb-restore');
      const btnZip = document.getElementById('bb-zip');
      const btnAdd = document.getElementById('bb-add-to-album');
  const selectAllBtn = document.getElementById('select-all');
      function getSelectedIds(){ return Array.from(document.querySelectorAll('.select-chk:checked')).map(i=>parseInt(i.getAttribute('data-id'))).filter(i=>!isNaN(i)); }
      // Select All behavior:
      // - Default click: select ALL items across the current filter scope (server-backed)
      // - Alt/Ctrl click: toggle only currently visible tiles
      if (selectAllBtn){
        selectAllBtn.addEventListener('click', function(ev){
          try {
            ev.preventDefault();
            const galEl = document.getElementById('gallery');
            const onlyVisible = !!(ev.altKey || ev.ctrlKey);
            if (!onlyVisible){
              const u = new URL(window.location.href);
              const params = new URLSearchParams();
              const type = u.searchParams.get('type') || '';
              const fav = u.searchParams.get('favorites') || '';
              const del = u.searchParams.get('show_deleted') || '';
              const album = u.searchParams.get('album_id') || '';
              if (type) params.set('type', type);
              if (fav) params.set('favorites', fav);
              if (del) params.set('show_deleted', del);
              if (album) params.set('album_id', album);
              fetch('/gallery/ids' + (params.toString() ? ('?' + params.toString()) : ''), { credentials: 'same-origin' })
                .then(r => r.ok ? r.json() : Promise.reject(r))
                .then(j => {
                  const ids = (j && Array.isArray(j.ids)) ? j.ids : [];
                  if (!ids.length) return;
                  ids.forEach(function(id){ const chk = document.querySelector('.select-chk[data-id="' + id + '"]'); if (chk) { try { chk.checked = true; } catch(_){} } });
                  // no toast on select-all per request
                  if (typeof updateSelectionUI === 'function') updateSelectionUI();
                })
                .catch(()=>{});
              return;
            }
            // Alt/Ctrl: toggle visible selection only
            const visible = Array.from(document.querySelectorAll('#gallery .gallery-item .select-chk'));
            const allChecked = visible.length>0 && visible.every(chk=>chk && chk.checked);
            visible.forEach(chk=>{ try { chk.checked = !allChecked; } catch(_){} });
            if (typeof updateSelectionUI === 'function') updateSelectionUI();
          } catch(e){}
        });
      }
  if (btnClear) btnClear.addEventListener('click', function(ev){ try { ev.preventDefault(); Array.from(document.querySelectorAll('.select-chk:checked')).forEach(c=>{ try { c.checked=false; } catch(_){} }); if (typeof updateSelectionUI === 'function') updateSelectionUI(); } catch(e){} });
      if (btnDelete) btnDelete.addEventListener('click', function(){
        try {
          const ids = getSelectedIds();
          try { console.log('[GalleryModule] bb-delete clicked, selected ids=', ids); } catch(e){}
          if (!ids.length) return;
          const dlg = document.getElementById('delete-confirm'); if (dlg) dlg.style.display='flex';
        } catch (e) { }
      });
      if (btnRestore) btnRestore.addEventListener('click', function(){ const ids = getSelectedIds(); if (!ids.length) return; const form = document.getElementById('restore-form'); if (form){ Array.from(form.querySelectorAll('input[name="file_ids"]')).forEach(i=>i.remove()); ids.forEach(id=>{ const h = document.createElement('input'); h.type='hidden'; h.name='file_ids'; h.value=String(id); form.appendChild(h); } );
        // Ensure CSRF hidden input is present (template should render it); as a fallback, inject from meta
        try {
          let csrfInput = form.querySelector('input[name="csrf_token"]');
          if (!csrfInput) {
            const meta = document.querySelector('meta[name="csrf-token"]');
            if (meta && meta.content) {
              csrfInput = document.createElement('input'); csrfInput.type='hidden'; csrfInput.name='csrf_token'; csrfInput.value = meta.content; form.appendChild(csrfInput);
            }
          }
        } catch(e){}
        form.submit(); } });
      if (btnZip) btnZip.addEventListener('click', function(){ const ids = getSelectedIds(); if (!ids.length) return; const form = document.getElementById('zip-form'); if (form){ Array.from(form.querySelectorAll('input[name="file_ids"]')).forEach(i=>i.remove()); ids.forEach(id=>{ const h = document.createElement('input'); h.type='hidden'; h.name='file_ids'; h.value=String(id); form.appendChild(h); } ); form.submit(); } });
      if (btnAdd) btnAdd.addEventListener('click', function(){ const ids = getSelectedIds(); if (!ids.length) return; if (typeof openAddToAlbumModal === 'function') openAddToAlbumModal(ids); });
      // Wire confirm delete inside modal to submit delete-form
      const delConfirmBtn = document.getElementById('del-confirm');
      if (delConfirmBtn) {
        delConfirmBtn.addEventListener('click', function(){
          try {
            const ids = getSelectedIds();
            try { console.log('[GalleryModule] del-confirm clicked, selected ids=', ids); } catch(e){}
            if (!ids.length) return;
            const form = document.getElementById('delete-form');
            if (!form) return;
            // Log target form attributes before mutating
            try { console.log('[GalleryModule] delete-form before mutation action=', form.getAttribute('action'), 'method=', form.getAttribute('method')); } catch(e){}
            // Remove any previous hidden inputs and append current selection
            Array.from(form.querySelectorAll('input[name="file_ids"]')).forEach(i=>i.remove());
            ids.forEach(id=>{ const h = document.createElement('input'); h.type='hidden'; h.name='file_ids'; h.value=String(id); form.appendChild(h); } );
            // Log what was appended
            try {
              const added = Array.from(form.querySelectorAll('input[name="file_ids"]')).map(i=>i.value);
              console.log('[GalleryModule] delete-form inputs now=', added);
            } catch(e){}

            // Attempt a normal form submit, but always send an unconditional fetch as
            // a reliable path. We prefer form.submit() for compatibility, but some
            // environments may prevent navigation. The fetch ensures the server sees
            // the request and lets us update the UI immediately.
            // Build a fresh FormData and POST it (do NOT call form.submit() because
            // that may trigger a full navigation before our fetch completes).
            try {
              const action = form.getAttribute('action') || window.location.pathname;
              const method = (form.getAttribute('method') || 'POST').toUpperCase();
              const fd = new FormData();
              ids.forEach(id => fd.append('file_ids', String(id)));
              // Include CSRF token from hidden input or meta tag
              try {
                const csrfFromForm = (form.querySelector('input[name="csrf_token"]') || {}).value;
                const meta = document.querySelector('meta[name="csrf-token"]');
                const csrf = csrfFromForm || (meta && meta.content) || '';
                if (csrf) fd.append('csrf_token', csrf);
              } catch(e){}
              console.log('[GalleryModule] sending fetch delete to', action, 'ids=', ids);
              fetch(action, { method: method, body: fd, credentials: 'same-origin', headers: { 'Accept': 'application/json' } })
                .then(r => {
                  const ct = (r.headers && r.headers.get) ? (r.headers.get('content-type') || '') : '';
                  // If the response indicates an auth problem, redirect user to login.
                  if (r.status === 401 || r.status === 403) {
                    try { console.warn('[GalleryModule] delete response 401/403 — redirecting to login'); } catch(e){}
                    try { window.location.href = '/login'; } catch(e){}
                    throw new Error('not-authorized');
                  }
                  // If the fetch followed a redirect, it's often a 303 -> /gallery success.
                  // Only treat it as an auth redirect if the final URL looks like the login page.
                  if (r.redirected) {
                    try {
                      const u = r.url || '';
                      if (u.indexOf('/login') !== -1 || u.indexOf('/auth') !== -1) {
                        try { window.location.href = u; } catch(e){}
                        throw new Error('not-authorized-redirect');
                      }
                      // Otherwise proceed — this was likely a 303 back to /gallery which is success
                    } catch(e) {}
                  }
                  if (!r.ok) throw new Error('delete-failed');
                  // Prefer JSON responses when available to confirm success
                  if (ct && ct.indexOf('application/json') !== -1) return r.json().catch(() => ({}));
                  return r.text();
                })
                .then(() => {
                  try {
                    // Close modal if present
                    const dlg = document.getElementById('delete-confirm'); if (dlg) dlg.style.display = 'none';
                    // Remove tiles from the DOM and clear selection
                    ids.forEach(id => {
                      try {
                        const chk = document.querySelector('.select-chk[data-id="' + id + '"]');
                        if (chk) {
                          const tile = chk.closest && chk.closest('.gallery-item');
                          if (tile) tile.remove();
                        }
                        // Update local files array if present
                        try { const idx = files.findIndex(f => String(f.id) === String(id) || f.id === id); if (idx >= 0) files[idx].deleted = true; } catch(e){}
                      } catch(e){}
                    });
                    if (typeof updateSelectionUI === 'function') updateSelectionUI();
                  } catch (e) { console.error('[GalleryModule] post-delete UI update error', e); }
                })
                .catch(err => { console.error('[GalleryModule] delete fetch failed', err); })
                .finally(() => { try { if (window.EPU && window.EPU.snackbar) window.EPU.snackbar.show('Deleted successfully'); } catch(_){} });
            } catch (e) { console.error('[GalleryModule] delete fetch construction error', e); }
          } catch (e) { console.error('[GalleryModule] del-confirm handler error', e); }
        });
      }
      // Expose updateSelectionUI
      if (typeof window.updateSelectionUI !== 'function') window.updateSelectionUI = function(){
        try{
          const ids = getSelectedIds(); const n = ids.length;
          // Diagnostic logging for selection state
          try { console.log('[GalleryModule] updateSelectionUI selected=', ids, 'count=', n); } catch(e){}
          if (bulkBar && bulkCount) { bulkCount.textContent = n + (n===1? ' selected' : ' selected'); bulkBar.style.display = n>0? 'block' : 'none'; }
          if (btnDelete) btnDelete.disabled = n===0;
          // Restore button should only be visible when at least one selected file is deleted.
          try {
            const anyDeleted = ids.length > 0 && ids.some(id => { const f = getFileById(id); return f && !!f.deleted; });
            if (btnRestore) {
              btnRestore.style.display = anyDeleted ? '' : 'none';
              btnRestore.disabled = !anyDeleted;
            }
          } catch (e) { if (btnRestore) { btnRestore.style.display = 'none'; btnRestore.disabled = true; } }
          if (btnZip) btnZip.disabled = n===0;
          if (btnAdd) btnAdd.disabled = n===0;
          try { document.querySelectorAll('.fav-btn').forEach(function(b){ b.setAttribute('aria-pressed', b.classList.contains('is-fav') ? 'true' : 'false'); }); } catch(e){}
          // Log resulting display state for the bulk bar
          try { console.log('[GalleryModule] bulk-bar display=', bulkBar ? bulkBar.style.display : 'missing'); } catch(e){}
        }catch(e){}
      };
      // Initial state
      window.updateSelectionUI(); } } catch (e) {}
    // Ensure checkbox changes update the bulk UI
    try {
      const galEl = document.getElementById('gallery');
      if (galEl) {
        // Keyboard navigation: Enter/Space on a focused tile opens lightbox
        galEl.addEventListener('keydown', function(ev){
          try {
            const t = ev.target;
            if (!t || !t.classList || !t.classList.contains('gallery-item')) return;
            if (ev.key === 'Enter' || ev.key === ' ') {
              ev.preventDefault();
              const fidAttr = t.getAttribute('data-file-id');
              let idx = -1;
              if (fidAttr) {
                const fid = parseInt(fidAttr, 10);
                idx = files.findIndex(f => f && f.id === fid);
              }
              if (idx >= 0) openLightbox(idx);
            }
          } catch(e){}
        });
        galEl.addEventListener('change', function(ev){
          try { const t = ev.target; if (t && t.classList && t.classList.contains('select-chk')) { if (typeof updateSelectionUI === 'function') updateSelectionUI(); } } catch(e){}
        });
        // Also handle direct clicks on checkboxes (some environments may not reliably
        // fire/bubble change events for programmatic toggles). Delegate click so
        // the bulk bar updates immediately when a checkbox is clicked.
        galEl.addEventListener('click', function(ev){
          try {
            const t = ev.target;
            if (t && t.classList && t.classList.contains('select-chk')) {
              try { console.log('[GalleryModule] select-chk click id=', t.getAttribute('data-id')); } catch(e){}
              if (typeof updateSelectionUI === 'function') {
                updateSelectionUI();
                return;
              }
              // Fallback: inline update in case initBulkBar hasn't run yet
              try {
                const bulkBar = document.getElementById('bulk-bar');
                const bulkCount = document.getElementById('bulk-count');
                const btnDelete = document.getElementById('bb-delete');
                const btnRestore = document.getElementById('bb-restore');
                const btnZip = document.getElementById('bb-zip');
                const btnAdd = document.getElementById('bb-add-to-album');
                const ids = Array.from(document.querySelectorAll('.select-chk:checked')).map(i=>parseInt(i.getAttribute('data-id'))).filter(i=>!isNaN(i));
                const n = ids.length;
                if (bulkBar && bulkCount) { try { bulkCount.textContent = n + (n===1? ' selected' : ' selected'); bulkBar.style.display = n>0? 'block' : 'none'; } catch(e){} }
                if (btnDelete) btnDelete.disabled = n===0;
                try {
                  const anyDeleted = ids.length > 0 && ids.some(id => { const f = (typeof getFileById === 'function') ? getFileById(id) : null; return f && !!f.deleted; });
                  if (btnRestore) {
                    btnRestore.style.display = anyDeleted ? '' : 'none';
                    btnRestore.disabled = !anyDeleted;
                  }
                } catch(e) { if (btnRestore) { btnRestore.style.display = 'none'; btnRestore.disabled = true; } }
                if (btnZip) btnZip.disabled = n===0;
                if (btnAdd) btnAdd.disabled = n===0;
                try { console.log('[GalleryModule] fallback updateSelectionUI selected=', ids, 'count=', n, 'bulk display=', bulkBar ? bulkBar.style.display : 'missing'); } catch(e){}
              } catch(e){}
            }
            // If click was on media, ensure lightbox opens
            const tile = t.closest && t.closest('.gallery-item');
            if (!tile) return;
            const onMedia = t && (t.tagName === 'IMG' || t.tagName === 'VIDEO');
            if (onMedia){
              const fid = parseInt(tile.getAttribute('data-file-id') || '-1', 10);
              if (!isNaN(fid)){
                const realIdx = files.findIndex(f => f && f.id === fid);
                if (realIdx >= 0) openLightbox(realIdx);
              }
            }
          } catch(e){}
        });
        // Toggle checkbox when user clicks a tile (but not when clicking the media or controls)
        galEl.addEventListener('mousedown', function(ev){
          try {
            const tile = ev.target.closest && ev.target.closest('.gallery-item');
            if (!tile) return;
            const checkbox = tile.querySelector && tile.querySelector('.select-chk');
            if (!checkbox) return;
            // Determine if click was on media (IMG/VIDEO) or interactive control
            const isClickOnMedia = ev.target && (ev.target.tagName === 'IMG' || ev.target.tagName === 'VIDEO' || ev.target.classList && ev.target.classList.contains('tile-overlay'));
            if (!isClickOnMedia && !ev.target.classList.contains('select-chk')){
              // toggle selection and update UI
              checkbox.checked = !checkbox.checked;
              if (typeof updateSelectionUI === 'function') updateSelectionUI();
              // prevent the click from also opening lightbox
              ev.preventDefault();
            }
          } catch (e) { /* ignore */ }
        });
      }
    } catch(e){}
  initFilters(); try { if (typeof window.initBulkBar === 'function') window.initBulkBar(); } catch (e) {}
  try { initFavoriteToggle(); } catch (e) {}
  // Slideshow is now a dedicated page at /live/{code}; legacy lightbox slideshow removed
    initInfiniteScroll(); try { if (typeof updateSelectionUI === 'function') updateSelectionUI(); } catch (e) {}
    // Try to pre-load more files on initial page load if we have fewer than a page
    try {
      const galEl = document.getElementById('gallery');
      const pageSize = parseInt(galEl && galEl.getAttribute ? (galEl.getAttribute('data-page-size') || '100') : '100', 10);
      const curCount = Array.isArray(files) ? files.length : 0;
      // If server indicates there are more files (data-next-offset present) and we have fewer than pageSize, trigger a fetch.
      const nextRaw = galEl && galEl.getAttribute ? galEl.getAttribute('data-next-offset') : null;
      if ((nextRaw !== null && nextRaw !== '') && curCount < pageSize) {
        try { if (typeof window.fetchMoreGallery === 'function') window.fetchMoreGallery(); else { /* fallback: simulate scroll to trigger fetch */ window.dispatchEvent(new Event('scroll')); } } catch(e){}
      }
    } catch (e) {}

    // If template rendered some initial tiles, observe and process their images so
    // we can compute accurate tile heights (server-rendered images may already be present)
    try {
      document.querySelectorAll('.gallery-item img.gallery-img').forEach(img => {
        try {
          // If this image is using data-src (lazy pattern) observe it so it will be loaded
          if (img.classList.contains('lazy') || (img.dataset && img.dataset.src)) lazyObserver.observe(img);

          // If the image is already decoded/loaded, set its aspect and let the masonry reflow pick it up
          if (img.complete && img.naturalWidth) {
            setTileAspectRatio(img);
          } else {
            // Otherwise attach a load listener to set aspect and reflow when ready
            img.addEventListener('load', function () {
              try { setTileAspectRatio(img); reflowGalleryMasonry(); } catch (e) {}
            }, { once: true });
          }
        } catch (e) { /* per-image */ }
      });
    } catch (e) {}

    // Reflow on window resize, debounced to avoid thrash
    try { window.addEventListener('resize', debounce(reflowGalleryMasonry, 120)); } catch (e) {}

  // Wire lightbox controls
  try { const lbCloseEl = document.getElementById('lightbox-close'); if (lbCloseEl) lbCloseEl.addEventListener('click', closeLightbox); } catch (e) {}
  try { const lbNextEl = document.getElementById('lb-next'); if (lbNextEl) lbNextEl.addEventListener('click', nextSlide); } catch (e) {}
  try { const lbPrevEl = document.getElementById('lb-prev'); if (lbPrevEl) lbPrevEl.addEventListener('click', prevSlide); } catch (e) {}
  try {
    const newAlbumEl = document.getElementById('new-album');
    if (newAlbumEl) newAlbumEl.addEventListener('click', function (ev) {
      try {
        ev.preventDefault(); ev.stopPropagation();
        if (typeof openCreateAlbumModal === 'function') { openCreateAlbumModal(); return; }
        const modal = document.getElementById('create-album-modal');
        if (modal) { modal.style.display = 'flex'; }
      } catch(_){}
    });
  } catch (e) {}
    document.addEventListener('keydown', (e) => {
      const lb = document.getElementById('lightbox');
      if (!lb || lb.style.display === 'none') return;
      if (e.key === 'Escape') {
        try { window.__slideshowPlaying = false; } catch (_) {}
        try { const v = document.getElementById('lightbox-video'); if (v) v.pause(); } catch (_) {}
        try { const lbPause = document.getElementById('lb-pause'); const lbPlay = document.getElementById('lb-play'); const lbDelayGroup = document.getElementById('lb-delay-group'); if (lbPause) lbPause.style.display='none'; if (lbPlay) lbPlay.style.display=''; if (lbDelayGroup) lbDelayGroup.style.display='none'; } catch(_){}
        closeLightbox();
      } else if (e.key === 'ArrowRight') {
        nextSlide();
      } else if (e.key === 'ArrowLeft') {
        prevSlide();
      }
    });

    // Initial reflow after images loaded
    setTimeout(() => { try { reflowGalleryMasonry(); renderColumnMasonry(); } catch (e) {} }, 120);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();

  // Capture-phase click logger to detect clicks before other handlers/extensions
  try {
    document.addEventListener('click', function(ev){
      try {
        const t = ev.target;
        const ids = [];
        if (!t) return;
        if (t.id) ids.push(t.id);
        try { const c = t.closest && (t.closest('#bb-delete') || t.closest('#del-confirm') || t.closest('#del-cancel') || t.closest('#bb-clear') ); if (c && c.id) ids.push(c.id); } catch(e){}
        if (ids.length) {
          try { console.log('[GalleryModule][CAPTURE] click target ids=', ids, 'tag=', t.tagName, 'class=', t.className); } catch(e){}
        }
      } catch(e){}
    }, true);
  } catch(e) {}
 
  // Pause any videos playing in grid (used by slideshow / lightbox)
  function pauseAllGridVideos(){ try { document.querySelectorAll('.gallery video, .dynamic-gallery video').forEach(v=>{ try{ v.pause(); v.currentTime = 0; }catch(_){} }); } catch(_){} }

  // Stable DOM reorder to match canonical `files` array. Adapts to masonry-columns wrapper by
  // removing wrapper, reordering tiles into the gallery container, then recreating column masonry.
  function stableReorderDOM(){
    try{
      const gal = document.getElementById('gallery') || document.querySelector('.dynamic-gallery'); if (!gal) return;
      const idToTile = new Map();
      Array.from(gal.querySelectorAll('.gallery-item')).forEach(tile => {
        try {
          const chk = tile.querySelector && tile.querySelector('.select-chk');
          const id = chk ? parseInt(chk.getAttribute('data-id')) : NaN;
          if (!isNaN(id)) idToTile.set(Number(id), tile);
        } catch (e) {}
      });
      const frag = document.createDocumentFragment();
      files.forEach((f, idx) => {
        const tile = idToTile.get(f.id);
        if (tile) { tile.setAttribute('data-index', String(idx)); frag.appendChild(tile); idToTile.delete(f.id); }
      });
      idToTile.forEach(tile => frag.appendChild(tile));
      // Remove any existing masonry wrapper and replace gallery children with ordered fragment
      const existing = gal.querySelector(':scope > .masonry-columns'); if (existing) existing.remove();
      while (gal.firstChild) gal.removeChild(gal.firstChild);
      gal.appendChild(frag);
      // Re-run column masonry and grid reflow to recreate columns in the new order
      setTimeout(()=>{ try { renderColumnMasonry(); reflowGalleryMasonry(); } catch(e) {} }, 60);
    }catch(e){}
  }

  // Fetch and apply server canonical order for an event (if present)
  function applyServerOrder(eventId){
    if (!eventId) return Promise.resolve();
    return fetch('/events/' + encodeURIComponent(eventId) + '/gallery/order')
      .then(function(r){ if (!r.ok) throw new Error('no-order'); return r.json(); })
      .then(function(j){ if (!j || !j.ok || !Array.isArray(j.files)) throw new Error('bad');
        const newFiles = j.files.map(function(f){ return Object.assign({}, f, { favorite: !!f.favorite }); });
        files = newFiles; window.__gallerySeenIds = new Set(files.map(f=>f.id));
        try { stableReorderDOM(); } catch(e) {}
      }).catch(function(){ /* ignore and keep DOM order */ });
  }

  // Update the Favorites pill count immediately based on current `files` state
  function renderFavoritesCount(){
    try {
      const pill = document.querySelector('.pill-filter[data-filter="favorites"]');
      if (!pill) return;
      const cnt = pill.querySelector('.count');
      if (!cnt) return;
      const total = Array.isArray(files) ? files.filter(f => !!f.favorite).length : 0;
      cnt.textContent = String(total);
      // If favorites filter is active, hide tiles that are not favorited
      const active = pill.getAttribute('aria-pressed') === 'true';
      if (active) {
        try {
          document.querySelectorAll('.gallery-item').forEach(function(tile){
            const chk = tile.querySelector('.select-chk');
            const id = chk ? parseInt(chk.getAttribute('data-id')||'-1',10) : -1;
            const f = files.find(x => x && x.id === id);
            tile.style.display = (f && f.favorite) ? '' : 'none';
          });
          // Reflow layout after visibility changes
          setTimeout(function(){ try { reflowGalleryMasonry(); } catch(_){} }, 30);
        } catch(_){}
      }
    } catch(_){}
  }

  // Favorite toggle: delegate clicks on .fav-btn to POST favorite/unfavorite and update UI
  function initFavoriteToggle(){
    try{
      document.addEventListener('click', function(ev){
        try{
          const t = ev.target;
          if (!t || !t.classList) return;
          if (t.classList.contains('fav-btn')){
            ev.preventDefault(); ev.stopPropagation();
            const id = parseInt(t.getAttribute('data-id'));
            if (!id) return;
            const isFav = t.classList.contains('is-fav');
            const url = isFav ? '/gallery/unfavorite' : '/gallery/favorite';
            const fd = new FormData(); fd.append('file_id', String(id));
            // Optimistically toggle
            t.classList.toggle('is-fav'); t.textContent = t.classList.contains('is-fav') ? '★' : '☆'; t.setAttribute('aria-pressed', t.classList.contains('is-fav') ? 'true' : 'false');
            fetch(url, { method: 'POST', body: fd, credentials: 'same-origin' })
              .then(r => r.json())
              .then(resp => {
                if (!resp || resp.ok !== true){
                  // revert on failure
                  t.classList.toggle('is-fav'); t.textContent = t.classList.contains('is-fav') ? '★' : '☆'; t.setAttribute('aria-pressed', t.classList.contains('is-fav') ? 'true' : 'false');
                } else {
                  try { const idx = files.findIndex(f=>f && f.id===id); if (idx>=0) files[idx].favorite = t.classList.contains('is-fav'); } catch(e){}
                  try { renderFavoritesCount(); } catch(e){}
                }
              })
              .catch(()=>{ try { t.classList.toggle('is-fav'); t.textContent = t.classList.contains('is-fav') ? '★' : '☆'; t.setAttribute('aria-pressed', t.classList.contains('is-fav') ? 'true' : 'false'); } catch(e){} });
          }
        }catch(e){}
      }, false);
    }catch(e){}
  }

  // Legacy lightbox slideshow has been removed in favor of dedicated /live/{code}

  // Public small helpers (if other modules call them)
  return {
    appendFiles, reflowGalleryMasonry, openLightbox,
    closeLightbox, prevSlide, nextSlide,
    stableReorderDOM, applyServerOrder, pauseAllGridVideos
  };
})();

// expose for debugging
window.GalleryModule = G;
