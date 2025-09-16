// Pricing page interactions: handle plan checkout via Stripe.
function parseConfig(){
  try{ const el = document.getElementById('pricing-config'); return el ? JSON.parse(el.textContent) : {}; }catch(_){ return {}; }
}

async function startCheckout(plan){
  const res = await fetch('/create-checkout-session', {
    method: 'POST',
    credentials: 'include', // always send cookies (works for same-site and cross-site cases)
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ plan })
  });
  // If server responded with auth error, redirect to login
  if (res.status === 401 || res.status === 403) { window.location.href = '/login'; return; }
  // If the server returned HTML (likely the login page) instead of JSON, redirect to login
  const ctype = (res.headers.get('content-type') || '').toLowerCase();
  if (ctype.indexOf('application/json') === -1) {
    // If it's an HTML response and the final URL looks like login, go there; otherwise, fallback to /login
    if (res.redirected && res.url && res.url.indexOf('/login') !== -1) {
      window.location.href = res.url; return;
    }
    window.location.href = '/login';
    return;
  }
  // Parse JSON
  const data = await res.json();
  if (!data || !data.id) throw new Error('Invalid response');
  // eslint-disable-next-line no-undef
  const stripe = Stripe((parseConfig().stripe_pk) || '');
  await stripe.redirectToCheckout({ sessionId: data.id });
}

function boot(){
  document.querySelectorAll('.js-plan-continue').forEach(btn => {
    btn.addEventListener('click', async () => {
      try {
        const plan = btn.getAttribute('data-plan');
        await startCheckout(plan);
      } catch (e) {
        if (window.EPU?.snackbar) window.EPU.snackbar.show('Unable to start checkout');
      }
    });
  });
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
