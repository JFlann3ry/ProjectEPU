(function () {
    try {
        const progress = document.getElementById('scroll-progress');
        if (!progress) return;

        const supportsScrollTimeline =
            typeof CSS !== 'undefined' &&
            CSS.supports &&
            CSS.supports('animation-timeline: scroll()');
        let last = -1;

        function onScroll() {
            const y = window.scrollY || window.pageYOffset || 0;
            progress.style.opacity = y > 8 ? '1' : '0';
            if (!supportsScrollTimeline) {
                const root = document.documentElement;
                const max = root.scrollHeight - root.clientHeight || 1;
                const percent = Math.min(1, Math.max(0, y / max));
                if (percent !== last) {
                    progress.style.transform = `scaleX(${percent.toFixed(4)})`;
                    last = percent;
                }
            }
        }

        document.addEventListener('scroll', onScroll, { passive: true });
        onScroll();

        const prefersReducedMotion =
            window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        if (!prefersReducedMotion && 'IntersectionObserver' in window) {
            const observer = new IntersectionObserver(
                (entries) => {
                    entries.forEach((entry) => {
                        if (entry.isIntersecting) {
                            entry.target.classList.add('reveal-in');
                            observer.unobserve(entry.target);
                        }
                    });
                },
                { rootMargin: '0px 0px -10% 0px', threshold: 0.05 }
            );
            document.querySelectorAll('.reveal').forEach((element) => observer.observe(element));
        } else {
            document.querySelectorAll('.reveal').forEach((element) => {
                element.classList.add('reveal-in');
            });
        }
    } catch (_error) {
        // Progressive enhancement only.
    }
})();
