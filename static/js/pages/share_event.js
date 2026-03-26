function copyShareLink() {
  const url = window.location.href;
  return navigator.clipboard.writeText(url);
}

function hexToRgb(hexValue) {
  let value = (hexValue || '').trim();
  if (!value) {
    return { r: 0, g: 0, b: 0 };
  }
  value = value.replace('#', '');
  if (value.length === 3) {
    value = value
      .split('')
      .map((c) => c + c)
      .join('');
  }
  const r = parseInt(value.substring(0, 2), 16) || 0;
  const g = parseInt(value.substring(2, 4), 16) || 0;
  const b = parseInt(value.substring(4, 6), 16) || 0;
  return { r, g, b };
}

function luminance(rgb) {
  let sr = rgb.r / 255;
  let sg = rgb.g / 255;
  let sb = rgb.b / 255;
  [sr, sg, sb] = [sr, sg, sb].map((v) =>
    v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4)
  );
  return 0.2126 * sr + 0.7152 * sg + 0.0722 * sb;
}

function applyButtonContrast() {
  const root = document.querySelector('.theme-root');
  if (!root) {
    return;
  }
  const b1 = getComputedStyle(root).getPropertyValue('--btn1');
  const lum = luminance(hexToRgb(b1));
  root.style.setProperty('--btn-text', lum > 0.55 ? '#111111' : '#ffffff');
}

function boot() {
  applyButtonContrast();

  const copyBtn = document.querySelector('.js-copy-share-link');
  if (!copyBtn) {
    return;
  }
  copyBtn.addEventListener('click', async () => {
    try {
      await copyShareLink();
      if (window.EPU && window.EPU.snackbar && typeof window.EPU.snackbar.show === 'function') {
        window.EPU.snackbar.show('Link copied');
      } else {
        alert('Link copied');
      }
    } catch (_e) {
      if (window.EPU && window.EPU.snackbar && typeof window.EPU.snackbar.show === 'function') {
        window.EPU.snackbar.show('Unable to copy link');
      } else {
        alert('Unable to copy link');
      }
    }
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot);
} else {
  boot();
}
