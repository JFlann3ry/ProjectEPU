(function () {
    const KEY = 'epu_cookie_consent_v1';
    const ns = (window.EPU = window.EPU || {});

    function readConsent() {
        try {
            const raw = localStorage.getItem(KEY);
            if (!raw) return null;
            return JSON.parse(raw);
        } catch (_error) {
            return null;
        }
    }

    function hasAnalyticsConsent() {
        const consent = readConsent();
        return !!(consent && consent.analytics === true);
    }

    function send(eventName, payload) {
        if (!eventName || !hasAnalyticsConsent()) return false;
        try {
            const params = new URLSearchParams();
            params.set('e', String(eventName));
            params.set('path', String((payload && payload.path) || window.location.pathname || ''));
            params.set('source', String((payload && payload.source) || 'web'));
            if (payload && payload.meta) params.set('meta', String(payload.meta));
            fetch('/analytics/collect?' + params.toString(), {
                method: 'GET',
                credentials: 'same-origin',
                cache: 'no-store',
                keepalive: true,
            }).catch(function () {
                // Best effort only.
            });
            return true;
        } catch (_error) {
            return false;
        }
    }

    function track(eventName, payload) {
        return send(eventName, payload || {});
    }

    function bindFunnels() {
        document.addEventListener('click', function (event) {
            const signupLink = event.target.closest('a[href="/login"]');
            if (signupLink) track('signup_start', { source: 'nav' });

            const createLink = event.target.closest('a[href="/events/create"]');
            if (createLink) track('event_create_start', { source: 'nav' });
        });

        document.addEventListener('submit', function (event) {
            const form = event.target;
            if (!(form && form.getAttribute)) return;
            const action = String(form.getAttribute('action') || '');
            if (action.indexOf('/events/create') !== -1) {
                track('event_create_submit', { source: 'form' });
            }
        });

        document.addEventListener('epu:checkout-start', function (event) {
            const detail = (event && event.detail) || {};
            track('checkout_start', {
                source: String(detail.source || 'web'),
                meta: String(detail.plan || detail.code || ''),
            });
        });

        document.addEventListener('epu:checkout-success', function (event) {
            const detail = (event && event.detail) || {};
            track('checkout_success', {
                source: String(detail.source || 'web'),
                meta: String(detail.purchase_id || ''),
            });
        });

        document.addEventListener('epu:consent-updated', function () {
            if (hasAnalyticsConsent()) {
                track('consent_update', { source: 'cookie_settings' });
            }
        });
    }

    function boot() {
        ns.analytics = { track: track, hasConsent: hasAnalyticsConsent };
        track('landing', { source: 'page' });
        bindFunnels();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();
