function getMaxScrollTop() {
  return Math.max(0, (document.documentElement.scrollHeight || 0) - window.innerHeight);
}

function bootAccordion() {
  const items = document.querySelectorAll('.accordion-item');

  function toggleItem(button) {
    const item = button.closest('.accordion-item');
    const panel = item ? item.querySelector('.accordion-panel') : null;
    const expanded = button.getAttribute('aria-expanded') === 'true';
    const nextState = !expanded;
    button.setAttribute('aria-expanded', nextState ? 'true' : 'false');
    if (item) {
      item.classList.toggle('open', nextState);
    }
    if (panel) {
      panel.style.maxHeight = nextState ? `${panel.scrollHeight}px` : '0px';
    }
  }

  items.forEach((item) => {
    const button = item.querySelector('.accordion-header');
    if (!button) {
      return;
    }
    button.addEventListener('click', () => toggleItem(button));
    button.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        toggleItem(button);
      }
    });
  });
}

function bootFaqNavigation() {
  const tocCard = document.querySelector('.faq-toc-card');
  const siteHeader = document.querySelector('header.header');
  const chips = Array.from(document.querySelectorAll('.faq-toc .chip'));
  const sectionEls = Array.from(document.querySelectorAll('.faq-section'));
  const searchInput = document.getElementById('faq-search');
  const emptyState = document.querySelector('.faq-empty');
  let lockedActiveId = null;
  let ticking = false;

  function computeStickyOffset() {
    const headerHeight = siteHeader ? siteHeader.offsetHeight : 0;
    const tocHeight = tocCard ? tocCard.offsetHeight : 0;
    return headerHeight + tocHeight + 28;
  }

  function applyCssOffset() {
    document.documentElement.style.setProperty('--faq-offset', `${computeStickyOffset()}px`);
  }

  function getTargetTopFor(id) {
    const section = document.getElementById(id);
    if (!section) {
      return null;
    }
    const sectionTop = section.getBoundingClientRect().top + window.scrollY;
    return Math.max(0, sectionTop - computeStickyOffset());
  }

  function scrollToSection(id) {
    const section = document.getElementById(id);
    const target = getTargetTopFor(id);
    if (!section || target === null) {
      return;
    }
    window.scrollTo({ top: target, behavior: 'smooth' });
    if (window.history && typeof window.history.replaceState === 'function') {
      window.history.replaceState(null, '', `#${id}`);
    }
  }

  function setActive(id) {
    chips.forEach((chip) => {
      chip.classList.toggle('active', chip.getAttribute('data-target') === id);
    });
  }

  function isSectionVisible(section) {
    const card = section.querySelector('.faq-section-card');
    if (!card || card.offsetParent === null) {
      return false;
    }
    return card.getBoundingClientRect().height > 0;
  }

  function updateActiveByScroll() {
    ticking = false;
    if (!sectionEls.length) {
      return;
    }
    const doc = document.documentElement;
    const atBottom = Math.ceil(window.scrollY + window.innerHeight) >= Math.floor(doc.scrollHeight - 2);
    const visibleSections = sectionEls.filter(isSectionVisible);
    if (!visibleSections.length) {
      return;
    }
    if (atBottom && lockedActiveId) {
      setActive(lockedActiveId);
      return;
    }

    const pivot = window.scrollY + computeStickyOffset() + 1;
    let current = visibleSections[0];
    visibleSections.forEach((section) => {
      if (section.offsetTop <= pivot) {
        current = section;
      }
    });
    setActive(current.id);
    if (!atBottom) {
      lockedActiveId = null;
    }
  }

  function norm(text) {
    return (text || '').toLowerCase();
  }

  function matches(text, query) {
    const parts = norm(query).split(/\s+/).filter(Boolean);
    const normalizedText = norm(text);
    return parts.every((part) => normalizedText.indexOf(part) !== -1);
  }

  function doFilter() {
    const query = searchInput ? searchInput.value : '';
    let any = false;
    sectionEls.forEach((section) => {
      const card = section.querySelector('.faq-section-card');
      const items = section.querySelectorAll('.accordion-item');
      let anyInSection = false;
      items.forEach((item) => {
        const title = item.querySelector('.q');
        const body = item.querySelector('.a');
        const text = `${title ? title.textContent : ''} ${body ? body.textContent : ''}`;
        const ok = !query || matches(text, query);
        if (!ok) {
          item.classList.remove('open');
          const header = item.querySelector('.accordion-header');
          const panel = item.querySelector('.accordion-panel');
          if (header) {
            header.setAttribute('aria-expanded', 'false');
          }
          if (panel) {
            panel.style.maxHeight = '0px';
          }
        }
        item.style.display = ok ? '' : 'none';
        anyInSection = anyInSection || ok;
        any = any || ok;
      });
      if (card) {
        card.style.display = anyInSection ? '' : 'none';
      }
    });
    if (emptyState) {
      emptyState.hidden = any;
    }
    updateActiveByScroll();
  }

  applyCssOffset();
  window.addEventListener('resize', applyCssOffset);

  chips.forEach((chip) => {
    chip.addEventListener('click', (event) => {
      const id = chip.getAttribute('data-target');
      if (!id) {
        return;
      }
      event.preventDefault();
      setActive(id);
      const target = getTargetTopFor(id);
      const maxTop = getMaxScrollTop();
      lockedActiveId = target !== null && target >= maxTop - 1 ? id : null;
      scrollToSection(id);
    });
  });

  window.addEventListener('scroll', () => {
    if (!ticking) {
      ticking = true;
      window.requestAnimationFrame(updateActiveByScroll);
    }
  });
  window.addEventListener('resize', updateActiveByScroll);
  window.addEventListener('resize', () => {
    document.querySelectorAll('.accordion-item.open .accordion-panel').forEach((panel) => {
      panel.style.maxHeight = `${panel.scrollHeight}px`;
    });
  });

  if (searchInput) {
    searchInput.addEventListener('input', doFilter);
  }

  updateActiveByScroll();

  if (window.location.hash && window.location.hash.length > 1) {
    const targetId = window.location.hash.substring(1);
    window.setTimeout(() => {
      setActive(targetId);
      const target = getTargetTopFor(targetId);
      const maxTop = getMaxScrollTop();
      if (target !== null && target >= maxTop - 1) {
        lockedActiveId = targetId;
      }
      scrollToSection(targetId);
      updateActiveByScroll();
    }, 0);
  }
}

function boot() {
  bootAccordion();
  bootFaqNavigation();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot);
} else {
  boot();
}