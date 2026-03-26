document.addEventListener('DOMContentLoaded', function(){
  const sel = document.getElementById('theme_id');
  const eventTypeSel = document.getElementById('event_type_id');
  const customTypeWrap = document.getElementById('custom-event-type-wrap');
  const customTypeInput = document.getElementById('custom_event_type');
  const customizer = document.getElementById('customizer');
  const editorLike = document.getElementById('theme-editor-like');
  const previewWrap = document.getElementById('admin-like-preview');
  const meta = document.getElementById('theme-meta');
  const swatch = document.getElementById('theme-swatch');
  const desc = document.getElementById('theme-desc');
  const primary = document.getElementById('primary_color');
  const accent = document.getElementById('accent_color');
  const secondary = document.getElementById('secondary_color');
  const textColor = document.getElementById('text_color');
  const fontSelect = document.getElementById('font_family');
  const ffSelectEl = document.getElementById('FontFamilySelect');
  const bg = document.getElementById('background_color');
  const welcome = document.getElementById('welcome_message');
  const instructions = document.getElementById('upload_instructions');
  const banner = document.getElementById('banner_image');
  // Use pv-cover-img to display banner inside the card, and pv-frost-wrap for the frosted background behind the form
  const pTitle = document.getElementById('guest-title');
  const pDesc = document.getElementById('guest-instructions');
  const pBtn = document.getElementById('pre22view-button');
  const pRoot = document.getElementById('preview-root');
  const frostWrap = document.getElementById('pv-frost-wrap');
  const pvBanner = document.getElementById('pv-banner');
  const pvProgress = document.getElementById('pv-progress');
  const pvUploads = document.getElementById('pv-uploads');
  const coverWrap = document.getElementById('pv-cover-wrap');
  
  const removeBannerHidden = document.getElementById('remove_banner');
  const removeBannerBtn = document.getElementById('remove-banner-btn');
  // If a banner preview is present on load, display the remove button so user can clear it
  (function(){
    try{
      const assetPreview = document.getElementById('asset-banner-preview');
      const nameEl = document.getElementById('banner_file_name');
      if (removeBannerBtn){
        if ((assetPreview && assetPreview.getAttribute('src')) || (nameEl && nameEl.textContent && nameEl.textContent !== 'No file chosen')){
          removeBannerBtn.style.display = '';
        } else {
          removeBannerBtn.style.display = 'none';
        }
      }
    }catch(e){}
  })();
  // Example swatches (removed for simplified preview)
  const exText = document.getElementById('ex-text');
  const exAccent = document.getElementById('ex-accent');
  const exBg = document.getElementById('ex-bg');
  const buttonStyle = document.getElementById('button_style');
  const cornerRadius = document.getElementById('corner_radius');
  const headingSize = document.getElementById('heading_size');
  const showCover = document.getElementById('show_cover');
  const typeGrad = document.getElementById('ButtonStyleGradient');  // Use actual radio button
  const typeSolid = document.getElementById('ButtonStyleSolid');    // Use actual radio button
  const gradientControls = document.getElementById('gradient-controls');
  const gradientDirWrap = document.getElementById('gradient-dir-wrap');
  const gradientTypeSelect = document.getElementById('ButtonGradientStyle');
  const bsSolidRadio = document.getElementById('ButtonStyleSolid');
  const bsGradRadio = document.getElementById('ButtonStyleGradient');
  // Removed global reset button
  const fullBtn = document.getElementById('full-button-preview');
  // Per-card reset links
  const resetCardButton = document.getElementById('reset-card-button');
  const resetCardColors = document.getElementById('reset-card-colors');
  const resetCardTypography = document.getElementById('reset-card-typography');
  

  // Initial values from server via JSON script to keep JS valid
  const initEl = document.getElementById('theme-init');
  const themeInit = initEl ? JSON.parse(initEl.textContent) : {};
  let themeText = themeInit.text || '#0F0E17';
  let themeFont = themeInit.font || 'Inter, Arial, sans-serif';
  let themeButton2 = themeInit.button2 || '#FF8906';

  function isThemeSelected(){
    return !!(sel && sel.value && sel.value.trim() !== '');
  }

  function getSelectedThemeData(){
    const opt = sel.options[sel.selectedIndex];
    if (!opt) return null;
    return {
      b1: opt.getAttribute('data-button1') || '#F25F4C',
      b2: opt.getAttribute('data-button2') || '#FF8906',
      bg: opt.getAttribute('data-bg') || '#ffffff',
      text: opt.getAttribute('data-text') || '#0F0E17',
      font: opt.getAttribute('data-font') || 'Inter, Arial, sans-serif',
  accent: opt.getAttribute('data-accent') || '#222',
  input_bg: opt.getAttribute('data-input-bg') || '#15161e',
  dropzone_bg: opt.getAttribute('data-dropzone-bg') || '#121424',
  style: opt.getAttribute('data-style') || 'gradient',
  desc: opt.getAttribute('data-desc') || ''
    };
  }

  function toggleCustomizer(){
    const useTheme = isThemeSelected();
    // Always show preview; only hide the custom editor when a prebuilt theme is selected
    if (previewWrap) previewWrap.style.display = '';
    if (editorLike) editorLike.style.display = useTheme ? 'none' : '';
    if (customizer){
      customizer.style.display = useTheme ? 'none' : '';
      // Disable/enable inputs within so they don't submit when hidden
      customizer.querySelectorAll('input, select, textarea, button').forEach(function(el){ el.disabled = useTheme; });
    }
    if (meta){ meta.style.display = useTheme ? 'flex' : 'none'; }
  }

  // Place the custom theme editor inside the Theme card just below the selector
  (function(){
    try {
      const themeSelect = document.getElementById('theme_id');
      const themeCard = themeSelect ? themeSelect.closest('.card') : null;
      const rowBelow = themeSelect ? themeSelect.closest('.grid') : null;
      if (editorLike && themeCard && rowBelow) {
        // Avoid nested card visuals; the editor should look like a section inside the Theme card
        editorLike.classList.remove('card');
        // Ensure spacing is compact under the selector row
        editorLike.style.margin = '8px 0 0 0';
        if (editorLike.parentElement !== themeCard) {
          rowBelow.insertAdjacentElement('afterend', editorLike);
        }
      }
    } catch (e) { /* no-op */ }
  })();

  function applyThemeFromSelect(){
    toggleCustomizer();
    // Update theme meta preview immediately
    const data = getSelectedThemeData();
    if (meta && data){
      if (swatch){
        swatch.style.background = `linear-gradient(90deg, ${data.b1} 0%, ${data.b2} 100%)`;
        swatch.style.boxShadow = `inset 0 0 0 4px ${data.bg || '#ffffff'}`;
      }
      if (desc){ desc.textContent = data.desc || ''; }
    }
  // Keep hidden button_style in sync with selected theme, and check corresponding radio
  const style = (data && data.style) || 'gradient';
  const hidden = document.getElementById('button_style'); if (hidden){ hidden.value = style; }
  // Also check the radio button to reflect the theme's button style
  if (style === 'solid') {
    if (bsSolidRadio) bsSolidRadio.checked = true;
    if (bsGradRadio) bsGradRadio.checked = false;
  } else {
    if (bsGradRadio) bsGradRadio.checked = true;
    if (bsSolidRadio) bsSolidRadio.checked = false;
  }
    updatePreview();
  }
  if (sel) sel.addEventListener('change', applyThemeFromSelect);

  // Event Type: show custom input when "Other" is selected and place side-by-side; otherwise stack
  function updateCustomTypeVisibility(){
    if (!eventTypeSel || !customTypeWrap || !customTypeInput) return;
    const isOther = String(eventTypeSel.value || '').toLowerCase() === 'other';
    customTypeWrap.style.display = isOther ? '' : 'none';
    customTypeInput.disabled = !isOther;
    if (!isOther) { customTypeInput.value = ''; }
    const group = document.getElementById('event-type-group');
    const wrap = document.getElementById('event-type-wrap');
    if (group){ group.style.gridTemplateColumns = isOther ? '1fr 1fr' : '1fr'; }
    if (wrap){ wrap.style.marginRight = isOther ? '6px' : '0'; }
  }
  if (eventTypeSel){ eventTypeSel.addEventListener('change', updateCustomTypeVisibility); }
  updateCustomTypeVisibility();

  function hexToRgb(hex){
    if (!hex) return {r:0,g:0,b:0};
    const h = hex.replace('#','');
    const v = h.length === 3 ? h.split('').map(c=>c+c).join('') : h;
    const num = parseInt(v, 16);
    return { r: (num >> 16) & 255, g: (num >> 8) & 255, b: num & 255 };
  }
  function relLuminance({r,g,b}){
    const srgb = [r,g,b].map(v=>v/255).map(v=> v<=0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4));
    return 0.2126*srgb[0] + 0.7152*srgb[1] + 0.0722*srgb[2];
  }
  function mix(hex1, hex2){
    const a = hexToRgb(hex1), b = hexToRgb(hex2);
    return { r: Math.round((a.r+b.r)/2), g: Math.round((a.g+b.g)/2), b: Math.round((a.b+b.b)/2) };
  }
  function rgbToHex({r,g,b}){
    const to2 = (n)=>n.toString(16).padStart(2,'0');
    return `#${to2(r)}${to2(g)}${to2(b)}`;
  }
  function getContrastColor(gradStart, gradEnd, bgColor){
    // Approximate visible bg as average of gradient colors laid over bg
    const gMix = mix(gradStart || '#000000', gradEnd || '#000000');
    const gLum = relLuminance(gMix);
    // Compare against white/black
    const whiteLum = relLuminance({r:255,g:255,b:255});
    const blackLum = relLuminance({r:0,g:0,b:0});
    const cWhite = (Math.max(gLum, whiteLum)+0.05)/(Math.min(gLum, whiteLum)+0.05);
    const cBlack = (Math.max(gLum, blackLum)+0.05)/(Math.min(gLum, blackLum)+0.05);
    return cWhite >= cBlack ? '#FFFFFF' : '#111111';
  }

  function updatePreview(){
    const useTheme = isThemeSelected();
    const data = useTheme ? getSelectedThemeData() : null;
    // Helper to get current value from visible theme-editor controls
    function val(id, fallback){ var el = document.getElementById(id); return (el && el.value) || fallback; }

    // Colors
    // When a theme is selected, its values take precedence. In Custom mode, prefer visible editor inputs.
    const bgColor = useTheme
      ? (data && data.bg)
      : val('BackgroundColour', (bg && bg.value) || '#ffffff');
    const txtColor = useTheme
      ? (data && data.text)
      : val('TextColour', (textColor && textColor.value) || themeText || '#0F0E17');
    const gradStart = useTheme
      ? (data && data.b1)
      : val('ButtonColour1', (primary && primary.value) || '#F25F4C');
    const gradEnd = useTheme
      ? (data && data.b2)
      : val('ButtonColour2', (secondary && secondary.value) || themeButton2 || '#FF8906');
    const accentCol = useTheme
      ? (data && data.accent)
      : val('AccentColour', (accent && accent.value) || '#222');
    // Font: prefer theme font when theme selected; otherwise use the editor's FontFamilySelect, then hidden fallback
    const fontFam = (useTheme && data && data.font) || (ffSelectEl && ffSelectEl.value) || (fontSelect && fontSelect.value) || themeFont || 'Inter, Arial, sans-serif';
  const btnText = getContrastColor(gradStart, gradEnd, bgColor);

    // Drive theme via CSS variables for exact parity
    if (pRoot){
      pRoot.style.setProperty('--bg', bgColor || '#ffffff');
      pRoot.style.setProperty('--text', txtColor || '#0F0E17');
      pRoot.style.setProperty('--font', fontFam || 'Inter, Arial, sans-serif');
      pRoot.style.setProperty('--btn1', gradStart || '#F25F4C');
      pRoot.style.setProperty('--btn2', gradEnd || '#FF8906');
      pRoot.style.setProperty('--btn-text', btnText || '#ffffff');
      // Ensure card and borders match selected theme, not stale custom vars
      pRoot.style.setProperty('--card', bgColor || '#0f0f12');
      pRoot.style.setProperty('--card-text', txtColor || '#e9eef6');
      pRoot.style.setProperty('--accent', accentCol || 'rgba(255,255,255,0.18)');
      // Sync to hidden submit fields so backend receives values
      const mapHidden = {
        primary_color: gradStart,
        secondary_color: gradEnd,
        text_color: txtColor,
        background_color: bgColor,
        accent_color: accentCol || (document.getElementById('AccentColour') && document.getElementById('AccentColour').value) || (accent && accent.value) || '#222',
        font_family: (ffSelectEl && ffSelectEl.value) || (fontSelect && fontSelect.value) || 'Inter, Arial, sans-serif',
        input_background_color: useTheme ? (data && data.input_bg) : ((document.getElementById('InputBackgroundColour') && document.getElementById('InputBackgroundColour').value) || '#15161e'),
        dropzone_background_color: useTheme ? (data && data.dropzone_bg) : ((document.getElementById('DropzoneBackgroundColour') && document.getElementById('DropzoneBackgroundColour').value) || '#121424')
      };
      Object.keys(mapHidden).forEach(function(k){ var el=document.getElementById(k); if (el && mapHidden[k]) el.value = mapHidden[k]; });
      // Apply to CSS vars so the previewed form widgets pick up the themed surfaces
      pRoot.style.setProperty('--input-bg', mapHidden.input_background_color);
      pRoot.style.setProperty('--dropzone-bg', mapHidden.dropzone_background_color);
    }
    // Toggle gradient vs solid on root class; for selected theme, honor its style
    if (pRoot){
      const styleVal = (bsSolidRadio && bsSolidRadio.checked)
        ? 'solid'
        : ((bsGradRadio && bsGradRadio.checked) ? 'gradient' : ((buttonStyle && buttonStyle.value) || (useTheme && data && data.style) || 'gradient'));
      if (gradientControls) { gradientControls.style.display = (styleVal === 'solid') ? 'none' : 'grid'; }
      if (gradientDirWrap) {
          const bgsEl = document.getElementById('ButtonGradientStyle');
          const selectedType = (bgsEl && bgsEl.value) || 'linear';
        gradientDirWrap.style.display = (styleVal === 'solid' || selectedType === 'radial') ? 'none' : 'block';
      }
      if (styleVal === 'solid'){
        pRoot.classList.remove('is-gradient');
        pRoot.classList.add('is-solid');
      } else {
        pRoot.classList.remove('is-solid');
        pRoot.classList.add('is-gradient');
      }
      // Build gradient CSS and expose as CSS var for buttons/progress
      const dirSel = document.getElementById('ButtonGradientDirection');
      const stySel = document.getElementById('ButtonGradientStyle');
      const dir = (dirSel && dirSel.value) || '90deg';
      const sty = (stySel && stySel.value) || 'linear';
      const gradCss = sty === 'radial'
        ? `radial-gradient(circle at center, ${gradStart} 0%, ${gradEnd} 100%)`
        : `linear-gradient(${dir}, ${gradStart} 0%, ${gradEnd} 100%)`;
      pRoot.style.setProperty('--btn-gradient', gradCss);
      // Keep hidden button_style in sync so saves donâ€™t override theme
      var bsHidden = document.getElementById('button_style');
      if (bsHidden) { bsHidden.value = styleVal; }
    }
    // Apply heading class (size) via classes
    if (headingSize && pTitle){
      pTitle.classList.remove('heading-s','heading-m','heading-l');
      pTitle.classList.add('heading-' + headingSize.value);
    }
    // Apply radius via class on card container
  const card = document.querySelector('#preview-root .theme-card');
    if (card && cornerRadius){
      card.classList.remove('radius-subtle','radius-rounded','radius-sharp');
      card.classList.add('radius-' + cornerRadius.value);
    }
    // Ensure the card visually reflects the selected background and border immediately
    if (card){
      card.style.background = bgColor || '';
      card.style.borderColor = accentCol || '';
    }
    // Text content
    pTitle.textContent = (welcome.value || 'Guest Upload');
    pDesc.textContent = (instructions.value || 'Welcome! Please upload your files for this event.');
  // Individual colour swatches removed; rely on Live Preview and full button preview only

    // Theme meta preview
    if (meta){
      if (useTheme){
        if (swatch){
          const dirSel = document.getElementById('ButtonGradientDirection');
          const stySel = document.getElementById('ButtonGradientStyle');
          const dir = (dirSel && dirSel.value) || '90deg';
          const sty = (stySel && stySel.value) || 'linear';
          const gradCss = sty === 'radial'
            ? `radial-gradient(circle at center, ${gradStart} 0%, ${gradEnd} 100%)`
            : `linear-gradient(${dir}, ${gradStart} 0%, ${gradEnd} 100%)`;
          swatch.style.background = gradCss;
          swatch.style.boxShadow = `inset 0 0 0 4px ${bgColor}`;
        }
        if (desc){ desc.textContent = (data && data.desc) || ''; }
      } else {
        if (swatch){ swatch.style.background = ''; swatch.style.boxShadow = ''; }
        if (desc){ desc.textContent = ''; }
      }
    }
  }

  const gradDirEl = document.getElementById('ButtonGradientDirection');
  const gradStyEl = document.getElementById('ButtonGradientStyle');
  [primary, secondary, textColor, fontSelect, ffSelectEl, accent, bg, welcome, instructions, buttonStyle, cornerRadius, headingSize, showCover, gradDirEl, gradStyEl].forEach(function(el){
    if (el) el.addEventListener('input', updatePreview);
  });
  [gradDirEl, gradStyEl].forEach(function(el){ if (el) el.addEventListener('change', updatePreview); });
  if (gradientTypeSelect) { gradientTypeSelect.addEventListener('change', updatePreview); }
  if (banner) {
    banner.addEventListener('change', function(){
  if (removeBannerHidden) removeBannerHidden.value = '0';
  if (removeBannerToggle) { removeBannerToggle.checked = false; removeBannerToggle.disabled = false; }
      const file = banner.files && banner.files[0];
      const nameEl = document.getElementById('banner_file_name');
      if (nameEl) { nameEl.textContent = file ? file.name : 'No file chosen'; }
      if (!file) return updatePreview();
  // Show remove button once a file is chosen
  if (removeBannerBtn) removeBannerBtn.style.display = '';
      const type = (file.type || '').toLowerCase();
      if (!type.startsWith('image/')){
        banner.value = '';
        if (nameEl) nameEl.textContent = 'No file chosen';
        if (window.snackbar && window.snackbar.show){ window.snackbar.show('Please choose an image file.'); }
        else { alert('Please choose an image file.'); }
        return;
      }
      const reader = new FileReader();
      reader.onload = function(e){
        // Show as banner image in live preview
        const img = document.getElementById('pv-cover-img');
        if (img) { img.src = e.target.result; img.removeAttribute('hidden'); }
        if (coverWrap) { coverWrap.style.display = ''; }
        // Also show in assets preview card
        const ap = document.getElementById('asset-banner-preview');
        if (ap) { ap.src = e.target.result; ap.removeAttribute('hidden'); }
        // Tick and lock the Banner toggle
        if (pvBanner) { pvBanner.checked = true; pvBanner.disabled = true; }
        // Set frosted background on the local frost wrapper (match upload page behavior)
        if (frostWrap) {
          frostWrap.style.setProperty('--bg-image', `url('${e.target.result}')`);
          frostWrap.style.setProperty('--bg-size', 'contain');
          frostWrap.style.setProperty('--bg-position', 'center top');
          frostWrap.style.setProperty('--bg-blur', '14px');
        }
        updatePreview();
      };
      reader.readAsDataURL(file);
      // Also attempt to upload immediately to server via AJAX
      try {
        const meta = document.getElementById('event-meta');
        const eid = meta ? meta.getAttribute('data-event-id') : null;
        if (eid) {
          const fd = new FormData();
          fd.append('file', file);
          fetch(`/events/${eid}/banner`, { method: 'POST', body: fd, credentials: 'same-origin' })
            .then(r => r.json())
            .then(j => {
              if (j && j.ok && j.path) {
                const p = j.path + '?v=' + Date.now();
                const ap = document.getElementById('asset-banner-preview'); if (ap) { ap.src = p; ap.removeAttribute('hidden'); }
                const img = document.getElementById('pv-cover-img'); if (img) { img.src = p; img.removeAttribute('hidden'); }
                if (frostWrap) { frostWrap.style.setProperty('--bg-image', `url(${p})`); frostWrap.style.setProperty('--bg-size', 'contain'); frostWrap.style.setProperty('--bg-position', 'center top'); frostWrap.style.setProperty('--bg-blur', '14px'); }
              } else {
                if (window.snackbar && window.snackbar.show){ window.snackbar.show(j && j.error ? j.error : 'Upload failed'); }
              }
            })
            .catch(()=>{/*silent*/});
        }
      } catch(e) { /*ignore*/ }
    });
  }
  if (removeBannerBtn){
    removeBannerBtn.addEventListener('click', function(){
      if (removeBannerHidden) removeBannerHidden.value = '1';
      if (pvBanner){ pvBanner.checked = false; pvBanner.disabled = false; }
      if (coverWrap){ coverWrap.style.display = 'none'; const im=document.getElementById('pv-cover-img'); if (im){ im.removeAttribute('src'); im.setAttribute('hidden',''); } }
  if (frostWrap){ frostWrap.style.removeProperty('--bg-image'); frostWrap.style.removeProperty('--bg-size'); frostWrap.style.removeProperty('--bg-position'); frostWrap.style.removeProperty('--bg-blur'); }
      const ap = document.getElementById('asset-banner-preview'); if (ap){ ap.setAttribute('hidden',''); ap.removeAttribute('src'); }
      const nameEl = document.getElementById('banner_file_name'); if (nameEl){ nameEl.textContent = 'No file chosen'; }
      if (banner){ try{ banner.value = ''; }catch(e){} }
      updatePreview();
    });
  }
  // Initial state
  if (isThemeSelected()) {
    // Only toggle visibility/disable state; do NOT override the server-rendered
    // button_style value. The page already rendered with the saved effective style.
    // Calling applyThemeFromSelect() here would clobber the user's saved gradient
    // back to the theme default before they even interact.
    toggleCustomizer();
    var _initData = getSelectedThemeData();
    if (meta && _initData) {
      if (swatch) {
        swatch.style.background = 'linear-gradient(90deg, ' + (_initData.b1 || '#ccc') + ' 0%, ' + (_initData.b2 || '#ccc') + ' 100%)';
        swatch.style.boxShadow = 'inset 0 0 0 4px ' + (_initData.bg || '#ffffff');
      }
      if (desc) { desc.textContent = _initData.desc || ''; }
    }
  } else {
    toggleCustomizer();
  }
  // Initialize radio button states to match the page-loaded button style value
  if (buttonStyle && (bsSolidRadio || bsGradRadio)) {
    const loadedStyle = (buttonStyle.value || 'gradient').toLowerCase().trim();
    if (loadedStyle === 'solid') {
      if (bsSolidRadio) bsSolidRadio.checked = true;
      if (bsGradRadio) bsGradRadio.checked = false;
    } else {
      if (bsSolidRadio) bsSolidRadio.checked = false;
      if (bsGradRadio) bsGradRadio.checked = true;
    }
  }
  updatePreview();

  // On submit, make a final sync of visible editor values into hidden fields (Custom mode only)
  const form = document.getElementById('event-edit-form');
  if (form) {
    form.addEventListener('submit', function(){
      // Sync button_style hidden field from radio state
      var bsHidden = document.getElementById('button_style');
      if (bsHidden) {
        bsHidden.value = (bsSolidRadio && bsSolidRadio.checked) ? 'solid' : 'gradient';
      }
      // In custom mode, sync visible editor values into hidden fields before POST
      if (!isThemeSelected()) {
        const getVal = function(id, fallback){ const el = document.getElementById(id); return (el && el.value) || fallback || ''; };
        const payload = {
          primary_color: getVal('ButtonColour1', primary && primary.value),
          secondary_color: getVal('ButtonColour2', secondary && secondary.value),
          text_color: getVal('TextColour', textColor && textColor.value),
          background_color: getVal('BackgroundColour', bg && bg.value),
          accent_color: getVal('AccentColour', accent && accent.value),
          font_family: (ffSelectEl && ffSelectEl.value) || (fontSelect && fontSelect.value) || '',
          input_background_color: getVal('InputBackgroundColour', ''),
          dropzone_background_color: getVal('DropzoneBackgroundColour', '')
        };
        Object.keys(payload).forEach(function(k){
          const el = document.getElementById(k);
          if (el) { el.disabled = false; el.value = payload[k]; }
        });
      }
    });
  }

  // Button style type toggle (clickable types)
  function setType(val){
    if (!buttonStyle) return;
    buttonStyle.value = val;
    // Update radio button states to match the selected style
    if (bsSolidRadio) bsSolidRadio.checked = (val === 'solid');
    if (bsGradRadio) bsGradRadio.checked = (val === 'gradient');
  if (gradientControls) gradientControls.style.display = (val === 'solid') ? 'none' : 'grid';
    updatePreview();
  }
  // Attach listeners to radio buttons so changes trigger setType
  if (bsSolidRadio) bsSolidRadio.addEventListener('change', function(){ if (this.checked) setType('solid'); });
  if (bsGradRadio) bsGradRadio.addEventListener('change', function(){ if (this.checked) setType('gradient'); });

  // Per-card resets
  if (resetCardButton){
    resetCardButton.addEventListener('click', function(e){
      e.preventDefault();
      if (primary) primary.value = '#F25F4C';
      if (secondary) secondary.value = '#FF8906';
      if (buttonStyle) buttonStyle.value = 'gradient';
      if (typeGrad) typeGrad.setAttribute('aria-pressed', 'true');
      if (typeSolid) typeSolid.setAttribute('aria-pressed', 'false');
      updatePreview();
    });
  }
  if (resetCardColors){
    resetCardColors.addEventListener('click', function(e){
      e.preventDefault();
      if (textColor) textColor.value = '#0F0E17';
      if (accent) accent.value = '#222';
      if (bg) bg.value = '#ffffff';
      updatePreview();
    });
  }
  if (resetCardTypography){
    resetCardTypography.addEventListener('click', function(e){
      e.preventDefault();
      if (fontSelect) fontSelect.value = 'Inter, Arial, sans-serif';
      if (cornerRadius) cornerRadius.value = 'rounded';
      if (headingSize) headingSize.value = 'm';
      updatePreview();
    });
  }

  // Admin-like Theme Editor behavior
  (function(){
    const root = pRoot; if (!root) return;
    const wrapper = root.closest('.web-preview-wrapper');
    const web = root.querySelector('.web-preview');
    function scalePreview(){
      if (!wrapper || !web) return;
      web.style.transform = 'none';
      web.style.width = '100%';
      wrapper.style.height = 'auto';
    }
    window.addEventListener('resize', scalePreview);
    setTimeout(scalePreview, 0);

    const map = {
      BackgroundColour: '--card',
      TextColour: '--card-text',
      ButtonColour1: '--btn1',
      ButtonColour2: '--btn2',
      AccentColour: '--accent',
      InputBackgroundColour: '--input-bg',
      DropzoneBackgroundColour: '--dropzone-bg'
    };
    function apply(id){
      const el = document.getElementById(id); if (!el) return;
      let v = el.value || '';
      const hexInput = document.getElementById(id + 'Hex'); if (hexInput) { hexInput.value = (v || '').toUpperCase(); }
      const cssVar = map[id]; if (cssVar) root.style.setProperty(cssVar, v);
      updateContrast();
      updatePreview();
      scalePreview();
    }
    ['BackgroundColour','TextColour','ButtonColour1','ButtonColour2','AccentColour','InputBackgroundColour','DropzoneBackgroundColour'].forEach(function(id){
      const el=document.getElementById(id); if (el){ el.addEventListener('input', function(){ apply(id); }); }
    });
    ['BackgroundColour','TextColour','ButtonColour1','ButtonColour2','AccentColour','InputBackgroundColour','DropzoneBackgroundColour'].forEach(function(id){
      const hex = document.getElementById(id + 'Hex'); if (!hex) return;
      hex.addEventListener('input', function(){
        let v = hex.value || '';
        if (v && !v.startsWith('#') && !v.startsWith('rgb')) v = '#' + v;
        const sw = document.getElementById(id); if (sw){ sw.value = v; }
        const cssVar = map[id]; if (cssVar){ root.style.setProperty(cssVar, v); }
        updateContrast(); updatePreview();
      });
    });

    // Contrast helpers
    function hexToRgb(h){ h=(h||'').trim(); if(!h) return null; if(h[0]==='#') h=h.slice(1); if(h.length===3){ h=h.split('').map(c=>c+c).join(''); } const num=parseInt(h,16); if(isNaN(num)) return null; return {r:(num>>16)&255,g:(num>>8)&255,b:num&255}; }
    function relLum({r,g,b}){ const sr=[r,g,b].map(v=>{v/=255; return v<=0.03928? v/12.92: Math.pow((v+0.055)/1.055,2.4);}); return 0.2126*sr[0] + 0.7152*sr[1] + 0.0722*sr[2]; }
    function contrastRatio(bg, tx){ const L1=Math.max(bg,tx), L2=Math.min(bg,tx); return (L1+0.05)/(L2+0.05); }
    function updateContrast(){
  const bgEl = document.getElementById('BackgroundColour');
  const txEl = document.getElementById('TextColour');
  const bg = hexToRgb(bgEl && bgEl.value);
  const tx = hexToRgb(txEl && txEl.value);
      const ratioEl = document.getElementById('contrast-ratio'); if (!bg || !tx || !ratioEl) return;
      const r = contrastRatio(relLum(bg), relLum(tx));
      ratioEl.textContent = r.toFixed(2) + ':1';
      const aa = document.getElementById('contrast-aa'); const aaa = document.getElementById('contrast-aaa');
      if (aa){ aa.style.background = r >= 4.5 ? '#153a2b' : '#3a1514'; aa.style.borderColor = r >= 4.5 ? '#2a6a46' : '#5a1f1a'; }
      if (aaa){ aaa.style.background = r >= 7 ? '#153a2b' : '#3a1514'; aaa.style.borderColor = r >= 7 ? '#2a6a46' : '#5a1f1a'; }
    }
    updateContrast();

    // Button style radios
    const bsGrad = document.getElementById('ButtonStyleGradient');
    const bsSolid = document.getElementById('ButtonStyleSolid');
    function applyButtonStyle(){
      const isSolid = !!(bsSolid && bsSolid.checked);
      if (isSolid){ root.classList.add('is-solid'); root.classList.remove('is-gradient'); }
      else { root.classList.add('is-gradient'); root.classList.remove('is-solid'); }
      const hidden = document.getElementById('button_style'); if (hidden){ hidden.value = isSolid ? 'solid' : 'gradient'; }
      // Keep secondary color visible to avoid layout shift per request
      const b2w = document.getElementById('ButtonColour2Wrap'); if (b2w){ b2w.style.display = ''; }
  // Hide or show gradient controls immediately
  const gc = document.getElementById('gradient-controls');
  const gdw = document.getElementById('gradient-dir-wrap');
  const gstySel = document.getElementById('ButtonGradientStyle');
  if (gc) gc.style.display = isSolid ? 'none' : 'grid';
  if (gdw) gdw.style.display = (isSolid || (gstySel && gstySel.value === 'radial')) ? 'none' : 'block';
    }
    if (bsGrad) bsGrad.addEventListener('change', function(){ applyButtonStyle(); updatePreview(); });
    if (bsSolid) bsSolid.addEventListener('change', function(){ applyButtonStyle(); updatePreview(); });
    applyButtonStyle();

    // Preview toggles
    function applyToggles(){
      if (coverWrap && pvBanner){ coverWrap.style.display = pvBanner.checked ? '' : 'none'; }
      const prog = document.getElementById('progress-container'); if (prog && pvProgress){ prog.style.display = pvProgress.checked ? '' : 'none'; }
      // The preview uses `your-uploads-section` in the DOM; ensure we target that element
      const uploadsWrap = document.getElementById('your-uploads-section') || document.getElementById('pv-uploads-wrap');
      if (uploadsWrap && pvUploads){ uploadsWrap.style.display = pvUploads.checked ? '' : 'none'; }
      // Guestbook message input is always visible now
      scalePreview();
    }
    [pvBanner, pvProgress, pvUploads].forEach(function(x){ if (x) x.addEventListener('change', applyToggles); });
    // If a banner already exists, enforce it on load: tick and lock, show cover, set background
    (function(){
  var initialBannerEl = document.getElementById('initial-banner');
  var initialBanner = initialBannerEl ? (initialBannerEl.getAttribute('data-url') || '') : '';
      if (initialBanner) {
        if (pvBanner) { pvBanner.checked = true; pvBanner.disabled = true; }
        if (coverWrap) { coverWrap.style.display = ''; }
        if (pRoot) {
          if (frostWrap) {
            frostWrap.style.setProperty('--bg-image', `url(${initialBanner})`);
            frostWrap.style.setProperty('--bg-size', 'contain');
            frostWrap.style.setProperty('--bg-position', 'center top');
            frostWrap.style.setProperty('--bg-blur', '14px');
          }
        }
      }
      applyToggles();
    })();

    // Font family selector binds to hidden field
    const ffSel = document.getElementById('FontFamilySelect');
    if (ffSel){ ffSel.addEventListener('change', function(){ const h=document.getElementById('font_family'); if (h){ h.value = ffSel.value; } updatePreview(); }); }

    // Preview upload simulation: animate the progress bar and reflect theme colors
    (function(){
      const previewUploadBtn = document.querySelector('#preview-root .upload-actions .btn.primary');
  const progressContainer = document.getElementById('progress-container');
  const progressFill = progressContainer ? progressContainer.querySelector('.progress-fill') : null;
  const progressPercent = document.getElementById('progress-percent');
      let timer = null;

      function resetProgressBar(){
        if (!progressContainer || !progressFill) return;
        progressFill.style.width = '0%';
        if (progressPercent) progressPercent.textContent = '0%';
      }

      function stopUpload(){
        if (timer) { clearInterval(timer); timer = null; }
        resetProgressBar();
      }

      function startUpload(){
        if (!progressContainer || !progressFill) return;
        // Show progress via existing toggle and reset bar
        if (pvProgress) pvProgress.checked = true;
        resetProgressBar();
        applyToggles();
        let pct = 0;
        if (timer) { clearInterval(timer); timer = null; }
        timer = setInterval(function(){
          pct += Math.random()*12 + 6; // step forward
          if (pct >= 100){
            pct = 100;
            progressFill.style.width = '100%';
            if (progressPercent) progressPercent.textContent = '100%';
            clearInterval(timer); timer = null;
            // Show complete state and reveal uploads; leave the progress toggle checked
            setTimeout(function(){
              // Keep pvProgress checked so the progress container stays visible until the user unticks it
              if (pvUploads) pvUploads.checked = true;
              // Leave the progress bar at 100% so the completed state remains visible
              applyToggles();
            }, 600);
          } else {
            progressFill.style.width = Math.floor(pct) + '%';
            if (progressPercent) progressPercent.textContent = String(Math.floor(pct)) + '%';
          }
        }, 180);
      }

      if (previewUploadBtn){
        previewUploadBtn.addEventListener('click', function(e){ e.preventDefault(); startUpload(); });
      }
      // Start/stop animation when the "Uploading" toggle is changed
      if (pvProgress){
        pvProgress.addEventListener('change', function(){
          if (pvProgress.checked) { startUpload(); }
          else { stopUpload(); applyToggles(); }
        });
        // If already checked on load, animate
        if (pvProgress.checked) { startUpload(); }
      }
      // Optional: clicking the dropzone suggests files are selected
      const dropzone = document.getElementById('dropzone');
      const fileCount = document.getElementById('file-count');
      if (dropzone && fileCount){
        dropzone.addEventListener('click', function(){ fileCount.textContent = '3 files selected'; });
      }
    })();
  })();
});

document.addEventListener('DOMContentLoaded', function(){
  var img = document.getElementById('qr-img');
  var theme = null; // removed theme selector
  var logo = null; // removed logo toggle
  var fg = document.getElementById('qr-fg');
  var bg = document.getElementById('qr-bg');
  var fgHex = document.getElementById('qr-fg-hex');
  var bgHex = document.getElementById('qr-bg-hex');
  var ecc = null; // ECC removed
  var dl = null; // Download removed
  var logoFile = null; // removed logo upload
  var customLogo = null;
  if (!img) return;
  function buildParams(){
    var base = (img.getAttribute('data-guest-url') || '');
    var p = new URLSearchParams();
    p.set('url', base);
    // default to classic style; allow overriding fg/bg
    p.set('theme', 'classic');
  if (fg) p.set('fg', fg.value||'#000000');
  if (bg) p.set('bg', bg.value||'#ffffff');
    // Include or remove website logo depending on ultimate-only control
    var logoEl = document.getElementById('qr-remove-logo');
    if (logoEl) {
      p.set('logo', logoEl.checked ? '0' : '1');
    } else {
      p.set('logo', '1');
    }
    return p;
  }
  function update(){
    var url = new URL('/qr', window.location.origin);
    url.search = '?' + buildParams().toString();
    img.setAttribute('src', url.pathname + url.search);
  }
  // removed theme and logo listeners
  if (fg) fg.addEventListener('change', update);
  if (bg) bg.addEventListener('change', update);
  // ECC selector and Download button removed

  // Sync hex <-> swatch for QR colors
  function normHex(v){
    if (!v) return '';
    v = v.trim();
    if (!v) return '';
    if (v.startsWith('rgb')) return v; // ignore rgb/rgba entries
    if (!v.startsWith('#')) v = '#' + v;
    return v.toUpperCase();
  }
  function syncFromSwatch(id){
    var sw = document.getElementById(id);
    var hx = document.getElementById(id + '-hex');
    if (!sw || !hx) return;
    hx.value = (sw.value || '').toUpperCase();
  }
  function syncFromHex(id){
    var sw = document.getElementById(id);
    var hx = document.getElementById(id + '-hex');
    if (!sw || !hx) return;
    var v = normHex(hx.value || '');
    hx.value = v;
    if (v) { sw.value = v; }
  }
  if (fg && fgHex){
    fg.addEventListener('input', function(){ syncFromSwatch('qr-fg'); update(); syncHidden('qr-fg'); });
    fgHex.addEventListener('input', function(){ syncFromHex('qr-fg'); update(); syncHidden('qr-fg'); });
    syncFromSwatch('qr-fg');
    // initialize hidden input
    if (document.getElementById('qr-fill-input')) document.getElementById('qr-fill-input').value = (fg.value || '#000000').toUpperCase();
  }
  if (bg && bgHex){
    bg.addEventListener('input', function(){ syncFromSwatch('qr-bg'); update(); syncHidden('qr-bg'); });
    bgHex.addEventListener('input', function(){ syncFromHex('qr-bg'); update(); syncHidden('qr-bg'); });
    syncFromSwatch('qr-bg');
    // initialize hidden input
    if (document.getElementById('qr-back-input')) document.getElementById('qr-back-input').value = (bg.value || '#ffffff').toUpperCase();
  }
  // Keep hidden inputs in sync with visible controls
  function syncHidden(id){
    try{
      if (id === 'qr-fg'){
        var v = (document.getElementById('qr-fg').value || '').toUpperCase();
        var h = document.getElementById('qr-fill-input');
        if (h) h.value = v;
      }
      if (id === 'qr-bg'){
        var v2 = (document.getElementById('qr-bg').value || '').toUpperCase();
        var h2 = document.getElementById('qr-back-input');
        if (h2) h2.value = v2;
      }
    }catch(e){/* fail silently */}
  }
  // Wire ultimate-only logo toggle
  var qrLogoToggle = document.getElementById('qr-remove-logo');
  var qrLogoHidden = document.getElementById('qr-remove-logo-input');
  function syncQrLogoHidden(){
    try{
      if (!qrLogoHidden || !qrLogoToggle) return;
      // Hidden stores '1' when remove flag is true to match server expectations
      qrLogoHidden.value = qrLogoToggle.checked ? '1' : '0';
    }catch(e){}
  }
  if (qrLogoToggle) {
    qrLogoToggle.addEventListener('change', function(){ syncQrLogoHidden(); update(); });
    // initialize hidden state on load
    syncQrLogoHidden();
  }
  // Ensure hidden input is correct on submit regardless of theme/custom mode
  var outerForm = document.getElementById('event-edit-form');
  if (outerForm){ outerForm.addEventListener('submit', function(){ syncQrLogoHidden(); }, true); }
  // logo upload removed
  // Removed login link input as it's not editable
});
