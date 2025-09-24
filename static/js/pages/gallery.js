// Rewritten gallery page module
// Provides: lazy-loading thumbnails, infinite scroll that hits /gallery/data, tile aspect ratio handling,
// lightbox, selection helpers, filters wiring, and bulk actions.

/* globals window, document, fetch, URLSearchParams */

const G = (function () {
  'use strict';

  let files = [];
  let currentIndex = -1;
  const DEBUG = !!(window && window.__GALLERY_DEBUG);

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
      } catch (e) { /* ignore */ }
      obs.unobserve(img);
    });
  }, { rootMargin: '400px', threshold: 0.01 }) : { observe() {}, unobserve() {} };

  // Utility: get file by id from local or initial data
  function getFileById(id) {
    const n = Number(id);
    if (Number.isFinite(n) && Array.isArray(files)) return files.find(x => x && x.id === n) || null;
    try { if (Array.isArray(window.galleryFiles)) return window.galleryFiles.find(x => x && x.id === n) || null; } catch (e) {}
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

      // Build modal container
      let modal = document.getElementById('add-to-album-modal');
      if (modal) modal.remove();
      modal = document.createElement('div'); modal.id = 'add-to-album-modal'; modal.className = 'modal'; modal.setAttribute('role', 'dialog'); modal.setAttribute('aria-modal', 'true'); modal.style.display = 'flex'; modal.style.position = 'fixed'; modal.style.inset = '0'; modal.style.alignItems = 'center'; modal.style.justifyContent = 'center'; modal.style.background = 'rgba(0,0,0,0.5)'; modal.style.zIndex = '1002';

      const content = document.createElement('div'); content.className = 'modal-content'; content.style.maxWidth = '520px'; content.style.padding = '12px'; content.style.boxSizing = 'border-box'; content.style.background = 'rgba(0,0,0,0.85)'; content.style.border = '1px solid var(--color-border)'; content.style.borderRadius = '8px';
      const title = document.createElement('h3'); title.className = 'p-bold'; title.textContent = 'Add selected files to album'; content.appendChild(title);
      const listWrap = document.createElement('div'); listWrap.style.marginTop = '8px'; listWrap.textContent = 'Loading albums…'; content.appendChild(listWrap);

      const actions = document.createElement('div'); actions.style.display = 'flex'; actions.style.justifyContent = 'flex-end'; actions.style.gap = '8px'; actions.style.marginTop = '12px';
      const cancelBtn = document.createElement('button'); cancelBtn.type = 'button'; cancelBtn.className = 'btn'; cancelBtn.textContent = 'Cancel';
      const addBtn = document.createElement('button'); addBtn.type = 'button'; addBtn.className = 'btn primary'; addBtn.textContent = 'Add'; addBtn.disabled = true;
      actions.appendChild(cancelBtn); actions.appendChild(addBtn); content.appendChild(actions);

      modal.appendChild(content); document.body.appendChild(modal);

      function closeModal() { try { modal.remove(); } catch (e) {} }
      cancelBtn.addEventListener('click', closeModal);

      // Fetch albums for this event
      fetch('/events/' + encodeURIComponent(eventId) + '/albums', { credentials: 'same-origin' })
        .then(r => { if (!r.ok) throw new Error('bad'); return r.json(); })
        .then(j => {
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
              r.addEventListener('change', function () { selectedAlbum = this.value; addBtn.disabled = !selectedAlbum; });
              const t = document.createElement('span'); t.textContent = a.name + (a.count ? (' (' + a.count + ')') : '');
              row.appendChild(r); row.appendChild(t); form.appendChild(row);
            } catch (e) {}
          });
          listWrap.appendChild(form);

          addBtn.addEventListener('click', function () {
            if (!selectedAlbum) return;
            addBtn.disabled = true; addBtn.textContent = 'Adding…';
            // Send POST for each file id; run sequentially to avoid DB race concerns
            const promises = ids.map(fid => {
              const fd = new FormData(); fd.append('file_id', String(fid));
              return fetch('/events/' + encodeURIComponent(eventId) + '/albums/' + encodeURIComponent(selectedAlbum) + '/add', {
                method: 'POST', body: fd, credentials: 'same-origin'
              }).then(r => r.ok ? r.json().catch(()=>({ok:true})) : Promise.reject(r));
            });
            Promise.all(promises).then(() => {
              try { closeModal(); } catch (e) {}
            }).catch(() => {
              try { addBtn.disabled = false; addBtn.textContent = 'Add'; } catch (e) {}
            });
          });
        })
        .catch(() => {
          listWrap.innerHTML = ''; const err = document.createElement('div'); err.className = 'muted'; err.textContent = 'Unable to load albums.'; listWrap.appendChild(err);
        });

    } catch (e) { /* ignore */ }
  }

  // expose helper to global scope in case other inline scripts expect it
  try { window.openAddToAlbumModal = openAddToAlbumModal; } catch (e) {}

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
          let h = Math.round(child.getBoundingClientRect().height) || child.offsetHeight || 0;
          h = Math.min(maxTile, Math.max(h, 40));
          const span = Math.max(1, Math.ceil((h + rowGap) / (rowHeight + rowGap)));
          child.style.gridRowEnd = 'span ' + String(span);
          if (child.classList && child.classList.contains('group-heading')) child.style.gridColumn = '1 / -1';
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
          // Insert heading as a full-width row between columns
          const headingWrap = document.createElement('div'); headingWrap.style.width = '100%'; headingWrap.style.display = 'flex'; headingWrap.style.flexBasis = '100%'; headingWrap.style.boxSizing = 'border-box'; headingWrap.appendChild(it);
          wrapper.appendChild(headingWrap);
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
      if (lbContent) lbContent.classList.add('loading'); vid.style.display = 'none'; img.style.display = ''; img.alt = f.name || '';
      const thumb = f.thumb_url || ''; const fullUrl = f.url || thumb || '';
      if (thumb) img.src = thumb; else if (fullUrl) img.src = fullUrl;
      if (fullUrl && fullUrl !== thumb) { const pre = new Image(); pre.onload = function () { img.src = fullUrl; if (lbContent) lbContent.classList.remove('loading'); }; pre.onerror = function () { if (lbContent) lbContent.classList.remove('loading'); }; pre.src = fullUrl; } else { if (lbContent) lbContent.classList.remove('loading'); }
    } else if (f.type === 'video') {
      if (lbContent) lbContent.classList.remove('loading'); img.style.display = 'none'; vid.style.display = ''; if (f.thumb_url) vid.setAttribute('poster', f.thumb_url); else vid.removeAttribute('poster'); vid.src = f.url || ''; try { vid.load(); } catch (e) {}
    }
  }

  function openLightbox(index) { const lb = document.getElementById('lightbox'); if (!lb) return; currentIndex = index; renderLightbox(); lb.style.display = 'flex'; }
  function closeLightbox() { const lb = document.getElementById('lightbox'); const vid = document.getElementById('lightbox-video'); try { if (vid) { vid.pause(); vid.removeAttribute('src'); if (typeof vid.load === 'function') vid.load(); vid.onended = null; } } catch (e) {} if (lb) lb.style.display = 'none'; }
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
        img.addEventListener('load', function () { try { setTileAspectRatio(img); reflowGalleryMasonry(); } catch (e) {} }, { once: true });
        tile.appendChild(img); lazyObserver.observe(img);
      } else if (file.type === 'video') {
        const v = document.createElement('video'); v.src = file.url || ''; v.className = 'gallery-video'; v.controls = true; v.preload = 'metadata'; v.addEventListener('loadedmetadata', function () { try { setTileHeightFromVideo(v); reflowGalleryMasonry(); } catch (e) {} }, { once: true }); tile.appendChild(v);
      }

      if (file.type === 'video') { const badge = document.createElement('div'); badge.className = 'tile-badge video'; badge.title = 'Video'; badge.textContent = '▶'; tile.appendChild(badge); }
      if (file.deleted && !window.__showDeletedMode) { const badge = document.createElement('div'); badge.className = 'tile-badge deleted'; badge.title = 'Deleted'; badge.textContent = 'Deleted'; tile.appendChild(badge); }
      const fav = document.createElement('button'); fav.className = 'fav-btn' + (file.favorite ? ' is-fav' : ''); fav.title = file.favorite ? 'Unfavorite' : 'Favorite'; fav.setAttribute('data-id', String(file.id)); fav.textContent = file.favorite ? '★' : '☆'; tile.appendChild(fav);
      if (typeof file.ordinal === 'number') { const ord = document.createElement('div'); ord.className = 'tile-ordinal'; ord.setAttribute('aria-hidden', 'true'); ord.textContent = String(file.ordinal); tile.appendChild(ord); }

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
    try { if (typeof initBulkBar !== 'function') initBulkBar = function() {
      const bulkBar = document.getElementById('bulk-bar');
      const bulkCount = document.getElementById('bulk-count');
      const btnClear = document.getElementById('bb-clear');
      const btnDelete = document.getElementById('bb-delete');
      const btnRestore = document.getElementById('bb-restore');
      const btnZip = document.getElementById('bb-zip');
      const btnAdd = document.getElementById('bb-add-to-album');
      const selectAllBtn = document.getElementById('select-all');
      function getSelectedIds(){ return Array.from(document.querySelectorAll('.select-chk:checked')).map(i=>parseInt(i.getAttribute('data-id'))).filter(i=>!isNaN(i)); }
      // select-all toggles selection of visible tiles
      if (selectAllBtn){ selectAllBtn.addEventListener('click', function(){ const visible = Array.from(document.querySelectorAll('#gallery .gallery-item .select-chk')); const allChecked = visible.every(chk=>chk.checked); visible.forEach(chk=>chk.checked = !allChecked); updateSelectionUI(); }); }
      if (btnClear) btnClear.addEventListener('click', function(){ Array.from(document.querySelectorAll('.select-chk:checked')).forEach(c=>c.checked=false); updateSelectionUI(); });
      if (btnDelete) btnDelete.addEventListener('click', function(){ const ids = getSelectedIds(); if (!ids.length) return; const dlg = document.getElementById('delete-confirm'); if (dlg) dlg.style.display='flex'; });
      if (btnRestore) btnRestore.addEventListener('click', function(){ const ids = getSelectedIds(); if (!ids.length) return; const form = document.getElementById('restore-form'); if (form){ Array.from(form.querySelectorAll('input[name="file_ids"]')).forEach(i=>i.remove()); ids.forEach(id=>{ const h = document.createElement('input'); h.type='hidden'; h.name='file_ids'; h.value=String(id); form.appendChild(h); } ); form.submit(); } });
      if (btnZip) btnZip.addEventListener('click', function(){ const ids = getSelectedIds(); if (!ids.length) return; const form = document.getElementById('zip-form'); if (form){ Array.from(form.querySelectorAll('input[name="file_ids"]')).forEach(i=>i.remove()); ids.forEach(id=>{ const h = document.createElement('input'); h.type='hidden'; h.name='file_ids'; h.value=String(id); form.appendChild(h); } ); form.submit(); } });
      if (btnAdd) btnAdd.addEventListener('click', function(){ const ids = getSelectedIds(); if (!ids.length) return; if (typeof openAddToAlbumModal === 'function') openAddToAlbumModal(ids); });
      // Wire confirm delete inside modal to submit delete-form
      const delConfirmBtn = document.getElementById('del-confirm');
      if (delConfirmBtn) {
        delConfirmBtn.addEventListener('click', function(){ const ids = getSelectedIds(); if (!ids.length) return; const form = document.getElementById('delete-form'); if (form){ Array.from(form.querySelectorAll('input[name="file_ids"]')).forEach(i=>i.remove()); ids.forEach(id=>{ const h = document.createElement('input'); h.type='hidden'; h.name='file_ids'; h.value=String(id); form.appendChild(h); } ); form.submit(); } });
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
    initFilters(); try { if (typeof initBulkBar === 'function') initBulkBar(); } catch (e) {}
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
  try { const lbNextEl = document.getElementById('lightbox-next'); if (lbNextEl) lbNextEl.addEventListener('click', nextSlide); } catch (e) {}
  try { const lbPrevEl = document.getElementById('lightbox-prev'); if (lbPrevEl) lbPrevEl.addEventListener('click', prevSlide); } catch (e) {}
  try { const newAlbumEl = document.getElementById('new-album'); if (newAlbumEl) newAlbumEl.addEventListener('click', function () { if (typeof openCreateAlbumModal === 'function') openCreateAlbumModal(); }); } catch (e) {}
    document.addEventListener('keydown', (e) => { const lb = document.getElementById('lightbox'); if (!lb || lb.style.display === 'none') return; if (e.key === 'Escape') closeLightbox(); else if (e.key === 'ArrowRight') nextSlide(); else if (e.key === 'ArrowLeft') prevSlide(); });

    // Initial reflow after images loaded
    setTimeout(() => { try { reflowGalleryMasonry(); renderColumnMasonry(); } catch (e) {} }, 120);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();

  // Public small helpers (if other modules call them)
  return {
    appendFiles, reflowGalleryMasonry, openLightbox
  };
})();

// expose for debugging
window.GalleryModule = G;
