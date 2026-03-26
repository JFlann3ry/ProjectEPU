(function () {
    const namespace = (window.EPU = window.EPU || {});

    function initModal() {
        const root = document.getElementById('modal-root');
        const titleEl = document.getElementById('modal-title');
        const bodyEl = document.getElementById('modal-body');
        const actionsEl = root ? root.querySelector('.modal-actions') : null;
        const closeX = root ? root.querySelector('.modal-x') : null;
        if (!root || !titleEl || !bodyEl) return;

        let lastFocused = null;

        function getFocusable(container) {
            if (!container) return [];
            const selector = [
                'a[href]',
                'area[href]',
                'button:not([disabled])',
                'input:not([disabled])',
                'select:not([disabled])',
                'textarea:not([disabled])',
                '[tabindex]:not([tabindex="-1"])',
            ].join(',');
            return Array.from(container.querySelectorAll(selector)).filter((element) => {
                const hidden = element.getAttribute('aria-hidden') === 'true';
                const style = window.getComputedStyle(element);
                return !hidden && style.display !== 'none' && style.visibility !== 'hidden';
            });
        }

        function onKeydown(event) {
            if (root.style.display === 'none') return;
            if (event.key === 'Escape') {
                event.preventDefault();
                hide();
                return;
            }
            if (event.key !== 'Tab') return;
            const box = root.querySelector('.modal');
            const focusables = getFocusable(box);
            if (focusables.length === 0) {
                event.preventDefault();
                if (box) box.focus();
                return;
            }
            const first = focusables[0];
            const last = focusables[focusables.length - 1];
            const active = document.activeElement;
            if (event.shiftKey && (active === first || active === box)) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && active === last) {
                event.preventDefault();
                first.focus();
            }
        }

        function hide() {
            const box = root.querySelector('.modal');
            if (box) {
                box.removeAttribute('data-wide');
                box.removeAttribute('data-fit');
            }
            root.style.display = 'none';
            root.setAttribute('aria-hidden', 'true');
            bodyEl.innerHTML = '';
            titleEl.textContent = '';
            if (actionsEl) actionsEl.innerHTML = '';
            document.removeEventListener('keydown', onKeydown, true);
            if (lastFocused && document.contains(lastFocused) && typeof lastFocused.focus === 'function') {
                lastFocused.focus();
            }
            lastFocused = null;
        }

        function show(opts) {
            const { title, body, actions, wide, fit, noDefaultClose, raw } = opts || {};
            titleEl.textContent = title || '';
            bodyEl.innerHTML = raw ? body || '' : `<div class="modal-inner-text">${body || ''}</div>`;
            const box = root.querySelector('.modal');
            if (box) {
                box.setAttribute('data-wide', wide ? 'true' : 'false');
                box.setAttribute('data-fit', fit ? 'true' : 'false');
            }
            if (actionsEl) {
                actionsEl.innerHTML = '';
                if (Array.isArray(actions)) {
                    actions.forEach((action) => {
                        const button = document.createElement('button');
                        button.className = action.danger ? 'btn danger' : 'btn';
                        button.textContent = action.label || 'OK';
                        button.type = 'button';
                        button.addEventListener('click', () => {
                            if (action.onClick) action.onClick(hide);
                            else if (action.role === 'cancel') hide();
                        });
                        actionsEl.appendChild(button);
                    });
                    const cancelExists = actions.some((action) => action.role === 'cancel');
                    if (!cancelExists && !noDefaultClose) {
                        const closeButton = document.createElement('button');
                        closeButton.className = 'btn';
                        closeButton.type = 'button';
                        closeButton.textContent = 'Close';
                        closeButton.addEventListener('click', hide);
                        actionsEl.appendChild(closeButton);
                    }
                }
            }
            lastFocused = document.activeElement;
            root.style.display = 'flex';
            root.setAttribute('aria-hidden', 'false');
            document.addEventListener('keydown', onKeydown, true);
            const box = root.querySelector('.modal');
            const focusables = getFocusable(box);
            if (focusables.length > 0) {
                focusables[0].focus();
            } else if (box && typeof box.focus === 'function') {
                box.setAttribute('tabindex', '-1');
                box.focus();
            }
        }

        if (!root.dataset.overlayBound) {
            root.addEventListener('click', (event) => {
                if (event.target === root) hide();
            });
            root.dataset.overlayBound = '1';
        }
        if (closeX && !closeX.dataset.bound) {
            closeX.addEventListener('click', hide);
            closeX.dataset.bound = '1';
        }

        namespace.modal = { show, hide };
    }

    function initSnackbar() {
        const element = document.getElementById('snackbar');
        const text = element ? element.querySelector('.snack-text') : null;
        const action = element ? element.querySelector('.snack-action') : null;
        let hideTimer = null;

        function hide() {
            if (!element) return;
            element.style.display = 'none';
            if (hideTimer) {
                clearTimeout(hideTimer);
                hideTimer = null;
            }
            if (action) {
                action.onclick = null;
                action.style.display = '';
            }
        }

        function show(message, opts) {
            if (!element || !text) return;
            const { duration = 4000, onAction, actionText = 'Undo', hideAction = true } = opts || {};
            text.textContent = message || '';
            if (action) {
                if (hideAction) {
                    action.style.display = 'none';
                    action.onclick = null;
                } else {
                    action.style.display = '';
                    action.textContent = actionText;
                    action.onclick = function () {
                        if (onAction) onAction();
                        hide();
                    };
                }
            }
            element.style.display = 'block';
            if (hideTimer) clearTimeout(hideTimer);
            hideTimer = setTimeout(hide, duration);
        }

        namespace.snackbar = { show, hide };
    }

    function initMobileNav() {
        const button = document.querySelector('.menu-toggle');
        const nav = document.getElementById('site-nav');
        if (!button || !nav) return;

        function setOpen(open) {
            button.setAttribute('aria-expanded', open ? 'true' : 'false');
            nav.classList.toggle('open', !!open);
        }

        button.addEventListener('click', () => {
            setOpen(button.getAttribute('aria-expanded') !== 'true');
        });
        document.addEventListener('click', (event) => {
            if (!nav.classList.contains('open')) return;
            const inside = event.target === button || button.contains(event.target) || event.target === nav || nav.contains(event.target);
            if (!inside) setOpen(false);
        });
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') setOpen(false);
        });
        nav.addEventListener('click', (event) => {
            const link = event.target.closest('a');
            if (link && link.getAttribute('href')) setOpen(false);
        });
    }

    function initAvatarDropdown() {
        const menu = document.getElementById('user-menu');
        const button = document.getElementById('avatar-btn');
        const dropdown = document.getElementById('user-dropdown');
        if (!menu || !button || !dropdown) return;

        function open(on) {
            menu.open = !!on;
            button.setAttribute('aria-expanded', on ? 'true' : 'false');
            dropdown.classList.toggle('open', !!on);
        }

        button.addEventListener('click', () => {
            window.setTimeout(() => {
                const isOpen = !!menu.open;
                button.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
                dropdown.classList.toggle('open', isOpen);
            }, 0);
        });
        document.addEventListener('click', (event) => {
            if (event.target === button || button.contains(event.target) || dropdown.contains(event.target) || menu.contains(event.target)) return;
            open(false);
        });
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') open(false);
        });
        dropdown.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                open(false);
                button.focus();
            }
        });
    }

    function initTooltips() {
        function toggleTip(tip, expand) {
            if (!tip) return;
            const on = expand === undefined ? tip.getAttribute('aria-expanded') !== 'true' : !!expand;
            tip.setAttribute('aria-expanded', on ? 'true' : 'false');
        }

        document.addEventListener('click', (event) => {
            const tip = event.target.closest('.tip');
            if (tip) {
                event.preventDefault();
                toggleTip(tip);
            } else {
                document.querySelectorAll('.tip[aria-expanded="true"]').forEach((element) => {
                    element.setAttribute('aria-expanded', 'false');
                });
            }
        });
        document.addEventListener('keydown', (event) => {
            const tip = event.target.closest('.tip');
            if (!tip) return;
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                toggleTip(tip);
            }
            if (event.key === 'Escape') {
                toggleTip(tip, false);
                tip.blur();
            }
        });
        document.addEventListener('focusout', (event) => {
            const tip = event.target.closest('.tip');
            if (tip && !tip.contains(event.relatedTarget)) toggleTip(tip, false);
        });
    }

    function escapeHtml(value) {
        return (value || '').replace(/[&<>"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[char] || char));
    }

    function initShareModal() {
        async function openShareModal(opts) {
            if (!namespace.modal) return;
            const { code, title = '', tmpl = null, eid = null } = opts || {};
            const url = new URL(`/e/${code || ''}`, window.location.origin).href;
            const defaultTitle = title || 'My event';
            const rawTemplate = tmpl || `${defaultTitle} — %URL%`;
            const initial = rawTemplate.replace(/%TITLE%/g, defaultTitle).replace(/%URL%/g, url);
            const template = document.getElementById('share-modal-template');
            if (!template) return;

            namespace.modal.show({
                title: 'Share Event',
                body: template.innerHTML,
                fit: true,
                actions: [],
                noDefaultClose: true,
                raw: true,
            });

            setTimeout(() => {
                const textarea = document.getElementById('share-message');
                const urlText = document.getElementById('share-url-text');
                if (textarea) textarea.value = initial;
                if (urlText) urlText.textContent = url;

                const encoded = (value) => encodeURIComponent(value || '');
                const whatsapp = document.getElementById('share-wa');
                const messenger = document.getElementById('share-messenger');
                const email = document.getElementById('share-email');
                const copy = document.getElementById('share-copy');
                const smsButton = document.getElementById('share-sms');

                function getMessage() {
                    return textarea ? textarea.value : initial;
                }

                function notifyShared() {
                    try {
                        document.dispatchEvent(new CustomEvent('epu:shared', { detail: { eid } }));
                    } catch (_error) {
                        // Ignore CustomEvent issues.
                    }
                }

                const isMobile = (() => {
                    try {
                        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
                    } catch (_error) {
                        return false;
                    }
                })();

                if (smsButton) {
                    if (isMobile) smsButton.style.display = '';
                    else smsButton.remove();
                }

                if (whatsapp) {
                    whatsapp.onclick = () => {
                        window.open(`https://wa.me/?text=${encoded(getMessage())}`, '_blank');
                        notifyShared();
                    };
                }

                if (messenger) {
                    messenger.onclick = () => {
                        const message = getMessage();
                        const encodedUrl = encoded(url);
                        try {
                            window.open(`fb-messenger://share/?link=${encodedUrl}`, '_blank');
                            notifyShared();
                            return;
                        } catch (_error) {
                            // Fall back below.
                        }
                        if (navigator.share) {
                            navigator
                                .share({ title: defaultTitle, text: message, url })
                                .then(() => notifyShared())
                                .catch(() => window.open(`https://www.messenger.com/t/?link=${encodedUrl}`, '_blank'));
                        } else {
                            window.open(`https://www.messenger.com/t/?link=${encodedUrl}`, '_blank');
                        }
                    };
                }

                if (email) {
                    if (isMobile) {
                        email.onclick = () => {
                            const subject = defaultTitle;
                            const body = encodeURIComponent((getMessage() || '').replace(/\r?\n/g, '\r\n'));
                            window.location.href = `mailto:?subject=${encoded(subject)}&body=${body}`;
                            notifyShared();
                        };
                    } else {
                        email.remove();
                    }
                }

                if (smsButton) {
                    smsButton.onclick = () => {
                        const smsBody = encodeURIComponent(`${getMessage()}\n\n${url}`);
                        try {
                            window.location.href = `sms:?&body=${smsBody}`;
                            notifyShared();
                        } catch (_error) {
                            if (namespace.snackbar) namespace.snackbar.show('SMS not available');
                        }
                    };
                }

                if (copy) {
                    copy.onclick = () => {
                        const value = `${getMessage()}\r\n\r\n${url}`;
                        if (navigator.clipboard && navigator.clipboard.writeText) {
                            navigator.clipboard.writeText(value).then(() => {
                                if (namespace.snackbar) namespace.snackbar.show('Message + link copied');
                                notifyShared();
                            });
                        } else if (namespace.snackbar) {
                            namespace.snackbar.show('Copy not supported');
                        }
                    };
                }
            }, 30);
        }

        document.addEventListener(
            'click',
            (event) => {
                const button = event.target.closest && event.target.closest('.share-btn');
                if (!button) return;
                event.preventDefault();
                openShareModal({
                    code: button.getAttribute('data-code'),
                    published: button.getAttribute('data-published') === '1',
                    title: button.getAttribute('data-title') || '',
                    tmpl: button.getAttribute('data-share-template') || null,
                });
            },
            true
        );

        namespace.share = { open: openShareModal };
    }

    function initCookieFallback() {
        const footerLink = document.getElementById('footer-cookie-settings');
        if (!footerLink || footerLink.dataset.cookieBound) return;
        footerLink.addEventListener('click', (event) => {
            event.preventDefault();
            const button = document.getElementById('cookie-settings');
            if (button) {
                button.click();
            } else if (namespace.modal) {
                namespace.modal.show({
                    title: 'Cookie settings',
                    body: '<p>Cookie settings are not available.</p>',
                });
            }
        });
        footerLink.dataset.cookieBound = '1';
    }

    function boot() {
        initModal();
        initSnackbar();
        initMobileNav();
        initAvatarDropdown();
        initTooltips();
        initShareModal();
        initCookieFallback();
        if (namespace.shareButton && namespace.shareButton.upgradeAll) {
            namespace.shareButton.upgradeAll();
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();
