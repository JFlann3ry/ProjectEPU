function copyToClipboard(value) {
  if (!value) {
    return Promise.reject(new Error('missing value'));
  }
  return navigator.clipboard.writeText(value);
}

function boot() {
  document.querySelectorAll('.js-copy-pay-link').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const path = btn.getAttribute('data-pay-path') || '';
      const url = window.location.origin + path;
      const originalText = btn.textContent || 'Copy pay link';
      try {
        await copyToClipboard(url);
        btn.textContent = 'Link copied';
      } catch (_e) {
        btn.textContent = 'Copy failed';
      }
      setTimeout(() => {
        btn.textContent = originalText;
      }, 1500);
    });
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot);
} else {
  boot();
}
