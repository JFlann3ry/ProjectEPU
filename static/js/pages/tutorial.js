// Show best-available media; fall back to a placeholder if files are missing
(function(){
  try {
    var figures = document.querySelectorAll('.media');
    figures.forEach(function(fig){
      var ph = fig.querySelector('.placeholder');
      var vid = fig.querySelector('video');
      var img = fig.querySelector('img');
      var anyShown = false;
      function show(el){ if (el) { el.style.display = 'block'; anyShown = true; if (ph) ph.style.display = 'none'; } }
      function hide(el){ if (el) el.style.display = 'none'; }
      // Initialize hidden; reveal when loaded
      if (vid) {
        hide(vid);
        vid.addEventListener('loadedmetadata', function(){
          try { vid.currentTime = 0.01; } catch(e){}
        }, { once: true });
        vid.addEventListener('loadeddata', function(){ show(vid); try { vid.muted = true; vid.play().catch(function(){}); } catch(e){} }, { once: true });
        vid.addEventListener('error', function(){ hide(vid); if (!anyShown && img && img.complete && img.naturalWidth > 0) { show(img); } });
      }
      if (img) {
        hide(img);
        if (img.complete) { if (img.naturalWidth > 0) show(img); }
        img.addEventListener('load', function(){ show(img); }, { once: true });
        img.addEventListener('error', function(){ hide(img); if (!anyShown && vid && vid.readyState >= 2) { show(vid); } });
      }
      // If neither loads within ~1.2s, keep placeholder
      setTimeout(function(){ if (!anyShown && ph) ph.style.display = 'block'; }, 1200);
    });
  } catch(e){}
})();
