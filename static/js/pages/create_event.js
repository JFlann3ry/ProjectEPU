function setupEventTypeToggle() {
  const typeSelect = document.getElementById('type');
  const typeCustomWrap = document.getElementById('type_custom_wrap');
  const typeCustom = document.getElementById('type_custom');
  if (!typeSelect || !typeCustomWrap || !typeCustom) {
    return;
  }

  const sync = () => {
    const showCustom = typeSelect.value === 'Other';
    typeCustomWrap.style.display = showCustom ? '' : 'none';
    typeCustom.required = showCustom;
  };

  typeSelect.addEventListener('change', sync);
  sync();
}

function setupTermsModal() {
  const termsLink = document.getElementById('terms-link');
  const termsCheckbox = document.getElementById('terms');
  if (!termsLink) {
    return;
  }

  async function openSharedModal() {
    try {
      const response = await fetch('/terms/embed', { headers: { 'X-Requested-With': 'fetch' } });
      const html = await response.text();
      const body = `<div style="height:65vh; overflow:auto; padding:12px 16px;">${html}</div>`;
      if (window.EPU && window.EPU.modal) {
        window.EPU.modal.show({
          title: 'Terms and Conditions',
          body,
          fit: true,
          actions: [
            { label: 'Cancel', role: 'cancel' },
            {
              label: 'I Agree',
              onClick(hide) {
                if (termsCheckbox) {
                  termsCheckbox.checked = true;
                }
                hide();
              },
            },
          ],
        });
      } else {
        window.open('/terms', '_blank');
      }
    } catch (_error) {
      if (window.EPU && window.EPU.modal) {
        window.EPU.modal.show({
          title: 'Terms and Conditions',
          body: '<p class="muted">Could not load terms. Please open the full page: <a href="/terms" target="_blank">/terms</a></p>',
          actions: [{ label: 'Close', role: 'cancel' }],
          fit: true,
        });
      } else {
        window.open('/terms', '_blank');
      }
    }
  }

  termsLink.addEventListener('click', (event) => {
    event.preventDefault();
    openSharedModal();
  });
}

function setupTermsGuard() {
  const form = document.querySelector('form.card.form[action="/events/create"]');
  const terms = document.getElementById('terms');
  const noticeContainer = document.getElementById('create-event-notice-container');
  const label = document.getElementById('terms-label');
  if (!form || !terms) {
    return;
  }

  form.addEventListener('submit', (event) => {
    if (terms.checked) {
      return;
    }
    event.preventDefault();
    if (noticeContainer && window.EPU && window.EPU.ui && typeof window.EPU.ui.renderNotice === 'function') {
      noticeContainer.innerHTML = window.EPU.ui.renderNotice(
        'Please accept the Terms and Conditions to continue.',
        'warn',
        'style="margin-bottom:10px;"'
      );
    } else if (window.EPU && window.EPU.snackbar) {
      window.EPU.snackbar.show('Please accept the Terms and Conditions to continue.');
    } else {
      alert('Please accept the Terms and Conditions to continue.');
    }
    if (label) {
      label.style.transition = 'outline-color .2s';
      label.style.outline = '2px solid var(--accent)';
      window.setTimeout(() => {
        label.style.outline = '';
      }, 1500);
    }
    try {
      terms.focus();
    } catch (_error) {
      // Ignore focus failures.
    }
  });

  terms.addEventListener('change', () => {
    if (terms.checked && noticeContainer) {
      noticeContainer.innerHTML = '';
    }
  });
}

function boot() {
  setupEventTypeToggle();
  setupTermsModal();
  setupTermsGuard();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot);
} else {
  boot();
}