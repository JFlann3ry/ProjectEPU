// Gallery: video tiles open lightbox, arrow keys navigate, and order matches visual rows.
(function(){
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

  function rebuildGalleryOrder(){
    try {
      const gal = document.querySelector('.dynamic-gallery'); if (!gal) return;
      const byId = new Map(files.map(f=>[f.id,f]));
      const tiles = Array.from(gal.querySelectorAll('.gallery-item'));
      const withRects = tiles.map(tile => {
        const chk = tile.querySelector('.select-chk');
        const id = chk ? parseInt(chk.getAttribute('data-id')) : NaN;
        const r = tile.getBoundingClientRect();
        return {tile, id, top: Math.round(r.top), left: Math.round(r.left)};
      }).filter(x => x.id && !isNaN(x.id));
      const rowGap = 6;
      withRects.sort((a,b)=>{ const dt=a.top-b.top; if (Math.abs(dt)>rowGap) return dt; return a.left-b.left; });
      const newFiles = [];
      withRects.forEach((entry, idx) => {
        entry.tile.setAttribute('data-index', String(idx));
        const meta = byId.get(entry.id); if (meta) newFiles.push({...meta});
      });
      if (newFiles.length){ files = newFiles; window.__gallerySeenIds = new Set(files.map(f=>f.id)); }
    } catch(_){}
  }

  function initFromDOM(){
    try {
      const gal = document.querySelector('.dynamic-gallery'); if (!gal) return;
      const byId = new Map((Array.isArray(window.galleryFiles)?window.galleryFiles:[]).map(f=>[f.id,f]));
      const seenIds = new Set();
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
          const url = isVid ? (tile.querySelector('video')?.getAttribute('src') || '') : (img?.getAttribute('data-full') || img?.getAttribute('src') || '');
          newFiles.push({ id, type: isVid ? 'video' : 'image', url, favorite:false });
        }
      });
      if (newFiles.length){ files = newFiles; window.__gallerySeenIds = new Set(files.map(f=>f.id)); }
    } catch(_){}
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
        // Update DOM tiles order and data-index to match new order
        try{
          var gal = document.querySelector('.dynamic-gallery'); if (!gal) return;
          var idToTile = new Map();
          Array.from(gal.querySelectorAll('.gallery-item')).forEach(function(tile){
            var chk = tile.querySelector('.select-chk');
            var id = chk ? parseInt(chk.getAttribute('data-id')) : NaN;
            if (!isNaN(id)) idToTile.set(id, tile);
          });
          // Build document fragment in server order
          var frag = document.createDocumentFragment();
          files.forEach(function(f, idx){
            var tile = idToTile.get(f.id);
            if (tile){
              tile.setAttribute('data-index', String(idx));
              frag.appendChild(tile);
            }
          });
          // Append any leftover tiles not present in order at the end
          idToTile.forEach(function(tile, id){ if (!files.find(function(x){ return x.id === id; })) frag.appendChild(tile); });
          // Replace gallery children
          while (gal.firstChild) gal.removeChild(gal.firstChild);
          gal.appendChild(frag);
        }catch(_){ }
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
    document.getElementById('play-slideshow')?.addEventListener('click', function(){
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
