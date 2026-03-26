(function(){
  const demoModalBtn = document.getElementById('demo-modal');
  if (demoModalBtn) {
    demoModalBtn.addEventListener('click', function(){
      const body = `
        <div class="modal-section">
          <p class="muted">This is the standard modal style with a top-right close (×). No footer Close button is added by default on showcases.</p>
          <form class="form">
            <div class="floating-field">
              <label for="m-email" class="fl-label">Email</label>
              <input class="input-field" type="email" id="m-email" placeholder="you@example.com" />
            </div>
            <div class="btn-row">
              <button class="btn primary" type="button">Action</button>
            </div>
          </form>
        </div>
      `;
      if (window.EPU && window.EPU.modal && typeof window.EPU.modal.show === 'function') {
        window.EPU.modal.show({ title: 'Demo Modal', body, wide: false, fit: true, actions: [], noDefaultClose: true });
      }
    });
  }
})();
