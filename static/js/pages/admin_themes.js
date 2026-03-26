// Apply backgrounds to theme swatches using data attributes to avoid template logic inside CSS
(function(){
  const nodes = document.querySelectorAll('.theme-swatch');
  nodes.forEach(function(n){
    const style = (n.getAttribute('data-style')||'gradient').toLowerCase();
    const c1 = n.getAttribute('data-btn1') || '#4f8cff';
    const c2 = n.getAttribute('data-btn2') || '#8338EC';
    if (style === 'solid'){
      n.style.background = c1;
      n.style.backgroundImage = 'none';
    } else {
      n.style.backgroundImage = 'linear-gradient(90deg,' + c1 + ',' + c2 + ')';
    }
  });
})();

// Live Preview: Auto-scale and event handlers for theme customization
(function(){
  const root = document.getElementById('preview-root');
  if (!root) return;

  // Auto-scale the web preview to fit the wrapper width
  const wrapper = root.closest('.web-preview-wrapper');
  const web = root.querySelector('.web-preview');

  function scalePreview(){
    if (!wrapper || !web) return;
    const base = parseInt(web.getAttribute('data-base') || '1100', 10);
    // Reset to natural size to measure height
    web.style.transform = 'scale(1)';
    const available = wrapper.clientWidth - 2; // account for borders
    const scale = Math.min(1, available / base);
    web.style.transform = 'scale(' + scale + ')';
    // lock wrapper height to scaled content height to avoid cut-off
    const naturalHeight = web.scrollHeight; // height at scale(1)
    wrapper.style.height = Math.ceil(naturalHeight * scale) + 'px';
  }

  window.addEventListener('resize', scalePreview);
  requestAnimationFrame(scalePreview);

  const seedForm = document.getElementById('seed-form');
  const seedBtn = document.getElementById('seed-btn');
  if (seedForm && seedBtn){
    seedForm.addEventListener('submit', function(){ seedBtn.disabled = true; seedBtn.textContent = 'Seeding…'; });
  }

  const map = {
    BackgroundColour: '--card',
    TextColour: '--card-text',
    ButtonColour1: '--btn1',
    ButtonColour2: '--btn2',
    AccentColour: '--accent',
    FontFamily: '--font',
    InputBackgroundColour: '--input-bg',
    DropzoneBackgroundColour: '--dropzone-bg'
  };

  function apply(id){
    const el = document.getElementById(id);
    if (!el) return;
    let v = el.value || '';
    // sync paired hex input if present
    const hexInput = document.getElementById(id + 'Hex');
    if (hexInput) { hexInput.value = (v || '').toUpperCase(); }
    const cssVar = map[id];
    if (!cssVar) return;
    root.style.setProperty(cssVar, v);
    // Reflow might affect height slightly (fonts), rescale lazily
    if (id === 'FontFamily'){
      setTimeout(scalePreview, 50);
    }
  }

  ['BackgroundColour','TextColour','ButtonColour1','ButtonColour2','AccentColour','FontFamily','InputBackgroundColour','DropzoneBackgroundColour'].forEach(function(id){
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener('input', function(){ apply(id); });
  });

  // Allow typing into hex fields
  ['BackgroundColour','TextColour','ButtonColour1','ButtonColour2','AccentColour','InputBackgroundColour','DropzoneBackgroundColour'].forEach(function(id){
    const hex = document.getElementById(id + 'Hex');
    if (!hex) return;
    hex.addEventListener('input', function(){
      let v = hex.value || '';
      if (v && !v.startsWith('#') && !v.startsWith('rgb')) v = '#' + v;
      const sw = document.getElementById(id);
      if (sw){ sw.value = v; }
      const cssVar = map[id];
      if (cssVar){ root.style.setProperty(cssVar, v); }
      updateContrast();
    });
  });

  // Contrast calculator (WCAG)
  function hexToRgb(h){
    h = (h||'').trim();
    if (!h) return null;
    if (h[0] === '#') h = h.slice(1);
    if (h.length === 3){ h = h.split('').map(c=>c+c).join(''); }
    const num = parseInt(h, 16);
    if (isNaN(num)) return null;
    return { r:(num>>16)&255, g:(num>>8)&255, b:num&255 };
  }

  function relLum({r,g,b}){
    const sr=[r,g,b].map(v=>{
      v/=255;
      return v<=0.03928? v/12.92: Math.pow((v+0.055)/1.055,2.4);
    });
    return 0.2126*sr[0] + 0.7152*sr[1] + 0.0722*sr[2];
  }

  function contrastRatio(bg, tx){
    const L1=Math.max(bg,tx), L2=Math.min(bg,tx);
    return (L1+0.05)/(L2+0.05);
  }

  function updateContrast(){
    const bg = hexToRgb(document.getElementById('BackgroundColour').value);
    const tx = hexToRgb(document.getElementById('TextColour').value);
    const panel = document.getElementById('contrast-panel');
    if(!panel || !bg || !tx){ return; }
    const r = contrastRatio(relLum(bg), relLum(tx));
    const ratioEl = document.getElementById('contrast-ratio');
    if (ratioEl){ ratioEl.textContent = r.toFixed(2) + ':1'; }
    const aa = document.getElementById('contrast-aa');
    const aaa = document.getElementById('contrast-aaa');
    if (aa){
      aa.style.background = r >= 4.5 ? '#153a2b' : '#3a1514';
      aa.style.borderColor = r >= 4.5 ? '#2a6a46' : '#5a1f1a';
    }
    if (aaa){
      aaa.style.background = r >= 7 ? '#153a2b' : '#3a1514';
      aaa.style.borderColor = r >= 7 ? '#2a6a46' : '#5a1f1a';
    }
  }

  ['BackgroundColour','TextColour'].forEach(function(id){
    const el=document.getElementById(id);
    if (el){ el.addEventListener('input', updateContrast); }
  });
  updateContrast();

  // Final scale pass once everything is set
  setTimeout(scalePreview, 0);

  const resetBtn = document.getElementById('reset-preview');
  if (resetBtn){ resetBtn.addEventListener('click', function(){ window.location.reload(); }); }

  // Font family selector -> hidden field binding
  const ffSelect = document.getElementById('FontFamilySelect');
  const ffHidden = document.getElementById('FontFamily');
  function setFontHidden(val){ if (ffHidden){ ffHidden.value = val; } apply('FontFamily'); }
  if (ffSelect){ ffSelect.addEventListener('change', function(){ setFontHidden(ffSelect.value); }); }

  // Button style toggle: gradient vs solid
  const bsGrad = document.getElementById('ButtonStyleGradient');
  const bsSolid = document.getElementById('ButtonStyleSolid');
  function applyButtonStyle(){
    if (!root) return;
    const isSolid = !!(bsSolid && bsSolid.checked);
    if (isSolid){
      root.classList.add('is-solid');
      root.classList.remove('is-gradient');
    } else {
      root.classList.add('is-gradient');
      root.classList.remove('is-solid');
    }
    // Show/hide Button 2 when solid vs gradient
    const b2w = document.getElementById('ButtonColour2Wrap');
    if (b2w){ b2w.style.display = isSolid ? 'none' : ''; }
    scalePreview();
  }
  if (bsGrad) bsGrad.addEventListener('change', applyButtonStyle);
  if (bsSolid) bsSolid.addEventListener('change', applyButtonStyle);
  // Default to gradient selected on load
  if (bsGrad && !bsGrad.checked && !(bsSolid && bsSolid.checked)) { bsGrad.checked = true; }
  applyButtonStyle();

  // Preview toggles
  const tCover = document.getElementById('pv-banner');
  const tProgress = document.getElementById('pv-progress');
  const tUploads = document.getElementById('pv-uploads');
  const coverWrap = document.getElementById('pv-cover-wrap');
  const prog = document.getElementById('progress-container');
  const uploadsWrap = document.getElementById('pv-uploads-wrap');
  function applyToggles(){
    if (coverWrap && tCover){
      coverWrap.style.display = tCover.checked ? '' : 'none';
      // Use the banner image as a blurred page background to simulate frosted backdrop
      const pvImg = document.getElementById('pv-cover-img');
      const src = pvImg && pvImg.currentSrc ? pvImg.currentSrc : '';
      if (tCover.checked && src){
        root.style.setProperty('--bg-image', `url('${src}')`);
        root.style.setProperty('--bg-size', 'cover');
        root.style.setProperty('--bg-position', 'center');
        // Add an overlay blur via filter on a pseudo element
        root.style.setProperty('--bg-blur', '28px');
        // Show only the blurred background copy (via ::before). Prevent the base element
        // from also drawing the background image to keep the foreground banner crisp.
        root.style.setProperty('background-image', 'none', 'important');
      } else {
        root.style.setProperty('--bg-image', 'none');
        root.style.setProperty('background-image', '');
      }
    }
    if (prog && tProgress){
      prog.style.display = tProgress.checked ? '' : 'none';
    }
    if (uploadsWrap && tUploads){
      uploadsWrap.style.display = tUploads.checked ? '' : 'none';
    }
    scalePreview();
  }
  [tCover, tProgress, tUploads].forEach(function(x){ if (x) x.addEventListener('change', applyToggles); });
  applyToggles();

  // Simulated progress animation
  if (tProgress && prog){
    tProgress.addEventListener('change', function(){
      if (!tProgress.checked) return;
      const fill = prog.querySelector('.progress-fill');
      if (!fill) return;
      let p = 0;
      fill.style.width = '0%';
      const id = setInterval(function(){
        p += 7;
        fill.style.width = Math.min(p,100) + '%';
        if (p>=100){ clearInterval(id); }
      }, 200);
    });
  }
})();
