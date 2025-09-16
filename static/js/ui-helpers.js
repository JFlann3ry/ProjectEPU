(function(){
  function renderNotice(text, kind, attrs){
    try {
      var k = (kind && ['success','error','warn'].indexOf(String(kind)) !== -1) ? (' ' + kind) : '';
      var at = attrs ? (' ' + String(attrs).trim()) : '';
      return '<div class="notice' + k + '"' + at + '>' + (text || '') + '</div>';
    } catch(e){ return '<div class="notice">' + (text || '') + '</div>'; }
  }
  function renderBtnRow(innerHtml, attrs){
    try {
      var at = attrs ? (' ' + String(attrs).trim()) : '';
      return '<div class="btn-row"' + at + '>' + (innerHtml || '') + '</div>';
    } catch(e){ return '<div class="btn-row">' + (innerHtml || '') + '</div>'; }
  }
  window.EPU = window.EPU || {};
  window.EPU.ui = { renderNotice: renderNotice, renderBtnRow: renderBtnRow };
})();
