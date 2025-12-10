(function(){
  const cfg = (window.EPU && window.EPU.liveCfg) || {}; const code = cfg.code || '';
  const stage = document.getElementById('live-stage');
  const statusEl = document.getElementById('status');
  const prevBtn = document.getElementById('prev');
  const nextBtn = document.getElementById('next');
  const playBtn = document.getElementById('play');
  const pauseBtn = document.getElementById('pause');
  const incBtn = document.getElementById('inc');
  const decBtn = document.getElementById('dec');
  const delayDisp = document.getElementById('delay-display');
  const fsBtn = document.getElementById('fs');
  const wrap = document.querySelector('.live-wrap');

  let list = []; let cursor = -1; let timer = null; let playing = false; let maxId = null;
  let delayMs = 3000;
  function renderDelay(){ if (delayDisp) delayDisp.textContent = Math.round(delayMs/1000)+'s'; }
  function setDelay(ms){ delayMs = Math.min(10000, Math.max(1500, parseInt(ms||3000,10))); renderDelay(); }
  renderDelay();
  if (incBtn) incBtn.onclick = function(){ setDelay(delayMs + 500); };
  if (decBtn) decBtn.onclick = function(){ setDelay(delayMs - 500); };

  function setStatus(t){ if (statusEl) statusEl.textContent = t; }

  function clearTimer(){ if (timer){ clearTimeout(timer); timer = null; } }
  function scheduleNext(){ clearTimer(); if (!playing) return; timer = setTimeout(()=>{ show(cursor+1); }, delayMs); }

  function mountMedia(item){
    if (!item) return;
    // Clean up any lingering non-current media (e.g., rapid next/prev presses)
    const allMedia = Array.from(stage.querySelectorAll('.live-media'));
    const currentEl = allMedia.find(el => el.classList.contains('current')) || null;
    allMedia.forEach(el => { if (el !== currentEl) { try { el.parentNode && el.parentNode.removeChild(el); } catch(_){} } });
    const prev = currentEl;

    if (item.type === 'image'){
      const img = document.createElement('img');
      img.className = 'live-media fade-enter';
      img.src = item.src; // full-quality original
      img.alt = '';
      // When the image has loaded, fade it in over the previous one
      img.onload = function(){
        img.classList.add('fade-enter-active');
      };
      // After fade-in completes, remove previous and mark current
      const onImgTransitionEnd = function(ev){
        if (ev.propertyName !== 'opacity') return;
        img.removeEventListener('transitionend', onImgTransitionEnd);
        if (prev && prev.parentNode) { try { prev.parentNode.removeChild(prev); } catch(_){} }
        img.classList.remove('fade-enter');
        img.classList.add('current');
        if (playing) scheduleNext();
      };
      img.addEventListener('transitionend', onImgTransitionEnd);
      // Append new on top so it can fade in; previous stays until fade completes
      stage.appendChild(img);
      // If there was no previous, make this immediately current (no dark gap)
      if (!prev){
        // If already loaded from cache, trigger transition immediately
        if (img.complete) { img.classList.add('fade-enter-active'); }
      }
    } else if (item.type === 'video'){
      const v = document.createElement('video');
      v.className = 'live-media fade-enter';
      v.src = item.src; v.autoplay = true; v.muted = true; v.loop = false; v.controls = false; v.playsInline = true;
      v.oncanplay = function(){ v.classList.add('fade-enter-active'); };
      const onVidTransitionEnd = function(ev){
        if (ev.propertyName !== 'opacity') return;
        v.removeEventListener('transitionend', onVidTransitionEnd);
        if (prev && prev.parentNode) { try { prev.parentNode.removeChild(prev); } catch(_){} }
        v.classList.remove('fade-enter');
        v.classList.add('current');
      };
      v.addEventListener('transitionend', onVidTransitionEnd);
      v.onended = function(){ scheduleNext(); };
      stage.appendChild(v);
      if (!prev){
        // If video can play immediately, kick off fade quickly
        if (v.readyState >= 2) { v.classList.add('fade-enter-active'); }
      }
    }
  }

  function show(idx){
    if (!list || !list.length) return;
    cursor = (idx % list.length + list.length) % list.length; // safe modulo
    mountMedia(list[cursor]);
  }

  async function fetchData(initial){
    try {
      let url = `/live/${encodeURIComponent(code)}/data`;
      if (!initial && maxId !== null){ url += `?since=${maxId}`; }
      const res = await fetch(url, { headers: { 'Accept': 'application/json' } });
      if (!res.ok){ setStatus('Disconnected'); return; }
      const data = await res.json();
      if (!data || data.ok !== true) { setStatus('Disconnected'); return; }
      const files = Array.isArray(data.files) ? data.files : [];
      if (typeof data.max_id === 'number') maxId = data.max_id;
      if (initial){
        list = files;
        if (list.length === 0){ setStatus('Waiting for uploads…'); }
        else { setStatus(`${list.length} items`); show(0); }
      } else if (files.length){
        const prevLen = list.length; list = list.concat(files);
        setStatus(`${list.length} items`);
        // If we were waiting, kick off from the first new item
        if (prevLen === 0){ show(0); }
      }
    } catch(e){ setStatus('Network error'); }
  }

  function play(){ if (!list.length){ show(0); } playing = true; playBtn.style.display='none'; pauseBtn.style.display=''; scheduleNext(); }
  function pause(){ playing = false; playBtn.style.display=''; pauseBtn.style.display='none'; clearTimer(); }
  function toggle(){ if (playing) pause(); else play(); }
  function prev(){ pause(); show(cursor-1); }
  function next(){ pause(); show(cursor+1); }

  if (prevBtn) prevBtn.onclick = prev;
  if (nextBtn) nextBtn.onclick = next;
  if (playBtn) playBtn.onclick = play;
  if (pauseBtn) pauseBtn.onclick = pause;

  function isFullscreen(){ return document.fullscreenElement === wrap; }
  async function enterFullscreen(){ if (!wrap) return; try { await wrap.requestFullscreen(); } catch(_){} if (wrap) wrap.setAttribute('data-fullscreen','true'); if (fsBtn) fsBtn.textContent = 'Exit Fullscreen'; }
  async function exitFullscreen(){ try { if (document.fullscreenElement) await document.exitFullscreen(); } catch(_){} if (wrap) wrap.setAttribute('data-fullscreen','false'); if (fsBtn) fsBtn.textContent = 'Fullscreen'; }
  if (fsBtn) fsBtn.onclick = function(){ if (isFullscreen()) exitFullscreen(); else enterFullscreen(); };
  document.addEventListener('fullscreenchange', function(){ const on = document.fullscreenElement === wrap; if (wrap) wrap.setAttribute('data-fullscreen', on ? 'true' : 'false'); if (fsBtn) fsBtn.textContent = on ? 'Exit Fullscreen' : 'Fullscreen'; });

  // Keyboard shortcuts (including Escape to exit fullscreen)
  window.addEventListener('keydown', function(e){
    if (e.key === '+' || e.key === '=') { try { window.EPU.liveDelay(1); } catch(_){} }
    else if (e.key === '-' || e.key === '_') { try { window.EPU.liveDelay(-1); } catch(_){} }
    else if (e.key === ' ') { e.preventDefault(); try { window.EPU.liveToggle(); } catch(_){} }
    else if (e.key === 'ArrowLeft') { try { window.EPU.livePrev(); } catch(_){} }
    else if (e.key === 'ArrowRight') { try { window.EPU.liveNext(); } catch(_){} }
    else if (e.key === 'Escape') { try { exitFullscreen(); } catch(_){} }
  });

  // Auto-hide HUD when idle (non-fullscreen), restore on interaction
  let idleTimer = null; const IDLE_MS = 3000;
  function setIdle(on){ if (!wrap) return; wrap.setAttribute('data-idle', on ? 'true' : 'false'); }
  function rescheduleIdle(){ if (!wrap) return; if (document.fullscreenElement) { setIdle(false); return; } setIdle(false); if (idleTimer) { clearTimeout(idleTimer); idleTimer = null; } idleTimer = setTimeout(()=>{ setIdle(true); }, IDLE_MS); }
  ['mousemove','mousedown','touchstart','keydown'].forEach(evt => { window.addEventListener(evt, rescheduleIdle, { passive: true }); });
  // Start idle timer after load
  rescheduleIdle();

  // Public helpers for keyboard shortcuts
  window.EPU = window.EPU || {};
  window.EPU.livePrev = prev; window.EPU.liveNext = next; window.EPU.liveToggle = toggle;
  window.EPU.liveDelay = function(delta){ setDelay(delayMs + (delta>0?500:-500)); };

  // Boot
  fetchData(true);
  // Poll for new files every 6s
  setInterval(()=>{ fetchData(false); }, 6000);
})();
