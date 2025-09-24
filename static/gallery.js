// Gallery: video tiles open lightbox, arrow keys navigate, and order matches visual rows.
// Prevent legacy script from running when the modern module-based gallery is loaded.
// The new module lives at `window.GalleryModule`. If present, skip the legacy bootstrap
// to avoid competing DOM reorders and selection UI wiring which caused the gallery to
// appear out-of-order after infinite-scroll appends.
(function(){
  try{ if (typeof window !== 'undefined' && window.GalleryModule) { if (window.__GALLERY_DEBUG) console.debug('legacy static/gallery.js skipped in favor of GalleryModule'); return; } } catch(_){}
  // State
  const initial = Array.isArray(window.galleryFiles) ? window.galleryFiles : [];
  const seen = new Set();
  let files = initial.filter(f => f && typeof f.id === 'number' && !seen.has(f.id) && (seen.add(f.id), true))
                     .map(f => ({...f, favorite: !!f.favorite}));
  window.__gallerySeenIds = new Set(files.map(f=>f.id));
  let currentIndex = 0;

  // Helpers
  function pauseAllGridVideos(){
    try { document.querySelectorAll('.dynamic-gallery video').forEach(v=>{ try{ v.pause(); v.currentTime=0; }catch(_){} }); } catch(_){}
  }

  function openLightbox(index){
    currentIndex = index;
    const file = files[index]; if (!file) return;
    const lb = document.getElementById('lightbox');
    const img = document.getElementById('lightbox-img');
    const vid = document.getElementById('lightbox-video');
    pauseAllGridVideos();
    if (file.type === 'image'){
      try { vid.pause(); } catch(_){}
      vid.removeAttribute('src'); if (typeof vid.load === 'function') vid.load();
      img.src = file.url;
      img.style.display='block'; vid.style.display='none';
      img.style.visibility='visible'; vid.style.visibility='hidden';
    } else {
      img.removeAttribute('src'); img.style.display='none';
      vid.src = file.url; vid.style.display='block';
      img.style.visibility='hidden'; vid.style.visibility='visible';
      try { vid.currentTime=0; const p = vid.play(); if (p && p.catch) p.catch(()=>{}); } catch(_){}
    }
    lb.style.display='flex'; lb.style.visibility='visible'; lb.style.opacity=1;
  }
  function closeLightbox(){
    const lb = document.getElementById('lightbox');
    const img = document.getElementById('lightbox-img');
    const vid = document.getElementById('lightbox-video');
    try { vid.pause(); } catch(_){}
    lb.style.display='none'; img.src=''; vid.removeAttribute('src'); if (typeof vid.load === 'function') vid.load();
  }
  function prevSlide(){ currentIndex = (currentIndex - 1 + files.length) % files.length; openLightbox(currentIndex); }
  function nextSlide(){ currentIndex = (currentIndex + 1) % files.length; openLightbox(currentIndex); }

  // Reorder gallery DOM to match the canonical order in `files` without
  // measuring element positions (which shifts while images load).
  function stableReorderDOM(){
    try{
      const gal = document.querySelector('.dynamic-gallery'); if (!gal) return;
      const idToTile = new Map();
      Array.from(gal.querySelectorAll('.gallery-item')).forEach(tile => {
        const chk = tile.querySelector('.select-chk');
        const id = chk ? parseInt(chk.getAttribute('data-id')) : NaN;
        if (!isNaN(id)) idToTile.set(id, tile);
      });
      // Build fragment in files order
      const frag = document.createDocumentFragment();
      files.forEach((f, idx) => {
        const tile = idToTile.get(f.id);
        if (tile) {
          tile.setAttribute('data-index', String(idx));
          frag.appendChild(tile);
          idToTile.delete(f.id);
        }
      });
      // Append any leftover tiles (not present in `files`) at the end
      idToTile.forEach((tile, id) => {
        frag.appendChild(tile);
      });
      // Replace gallery children preserving nodes
      while (gal.firstChild) gal.removeChild(gal.firstChild);
      gal.appendChild(frag);
    }catch(_){ }
  }

  // Bulk action UI: show/hide bulk bar, enable buttons and wire select-all/clear
  function initBulkBarLegacy(){
    try{
      const bulkBar = document.getElementById('bulk-bar');
      const bulkCount = document.getElementById('bulk-count');
      const btnClear = document.getElementById('bb-clear');
      const btnDelete = document.getElementById('bb-delete');
      const btnRestore = document.getElementById('bb-restore');
      const btnZip = document.getElementById('bb-zip');
      const btnAdd = document.getElementById('bb-add-to-album');
      const selectAllBtn = document.getElementById('select-all');
      function getSelectedIds(){ return Array.from(document.querySelectorAll('.select-chk:checked')).map(i=>parseInt(i.getAttribute('data-id'))).filter(i=>!isNaN(i)); }
      if (selectAllBtn){ selectAllBtn.addEventListener('click', function(){ const visible = Array.from(document.querySelectorAll('#gallery .gallery-item .select-chk')); if (!visible.length) return; const allChecked = visible.every(chk=>chk.checked); visible.forEach(chk=>chk.checked = !allChecked); updateSelectionUI(); }); }
      if (btnClear) btnClear.addEventListener('click', function(){ Array.from(document.querySelectorAll('.select-chk:checked')).forEach(c=>c.checked=false); updateSelectionUI(); });
      if (btnDelete) btnDelete.addEventListener('click', function(){ const ids = getSelectedIds(); if (!ids.length) return; const dlg = document.getElementById('delete-confirm'); if (dlg) dlg.style.display='flex'; });
      if (btnRestore) btnRestore.addEventListener('click', function(){ const ids = getSelectedIds(); if (!ids.length) return; const form = document.getElementById('restore-form'); if (form){ Array.from(form.querySelectorAll('input[name="file_ids"]')).forEach(i=>i.remove()); ids.forEach(id=>{ const h = document.createElement('input'); h.type='hidden'; h.name='file_ids'; h.value=String(id); form.appendChild(h); } ); form.submit(); } });
      if (btnZip) btnZip.addEventListener('click', function(){ const ids = getSelectedIds(); if (!ids.length) return; const form = document.getElementById('zip-form'); if (form){ Array.from(form.querySelectorAll('input[name="file_ids"]')).forEach(i=>i.remove()); ids.forEach(id=>{ const h = document.createElement('input'); h.type='hidden'; h.name='file_ids'; h.value=String(id); form.appendChild(h); } ); form.submit(); } });
      if (btnAdd) btnAdd.addEventListener('click', function(){ const ids = getSelectedIds(); if (!ids.length) return; if (typeof openAddToAlbumModal === 'function') openAddToAlbumModal(ids); });

      // confirm delete button inside modal (id: del-confirm) should submit delete-form
      const delConfirmBtn = document.getElementById('del-confirm');
      if (delConfirmBtn){ delConfirmBtn.addEventListener('click', function(){ const ids = getSelectedIds(); if (!ids.length) return; const form = document.getElementById('delete-form'); if (form){ Array.from(form.querySelectorAll('input[name="file_ids"]')).forEach(i=>i.remove()); ids.forEach(id=>{ const h = document.createElement('input'); h.type='hidden'; h.name='file_ids'; h.value=String(id); form.appendChild(h); } ); form.submit(); } }); }

      // expose updateSelectionUI globally for other scripts
      if (typeof window.updateSelectionUI !== 'function') window.updateSelectionUI = function(){ try{ const ids = getSelectedIds(); const n = ids.length; if (bulkBar && bulkCount) { bulkCount.textContent = n + (n===1? ' selected' : ' selected'); bulkBar.style.display = n>0? 'block' : 'none'; } if (btnDelete) btnDelete.disabled = n===0; if (btnRestore) btnRestore.disabled = n===0; if (btnZip) btnZip.disabled = n===0; if (btnAdd) btnAdd.disabled = n===0; }catch(e){} };
      // initialize
      try{ window.updateSelectionUI(); }catch(e){}
    }catch(e){}
  }

  function initFromDOM(){
    try{
      const gal = document.querySelector('.dynamic-gallery'); if (!gal) return;
      const byId = new Map((Array.isArray(window.galleryFiles)?window.galleryFiles:[]).map(f=>[f.id,f]));
      const seenIds = new Set();
      // Remove duplicate tiles while preserving first occurrence
      Array.from(gal.querySelectorAll('.gallery-item')).forEach(tile => {
        const chk = tile.querySelector('.select-chk');
        const id = chk ? parseInt(chk.getAttribute('data-id')) : NaN;
        if (!id || isNaN(id)) return;
        if (seenIds.has(id)) tile.remove(); else seenIds.add(id);
      });
      const newFiles = [];
      Array.from(gal.querySelectorAll('.gallery-item')).forEach((tile, idx) => {
        tile.setAttribute('data-index', String(idx));
        const chk = tile.querySelector('.select-chk');
        const id = chk ? parseInt(chk.getAttribute('data-id')) : NaN;
        if (!id || isNaN(id)) return;
        const m = byId.get(id);
        if (m) newFiles.push({...m, favorite: !!m.favorite});
        else {
          const isVid = !!tile.querySelector('video');
          const img = tile.querySelector('img');
          const videoEl = tile.querySelector('video');
          const url = isVid ? ((videoEl && videoEl.getAttribute('src')) || '') : ((img && (img.getAttribute('data-full') || img.getAttribute('src'))) || '');
          newFiles.push({ id, type: isVid ? 'video' : 'image', url, favorite:false });
        }
      });
      if (newFiles.length){ files = newFiles; window.__gallerySeenIds = new Set(files.map(f=>f.id)); }
    }catch(_){ }
  }

  // Attempt to fetch server-side canonical order for the current event if available
  function applyServerOrder(eventId){
    if (!eventId) return Promise.resolve();
    return fetch('/events/' + encodeURIComponent(eventId) + '/gallery/order')
      .then(function(r){ if (!r.ok) throw new Error('no-order'); return r.json(); })
      .then(function(j){ if (!j || !j.ok || !Array.isArray(j.files)) throw new Error('bad');
        // Replace files array and update DOM data-index to match
        var newFiles = j.files.map(function(f){ return Object.assign({}, f, { favorite: !!f.favorite }); });
        files = newFiles;
        window.__gallerySeenIds = new Set(files.map(f=>f.id));
    // Update DOM tiles order and data-index to match new order using stableReorderDOM
    try{ stableReorderDOM(); }catch(_){ }
      }).catch(function(){ /* ignore and keep DOM order */ });
  }

  function init(){
    initFromDOM();
    const gallery = document.querySelector('.dynamic-gallery');
    if (gallery){
      gallery.addEventListener('click', function(e){
        // fav toggle
        if (e.target && e.target.classList && e.target.classList.contains('fav-btn')){
          e.preventDefault(); e.stopPropagation();
          const btn = e.target; const id = parseInt(btn.getAttribute('data-id')); if (!id) return;
          const isFav = btn.classList.contains('is-fav');
          const url = isFav ? '/gallery/unfavorite' : '/gallery/favorite';
          const fd = new FormData(); fd.append('file_id', String(id));
          fetch(url, { method:'POST', body: fd }).then(r=>r.json()).then(resp=>{
            if (!resp || resp.ok !== true) return;
            btn.classList.toggle('is-fav'); btn.textContent = btn.classList.contains('is-fav') ? '★' : '☆';
            const idx = files.findIndex(f=>f.id===id); if (idx>=0) files[idx].favorite = btn.classList.contains('is-fav');
            if (typeof renderFavoritesCount === 'function') renderFavoritesCount();
          }).catch(()=>{});
          return;
        }
        // ignore checkbox direct clicks
        if (e.target && e.target.classList && e.target.classList.contains('select-chk')){ e.stopPropagation(); return; }
        // open lightbox on tile click
        let el = e.target;
        while (el && !el.classList.contains('gallery-clickable')) el = el.parentElement;
        if (el && el.classList.contains('gallery-clickable')){
          const tileVideo = el.querySelector('video'); if (tileVideo){ try { tileVideo.pause(); } catch(_){} }
          const idx = parseInt(el.getAttribute('data-index')); if (!isNaN(idx)) openLightbox(idx);
        }
      });
      gallery.addEventListener('mousedown', function(e){
        const tile = e.target.closest('.gallery-item'); if (!tile) return;
        const checkbox = tile.querySelector('.select-chk'); if (!checkbox) return;
        const isClickOnMedia = e.target.tagName==='IMG' || e.target.tagName==='VIDEO' || e.target.classList.contains('tile-overlay');
        if (!isClickOnMedia && !e.target.classList.contains('select-chk')){
          checkbox.checked = !checkbox.checked; if (typeof updateSelectionUI === 'function') updateSelectionUI(); e.preventDefault();
        }
      });
    }

    // observe appends to rebuild order
    try {
      const gal = document.querySelector('.dynamic-gallery');
      if (gal){
        let timer; const obs = new MutationObserver(muts=>{
          let added=false; for (const m of muts){ if (m.type==='childList' && m.addedNodes && m.addedNodes.length) added=true; }
          if (added){ clearTimeout(timer); timer = setTimeout(()=>{ try { rebuildGalleryOrder(); } catch(_){} }, 80); }
        });
        obs.observe(gal, { childList: true });
      }
    } catch(_){}

    // fade in
    try { document.querySelectorAll('.gallery-item').forEach((item,i)=>{ item.style.opacity=0; setTimeout(()=>{ item.style.transition='opacity 0.5s'; item.style.opacity=1; }, 100 + i*80); }); } catch(_){}

  // slideshow
  const playBtn = document.getElementById('play-slideshow');
  if (playBtn) playBtn.addEventListener('click', function(){
      if (files.length===0) return; let idx=0; let playing=true; window.__slideshowPlaying = true;
      function showSlide(i){
        openLightbox(i); const f = files[i];
        if (f.type==='video'){
          const v = document.getElementById('lightbox-video'); v.currentTime=0; v.play(); v.onended = function(){ if (!playing || window.__slideshowPlaying===false) return; if (i+1<files.length) showSlide(i+1); else { playing=false; window.__slideshowPlaying=false; closeLightbox(); } };
        } else {
          setTimeout(function(){ if (!playing || window.__slideshowPlaying===false) return; if (i+1<files.length) showSlide(i+1); else { playing=false; window.__slideshowPlaying=false; closeLightbox(); } }, 2500);
        }
      }
      showSlide(idx);
      const closeBtn = document.querySelector('.lightbox-close');
      if (closeBtn) closeBtn.onclick = function(){ playing=false; window.__slideshowPlaying=false; try { document.getElementById('lightbox-video').pause(); } catch(_){} closeLightbox(); };
    });

  if (typeof updateSelectionUI === 'function') updateSelectionUI();
  if (typeof renderFavoritesCount === 'function') renderFavoritesCount();
  try{ if (typeof initBulkBarLegacy === 'function') initBulkBarLegacy(); } catch(e) {}
    setTimeout(()=>{ try { rebuildGalleryOrder(); } catch(_){} }, 120);
    let reb; window.addEventListener('resize', ()=>{ clearTimeout(reb); reb = setTimeout(()=>{ try { rebuildGalleryOrder(); } catch(_){} }, 150); });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else { try { init(); } catch(_){} }

  // Keyboard controls
  document.addEventListener('keydown', function(e){
    if (e.key==='Escape'){ if (window.__slideshowPlaying){ window.__slideshowPlaying=false; try { document.getElementById('lightbox-video').pause(); } catch(_){} } closeLightbox(); return; }
    try { const lb = document.getElementById('lightbox'); const isOpen = lb && lb.style && lb.style.display && lb.style.display !== 'none'; if (!isOpen) return; if (e.key==='ArrowRight'){ e.preventDefault(); nextSlide(); } else if (e.key==='ArrowLeft'){ e.preventDefault(); prevSlide(); } } catch(_){ }
  });

  // Expose minimal API
  window.openLightbox = openLightbox;
  window.closeLightbox = closeLightbox;
  window.prevSlide = prevSlide;
  window.nextSlide = nextSlide;
  window.rebuildGalleryOrder = rebuildGalleryOrder;
})();
