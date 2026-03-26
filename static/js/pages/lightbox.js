// Lightbox component: modal image carousel with keyboard navigation and focus trap
(function(){
  if (window.Lightbox) return; // singleton

  const state = {
    images: [],
    captions: [],
    index: 0,
    inited: false
  };

  const focusableSelector = 'a[href], area[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]), [tabindex]:not([tabindex="-1"])';
  const lb = document.getElementById('lightbox');
  const img = document.getElementById('lb-img');
  const cap = document.getElementById('lb-caption');
  const btnPrev = lb.querySelector('.lightbox-prev');
  const btnNext = lb.querySelector('.lightbox-next');
  const btnClose = lb.querySelector('.lightbox-close');

  function render(){
    if (!state.images.length) return;
    img.src = state.images[state.index];
    cap.textContent = (state.captions[state.index] || '');
  }

  function trapFocus(e){
    if (lb.getAttribute('aria-hidden') === 'true') return;
    if (e.key !== 'Tab') return;
    const focusables = lb.querySelectorAll(focusableSelector);
    if (!focusables.length) return;
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    if (e.shiftKey){
      if (document.activeElement === first){ e.preventDefault(); last.focus(); }
    } else {
      if (document.activeElement === last){ e.preventDefault(); first.focus(); }
    }
  }

  function onOverlayClick(e){
    if (e.target === lb) api.close();
  }

  function onKey(e){
    if (lb.getAttribute('aria-hidden') === 'true') return;
    if (e.key === 'Escape') api.close();
    if (e.key === 'ArrowLeft') api.prev();
    if (e.key === 'ArrowRight') api.next();
  }

  const api = {
    init(){
      if (state.inited) return;
      state.inited = true;
      btnPrev.addEventListener('click', api.prev);
      btnNext.addEventListener('click', api.next);
      btnClose.addEventListener('click', api.close);
      lb.addEventListener('click', onOverlayClick);
      document.addEventListener('keydown', onKey);
      lb.addEventListener('keydown', trapFocus);
    },
    setData(images, captions){
      state.images = Array.isArray(images)?images:[];
      state.captions = Array.isArray(captions)?captions:[];
    },
    open(i){
      api.init();
      if (!state.images.length) return;
      state.index = Math.max(0, Math.min(i||0, state.images.length-1));
      render();
      lb.classList.add('is-open');
      lb.setAttribute('aria-hidden','false');
      document.body.classList.add('modal-open');
      try {
        btnClose.focus();
      } catch(e){}
    },
    close(){
      lb.classList.remove('is-open');
      lb.setAttribute('aria-hidden','true');
      document.body.classList.remove('modal-open');
    },
    prev(){
      if (!state.images.length) return;
      state.index = (state.index - 1 + state.images.length) % state.images.length;
      render();
    },
    next(){
      if (!state.images.length) return;
      state.index = (state.index + 1) % state.images.length;
      render();
    }
  };

  window.Lightbox = api;
})();
