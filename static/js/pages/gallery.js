// Gallery page module: depends on data from #gallery-data JSON script.
// Moves inline logic out of template for CSP and maintainability.

// Backing array of files currently rendered/known
let files = [];
let currentIndex = -1;

// Helpers reused from inline code
function getFileById(id){
  try {
    if (typeof files !== 'undefined' && Array.isArray(files)) {
      const f = files.find(x => x && x.id === id);
      if (f) return f;
    }
  } catch(_){}
  try {
    if (Array.isArray(window.galleryFiles)) {
      return window.galleryFiles.find(x => x && x.id === id) || null;
    }
  } catch(_){}
  return null;
}

function wireSelection(formId) {
  const form = document.getElementById(formId);
  if (!form) return;
  form.addEventListener('submit', function(e){
    let ids = Array.from(document.querySelectorAll('.select-chk:checked')).map(chk => chk.getAttribute('data-id'));
    if (formId === 'restore-form') {
      ids = ids.filter(id => { const f = getFileById(parseInt(id)); return f && f.deleted; });
    }
    if (formId === 'delete-form') {
      ids = ids.filter(id => { const f = getFileById(parseInt(id)); return f && !f.deleted; });
    }
    if (ids.length === 0) { e.preventDefault(); return; }
    const input = form.querySelector('input[name="file_ids"]');
    if (input) input.remove();
    ids.forEach(id => {
      const hidden = document.createElement('input');
      hidden.type = 'hidden';
      hidden.name = 'file_ids';
      hidden.value = id;
      form.appendChild(hidden);
    });
  });
}

function updateSelectionUI() {
  const chks = Array.from(document.querySelectorAll('.select-chk'));
  const selected = chks.filter(c => c.checked);
  chks.forEach(c => {
    const tile = c.closest('.gallery-item');
    if (!tile) return;
    tile.classList.toggle('selected', c.checked);
  });
  const count = selected.length;
  const selectedIds = selected.map(c => parseInt(c.getAttribute('data-id')));
  const hasDeletedSelected = selectedIds.some(id => { const f = getFileById(id); return f && f.deleted; });
  const hasNonDeletedSelected = selectedIds.some(id => { const f = getFileById(id); return f && !f.deleted; });
  (function(){
    const form = document.getElementById('restore-form');
    if (!form) return;
    const btn = form.querySelector('button[type="submit"]');
    if (hasDeletedSelected) {
      form.style.display = 'inline-block';
      if (btn) btn.disabled = false;
    } else {
      form.style.display = 'none';
      if (btn) btn.disabled = true;
    }
  })();
  const bb = document.getElementById('bulk-bar');
  const bc = document.getElementById('bulk-count');
  if (bb && bc) {
    if (count > 0) {
      bb.style.display = 'block';
      bc.textContent = count + ' selected';
    } else {
      bb.style.display = 'none';
    }
  }
  const bbr = document.getElementById('bb-restore');
  if (bbr) {
    if (hasDeletedSelected) {
      bbr.style.display = '';
      bbr.disabled = false;
    } else {
      bbr.style.display = 'none';
      bbr.disabled = true;
    }
  }
  const bbd = document.getElementById('bb-delete');
  if (bbd) {
    bbd.disabled = !hasNonDeletedSelected;
  }
  const sa = document.getElementById('select-all');
  if (sa) {
    const allSelected = chks.length > 0 && chks.every(c => c.checked);
    sa.textContent = allSelected ? 'Deselect All' : 'Select All';
  }
}

function initFilters(){
  function setParam(key, val, toggle){
    var url = new URL(window.location.href);
    if (toggle){
      var cur = url.searchParams.get(key);
      var next = (cur === '1' || cur === 'true') ? '' : '1';
      if (next) url.searchParams.set(key, next); else url.searchParams.delete(key);
    } else {
      if (val) url.searchParams.set(key, val); else url.searchParams.delete(key);
    }
    url.searchParams.delete('offset');
    window.location.href = url.toString();
  }
  document.querySelectorAll('.pill-filter').forEach(function(btn){
    btn.addEventListener('click', function(){
      var key = btn.getAttribute('data-filter');
      var toggle = btn.hasAttribute('data-toggle');
      var val = btn.getAttribute('data-value') || '';
      setParam(key, val, toggle);
    });
  });
}

function initBulkBar(){
  document.addEventListener('change', function(e){
    if (e.target && e.target.classList && e.target.classList.contains('select-chk')) {
      updateSelectionUI();
      e.stopPropagation();
    }
  });
  document.getElementById('select-all')?.addEventListener('click', function(){
    const chks = Array.from(document.querySelectorAll('.select-chk'));
    const allSelected = chks.length > 0 && chks.every(c => c.checked);
    chks.forEach(c => c.checked = !allSelected);
    const btn = document.getElementById('select-all');
    if (btn) btn.textContent = allSelected ? 'Select All' : 'Deselect All';
    updateSelectionUI();
  });
  document.getElementById('bb-clear')?.addEventListener('click', function(){
    document.querySelectorAll('.select-chk').forEach(c => c.checked = false);
    updateSelectionUI();
  });
  document.getElementById('bb-restore')?.addEventListener('click', function(){
    document.getElementById('restore-form')?.requestSubmit();
  });
  const delBtn = document.getElementById('bb-delete');
  if (delBtn) {
    delBtn.addEventListener('click', function(){
      const modal = document.getElementById('delete-confirm');
      if (modal) modal.style.display = 'flex';
    });
  }
  document.getElementById('del-cancel')?.addEventListener('click', function(){
    const modal = document.getElementById('delete-confirm');
    if (modal) modal.style.display = 'none';
  });
  document.getElementById('del-confirm')?.addEventListener('click', function(){
    const modal = document.getElementById('delete-confirm');
    if (modal) modal.style.display = 'none';
    document.getElementById('delete-form')?.requestSubmit();
  });
}

function initInfiniteScroll(){
  const gal = document.getElementById('gallery');
  if (!gal) return;
  let nextOffset = gal.getAttribute('data-next-offset');
  const pageSize = parseInt(gal.getAttribute('data-page-size') || '60');
  let loading = false;
  let done = !nextOffset;
  const loader = document.getElementById('gallery-loader');

  function appendFiles(items){
    const seen = (window.__gallerySeenIds instanceof Set) ? window.__gallerySeenIds : (window.__gallerySeenIds = new Set(files.map(f=>f.id)));
    const unique = [];
    for (const it of items || []) {
      if (!it || typeof it.id !== 'number') continue;
      if (seen.has(it.id)) continue;
      seen.add(it.id);
      unique.push(it);
    }
    if (unique.length === 0) { return; }
    const startIndex = files.length;
    const showDeleted = !!window.__showDeletedMode;
    const batch = showDeleted ? [...unique].sort((a,b)=>{
      const da = (a && typeof a.days_left === 'number') ? a.days_left : 9999;
      const db = (b && typeof b.days_left === 'number') ? b.days_left : 9999;
      return da - db;
    }) : unique;
    let lastDays = undefined;
    if (showDeleted) {
      const hs = document.querySelectorAll('.group-heading[data-days]');
      if (hs && hs.length) {
        const v = parseInt(hs[hs.length-1].getAttribute('data-days'));
        if (!isNaN(v)) lastDays = v;
      }
    }
  batch.forEach((file, i) => {
      files.push(file);
      const idx = startIndex + i;
      const days = (typeof file.days_left === 'number') ? file.days_left : 9999;
      if (showDeleted && (lastDays === undefined || days !== lastDays)){
        const heading = document.createElement('div');
        heading.className = 'group-heading';
        heading.setAttribute('data-days', String(days));
        heading.textContent = days >= 9999 ? 'Deletion date unknown' : (days === 0 ? 'Deleting soon' : (days === 1 ? '1 day left' : `${days} days left`));
        gal.appendChild(heading);
        lastDays = days;
      }
      const tile = document.createElement('div');
      const isVideo = file.type === 'video';
      const cls = isVideo ? 'gallery-item gallery-large gallery-video-tile gallery-clickable' : 'gallery-item gallery-clickable';
      tile.className = cls;
      tile.setAttribute('data-index', String(idx));
      tile.setAttribute('data-name', file.name || '');
      tile.setAttribute('data-datetime', file.datetime || '');
      const chk = document.createElement('input');
      chk.type = 'checkbox';
      chk.className = 'select-chk';
      chk.setAttribute('data-id', String(file.id));
      tile.appendChild(chk);
      if (file.type === 'image') {
        const img = document.createElement('img');
        img.src = file.thumb_url || file.url;
        img.className = 'gallery-img';
        img.alt = file.name || '';
        img.loading = 'lazy';
        if (file.url) img.setAttribute('data-full', file.url);
        if (file.srcset) {
          img.setAttribute('srcset', file.srcset);
          img.setAttribute('sizes', '(max-width: 640px) 45vw, (max-width: 1024px) 30vw, 20vw');
        }
        // Warm-up: start loading full image in background for better lightbox UX
        if (file.url) {
          const pre = new Image();
          pre.src = file.url;
          img.classList.add('is-warming');
          pre.onload = () => img.classList.remove('is-warming');
          pre.onerror = () => img.classList.remove('is-warming');
        }
        tile.appendChild(img);
      } else if (file.type === 'video') {
        const v = document.createElement('video');
        v.src = file.url; v.className = 'gallery-video'; v.controls = true;
        tile.appendChild(v);
      }
      const overlay = document.createElement('div'); overlay.className = 'tile-overlay'; tile.appendChild(overlay);
      if (file.type === 'video'){
        const badge = document.createElement('div'); badge.className = 'tile-badge video'; badge.title = 'Video'; badge.textContent = '▶'; tile.appendChild(badge);
      }
      if (file.deleted && !showDeleted){ const badge = document.createElement('div'); badge.className = 'tile-badge deleted'; badge.title = 'Deleted'; badge.textContent = 'Deleted'; tile.appendChild(badge); }
      const fav = document.createElement('button'); fav.className = 'fav-btn' + (file.favorite ? ' is-fav' : ''); fav.title = file.favorite ? 'Unfavorite' : 'Favorite'; fav.setAttribute('data-id', String(file.id)); fav.textContent = file.favorite ? '★' : '☆'; tile.appendChild(fav);
      // Click to open lightbox
      tile.addEventListener('click', (ev) => {
        // Ignore clicks on controls (checkboxes, buttons)
        const t = ev.target;
        if (t && (t.tagName === 'INPUT' || t.tagName === 'BUTTON')) return;
        openLightbox(idx);
      });
      gal.appendChild(tile);
    });
    if (typeof renderFavoritesCount === 'function') renderFavoritesCount();
  }

  function fetchMore(){
    if (loading || done) return;
    loading = true; if (loader) loader.style.display = 'block';
    // Add skeleton placeholders while loading next page
    const skeletons = [];
    for (let i=0;i<8;i++){
      const sk = document.createElement('div');
      sk.className = 'gallery-item skeleton';
      gal.appendChild(sk);
      skeletons.push(sk);
    }
    const params = new URLSearchParams(window.location.search);
    params.set('offset', String(nextOffset || 0)); params.set('limit', String(pageSize));
    fetch('/gallery/data?' + params.toString(), { headers: { 'accept': 'application/json' }})
      .then(r => r.json())
      .then(resp => {
        if (!resp || resp.ok !== true) return;
        appendFiles(resp.files || []);
        if (resp.next_offset != null) { nextOffset = resp.next_offset; }
        else { done = true; const end = document.getElementById('gallery-end'); if (end) end.style.display = 'block'; }
      })
      .catch(() => {})
      .finally(() => {
        // Remove skeletons
        skeletons.forEach(el => el.remove());
        loading = false; if (loader) loader.style.display = done ? 'none' : 'block';
      });
  }

  window.addEventListener('scroll', function(){
    if (done || loading) return;
    const scrollPos = window.scrollY + window.innerHeight;
    const nearBottom = document.body.offsetHeight - 800;
    if (scrollPos >= nearBottom) fetchMore();
  });
}

function openLightbox(index){
  const lb = document.getElementById('lightbox');
  if (!lb) return;
  currentIndex = index;
  renderLightbox();
  lb.style.display = 'flex';
}

function closeLightbox(){
  const lb = document.getElementById('lightbox');
  if (lb) lb.style.display = 'none';
}

function nextSlide(){ if (files.length === 0) return; currentIndex = (currentIndex + 1) % files.length; renderLightbox(); }
function prevSlide(){ if (files.length === 0) return; currentIndex = (currentIndex - 1 + files.length) % files.length; renderLightbox(); }

function renderLightbox(){
  const img = document.getElementById('lightbox-img');
  const vid = document.getElementById('lightbox-video');
  if (!img || !vid) return;
  const f = files[currentIndex];
  if (!f) return;
  if (f.type === 'image'){
    vid.style.display = 'none'; vid.pause();
    img.style.display = '';
    img.src = f.url || f.thumb_url || '';
  } else if (f.type === 'video'){
    img.style.display = 'none';
    vid.style.display = '';
    vid.src = f.url || '';
  }
}

function boot(){
  try {
    var dataEl = document.getElementById('gallery-data');
  window.galleryFiles = dataEl ? JSON.parse(dataEl.textContent) : [];
  // Initialize local array and expose for legacy helpers
  files = Array.isArray(window.galleryFiles) ? window.galleryFiles.slice() : [];
  window.files = files;
    window.__showDeletedMode = !!(dataEl && dataEl.dataset && dataEl.dataset.showDeleted === '1');
  } catch (_) { window.galleryFiles = []; }

  ['delete-form','restore-form','zip-form'].forEach(wireSelection);
  initFilters();
  initBulkBar();
  initInfiniteScroll();
  // Initial UI sync
  try { updateSelectionUI(); } catch(_){ }

  // Wire existing tiles for lightbox
  try {
    document.querySelectorAll('.gallery-item.gallery-clickable').forEach(tile => {
      tile.addEventListener('click', (ev) => {
        const t = ev.target;
        if (t && (t.tagName === 'INPUT' || t.tagName === 'BUTTON')) return;
        const idxAttr = tile.getAttribute('data-index');
        const idx = idxAttr ? parseInt(idxAttr) : -1;
        if (!isNaN(idx) && idx >= 0) openLightbox(idx);
      });
    });
  } catch(_){ }

  // Wire lightbox controls (no inline handlers)
  document.getElementById('lightbox-close')?.addEventListener('click', closeLightbox);
  document.getElementById('lightbox-next')?.addEventListener('click', nextSlide);
  document.getElementById('lightbox-prev')?.addEventListener('click', prevSlide);
  // New album button opens modal
  document.getElementById('new-album')?.addEventListener('click', function(){ openCreateAlbumModal(); });
  // Wire per-tile add-to-album buttons (for tiles already present)
  document.querySelectorAll('.add-to-album').forEach(btn => {
    btn.addEventListener('click', function(ev){
      ev.stopPropagation();
      const fid = parseInt(btn.getAttribute('data-id'));
      openAddToAlbumDialog(fid);
    });
  });
  // Keyboard navigation
  document.addEventListener('keydown', (e)=>{
    const lb = document.getElementById('lightbox');
    if (!lb || lb.style.display === 'none') return;
    if (e.key === 'Escape') closeLightbox();
    else if (e.key === 'ArrowRight') nextSlide();
    else if (e.key === 'ArrowLeft') prevSlide();
  });
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();

// Minimal modal helpers for album creation and adding
function openCreateAlbumDialog(){
  // open centered global modal via shared modal root
  openCreateAlbumModal();
}

function openCreateAlbumModal(){
  const meta = (document.getElementById('gallery-data') ? JSON.parse(document.getElementById('gallery-data').textContent || '{}') : {});
  const eventId = meta.event_id || '';
  const formId = 'create-album-form-modal';
  const nameId = 'create-album-name-modal';
  const descId = 'create-album-desc-modal';
  const html = `
    <form id="${formId}" class="form" style="max-width:100%;">
      <div style="margin-top:6px;">
        <label for="${nameId}">Album name</label>
        <input id="${nameId}" name="name" class="input-field" required maxlength="255" />
      </div>
      <div style="margin-top:8px;">
        <label for="${descId}">Description (optional)</label>
        <textarea id="${descId}" name="description" class="input-field" rows="3" maxlength="1024"></textarea>
      </div>
    </form>
  `;
  // Use global modal API; provide explicit actions so buttons appear in footer and modal is centered
  if (window.EPU && window.EPU.modal){
    window.EPU.modal.show({
      title: 'Create album',
      body: html,
      raw: true,
      noDefaultClose: true,
      actions: [
        { label: 'Cancel', role: 'cancel' },
        { label: 'Create', onClick: function(hide){
            const form = document.getElementById(formId);
            if (!form) return;
            // trigger submit handler which we've wired below
            form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
          }
        }
      ]
    });
    // Wire submit handler after modal is shown
    setTimeout(() => {
      const form = document.getElementById(formId);
      if (!form) return;
      const nameEl = document.getElementById(nameId);
      if (nameEl) { nameEl.focus(); nameEl.value = ''; }
      form.addEventListener('submit', function(e){
        e.preventDefault();
        const name = (document.getElementById(nameId) || {}).value || '';
        const desc = (document.getElementById(descId) || {}).value || '';
        if(!name){ if(window.EPU && window.EPU.snackbar) window.EPU.snackbar.show('Album name is required'); return; }
        fetch('/events/' + encodeURIComponent(eventId) + '/albums/create', { method: 'POST', headers: { 'content-type':'application/x-www-form-urlencoded' }, body: new URLSearchParams({ name: name, description: desc }) })
          .then(r => r.json()).then(j => {
            if(j && j.ok){
              const sel = document.getElementById('album-filter');
              if(sel){ const opt = document.createElement('option'); opt.value = j.album_id; opt.textContent = name + ' (0)'; sel.appendChild(opt); }
              if(window.EPU && window.EPU.modal) window.EPU.modal.hide();
              if(window.EPU && window.EPU.snackbar) window.EPU.snackbar.show('Album created');
            } else {
              if(window.EPU && window.EPU.snackbar) window.EPU.snackbar.show('Could not create album');
            }
          }).catch(()=>{ if(window.EPU && window.EPU.snackbar) window.EPU.snackbar.show('Could not create album'); });
      }, { once: true });
    }, 20);
  } else {
    // fallback to legacy inline modal if global modal unavailable
    const modal = document.getElementById('create-album-modal');
    if(modal){ modal.style.display = 'block'; modal.setAttribute('aria-hidden', 'false'); const name = document.getElementById('create-album-name'); if(name){ name.focus(); name.value = ''; } }
  }
}

function openAddToAlbumDialog(fileId){
  const meta = (document.getElementById('gallery-data') ? JSON.parse(document.getElementById('gallery-data').textContent || '{}') : {});
  const eventId = meta.event_id || '';
  // fetch albums and prompt
  fetch('/events/' + encodeURIComponent(eventId) + '/albums').then(r => r.json()).then(j => {
    if(!j || !Array.isArray(j.items) || j.items.length === 0){
      if(window.confirm('No albums found. Create one now?')) openCreateAlbumDialog();
      return;
    }
    const names = j.items.map(a => a.id + ': ' + a.name + (a.count ? (' ('+a.count+')') : '') ).join('\n');
    const pick = window.prompt('Choose album id to add to:\n' + names);
    if(!pick) return;
    const albumId = parseInt(pick.replace(/[^0-9]/g,''));
    if(isNaN(albumId)) return alert('Invalid album id');
    const body = new URLSearchParams({ file_id: String(fileId) });
    fetch('/events/' + encodeURIComponent(eventId) + '/albums/' + encodeURIComponent(albumId) + '/add', { method: 'POST', headers:{ 'content-type':'application/x-www-form-urlencoded' }, body: body })
      .then(r => r.json()).then(resp => {
        if(resp && resp.ok){ alert('Added to album'); }
        else alert('Could not add to album');
      }).catch(()=>alert('Could not add to album'));
  }).catch(()=>alert('Could not fetch albums'));
}
