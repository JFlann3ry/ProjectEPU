/* Billing purchase page interactions: retry checkout and email receipt */
(function(){
  function onClick(e){
    const btn = e.target.closest('[data-action]');
    if(!btn) return;
    const action = btn.getAttribute('data-action');
    if(action === 'retry-checkout'){
      e.preventDefault();
      retryCheckout(btn);
    } else if(action === 'email-receipt'){
      e.preventDefault();
      emailReceipt(btn);
    }
  }

  async function retryCheckout(btn){
    const purchaseId = btn.getAttribute('data-purchase-id');
    const pk = btn.getAttribute('data-stripe-pk');
    if(!purchaseId || !pk){ return; }
    // eslint-disable-next-line no-undef
    const stripe = Stripe(pk);
    async function go(id){
      const { error } = await stripe.redirectToCheckout({ sessionId: id });
      if (error) { console.warn('Stripe redirect error', error); throw error; }
    }
    try {
      btn.disabled = true;
      const res = await fetch(`/billing/purchase/${purchaseId}/restart-checkout`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
      if (!res.ok) throw new Error('Failed to create checkout session');
      const data = await res.json();
      const sessionId = data && data.id;
      if (!sessionId) throw new Error('No session id');
      await go(sessionId);
    } catch (e) {
      console.error('Unable to start checkout', e);
      alert('Sorry, we could not start checkout. Please try again.');
    } finally {
      btn.disabled = false;
    }
  }

  async function emailReceipt(btn){
    const purchaseId = btn.getAttribute('data-purchase-id');
    if(!purchaseId){ return; }
    try {
      btn.disabled = true;
      const res = await fetch(`/billing/purchase/${purchaseId}/email-receipt`, { method: 'POST' });
      if (res.ok) {
        window.location.href = `/billing/purchase/${purchaseId}?sent=1`;
      } else {
        if (res.status === 429) {
          alert('You can request this receipt once per hour. Please try again later.');
        } else {
          alert('Unable to send receipt email.');
        }
      }
    } catch (e) {
      console.error('Email receipt failed', e);
      alert('Unable to send receipt email.');
    } finally {
      btn.disabled = false;
    }
  }

  document.addEventListener('click', onClick);
})();
