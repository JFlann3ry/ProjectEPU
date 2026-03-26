const EX_IMAGES = [
  'https://source.unsplash.com/1200x800/?wedding,reception,guests',
  'https://source.unsplash.com/1200x800/?corporate,event,conference',
  'https://source.unsplash.com/1200x800/?school,performance,parents',
  'https://source.unsplash.com/1200x800/?sports,team,stadium',
  'https://source.unsplash.com/1200x800/?conference,speaker,audience',
  'https://source.unsplash.com/1200x800/?community,festival,people',
];

const EX_CAPTIONS = [
  'Weddings - candid guest photos with one simple QR flow',
  'Corporate events - booth photos and session highlights in one place',
  'School plays - parent uploads with easy ZIP exports',
  'Sports - post-match highlights from players and supporters',
  'Conferences - attendee moments and sponsor activations',
  'Community - festivals, birthdays, and meetups kept together',
];

function openLightbox(index) {
  if (!window.Lightbox || typeof window.Lightbox.open !== 'function') {
    return;
  }
  const safeIndex = Number.isFinite(index) ? index : 0;
  window.Lightbox.open(safeIndex);
}

function boot() {
  if (window.Lightbox && typeof window.Lightbox.setData === 'function') {
    window.Lightbox.setData(EX_IMAGES, EX_CAPTIONS);
  }

  document.querySelectorAll('.gallery-clickable').forEach((el) => {
    el.addEventListener('click', () => {
      const idx = parseInt(el.getAttribute('data-index') || '0', 10);
      openLightbox(Number.isFinite(idx) ? idx : 0);
    });
  });

}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot);
} else {
  boot();
}
