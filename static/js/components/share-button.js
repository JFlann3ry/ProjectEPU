// Reusable share-button component
(function(){
  const ns = window.EPU = window.EPU || {};
  function create(opts){
    // opts: { code, published, title, shareTemplate, className, attrs }
    const btn = document.createElement(opts && opts.tagName ? opts.tagName : 'button');
    btn.type = opts && opts.tagName ? btn.type : 'button';
    btn.className = (opts && opts.className) ? opts.className : 'btn share-btn';
    if (opts && opts.attrs){ Object.keys(opts.attrs).forEach(k => btn.setAttribute(k, opts.attrs[k])); }
    if (opts && opts.code !== undefined) btn.setAttribute('data-code', opts.code);
    if (opts && opts.published !== undefined) btn.setAttribute('data-published', opts.published ? '1' : '0');
    if (opts && opts.title !== undefined) btn.setAttribute('data-title', opts.title);
    if (opts && opts.shareTemplate !== undefined) btn.setAttribute('data-share-template', opts.shareTemplate);
    return btn;
  }

  function upgradeElement(el){
    if (!el) return;
    // Ensure required attributes exist; if missing, try to infer from other attributes
    if (!el.getAttribute('data-code')){
      const href = el.getAttribute('href') || '';
      const m = href.match(/\/e\/(\w+)/);
      if (m) el.setAttribute('data-code', m[1]);
    }
    if (!el.getAttribute('data-title')){
      // try text content
      const t = (el.getAttribute('data-title')||'') || (el.textContent||'').trim();
      if (t) el.setAttribute('data-title', t);
    }
    if (!el.getAttribute('data-published')){
      el.setAttribute('data-published', '0');
    }
    if (!el.getAttribute('data-share-template')){
      el.setAttribute('data-share-template', 'Join %TITLE% — %URL%');
    }
    // add role and aria if missing
    if (!el.getAttribute('role')) el.setAttribute('role', 'button');
  }

  function upgradeAll(root){
    root = root || document;
    const els = Array.from(root.querySelectorAll('.share-btn'));
    els.forEach(upgradeElement);
  }

  ns.shareButton = ns.shareButton || {};
  ns.shareButton.create = create;
  ns.shareButton.upgradeAll = upgradeAll;
})();
