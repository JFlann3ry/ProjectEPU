// Extras page module: handles Stripe checkout and removes inline handlers.

function parseConfig() {
  try {
    const el = document.getElementById('extras-config');
    return el ? JSON.parse(el.textContent) : {};
  } catch (_) { return {}; }
}

function getQtyFor(code) {
  const sel = document.getElementById(`qty-${code}`);
  if (!sel) return 1;
  const v = parseInt(sel.value || '1', 10);
  return Number.isFinite(v) && v > 0 ? v : 1;
}

async function startCheckout(stripe, code, quantity, event_code) {
  const res = await fetch('/extras/checkout', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, quantity, event_code })
  });
  if (res.status === 401 || res.status === 403) {
    window.location.href = '/login';
    return;
  }
  let data = null;
  try {
    data = await res.json();
  } catch (e) {
    // non-json response
  }
  if (!data || !data.id) {
    const msg = (data && data.detail) ? data.detail : `Failed to create checkout (status ${res.status})`;
    throw new Error(msg);
  }
  if (!stripe) throw new Error('Stripe not initialized');
  await stripe.redirectToCheckout({ sessionId: data.id });
}

function boot() {
  const cfg = parseConfig();
  const stripe = window.Stripe ? window.Stripe(cfg.stripe_pk || '') : null;
  document.querySelectorAll('.js-buy-extra').forEach((btn) => {
    btn.addEventListener('click', async () => {
      try {
        const code = btn.getAttribute('data-code');
        const allowQty = btn.getAttribute('data-allowqty') === '1';
        const qty = allowQty ? getQtyFor(code) : 1;
  await startCheckout(stripe, code, qty, cfg.event_code || '');
      } catch (e) {
  const msg = (e && e.message) ? e.message : 'Unable to start checkout';
  if (window.EPU?.snackbar) window.EPU.snackbar.show(msg);
  else alert(msg);
      }
    });
  });

  // Pre-select addon when ?code= is present in URL or provided via config
  try {
    const urlParams = new URLSearchParams(window.location.search);
    const pre = urlParams.get('code') || (cfg.preselect_code || '');
    if (pre) {
      const targetBtn = document.querySelector(`.js-buy-extra[data-code="${pre}"]`);
      if (targetBtn) {
        // scroll into view and add temporary highlight
        targetBtn.scrollIntoView({ behavior: 'smooth', block: 'center' });
        const card = targetBtn.closest('article.card');
        if (card) {
          card.classList.add('preselected');
          setTimeout(() => card.classList.remove('preselected'), 5000);
        }
      }
    }
  } catch (e) {
    // ignore
  }
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
