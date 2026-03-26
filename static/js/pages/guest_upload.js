(function () {
    const root = document.querySelector('.theme-root');
    if (!root) return;

    const hexRaw = getComputedStyle(root).getPropertyValue('--btn1').trim();
    if (hexRaw) {
        let hex = hexRaw.replace('#', '');
        if (hex.length === 3) {
            hex = hex.split('').map((char) => char + char).join('');
        }
        const red = parseInt(hex.substring(0, 2), 16) || 0;
        const green = parseInt(hex.substring(2, 4), 16) || 0;
        const blue = parseInt(hex.substring(4, 6), 16) || 0;
        const luma = 0.2126 * red + 0.7152 * green + 0.0722 * blue;
        root.style.setProperty('--btn-text', luma > 140 ? '#111111' : '#ffffff');
    }
})();

(function () {
    const userAgent = navigator.userAgent;
    let deviceType = 'Desktop';
    if (/Mobi|Android/i.test(userAgent)) deviceType = 'Mobile';
    else if (/Tablet|iPad/i.test(userAgent)) deviceType = 'Tablet';
    const deviceTypeInput = document.getElementById('device_type');
    if (deviceTypeInput) deviceTypeInput.value = deviceType;
})();

(function () {
    const fileInput = document.getElementById('file');
    const fileCount = document.getElementById('file-count');
    const chooseButton = document.getElementById('choose-files-btn');
    const clearButton = document.getElementById('clear-selection');
    const dropzone = document.getElementById('dropzone');
    let dataTransfer = (() => {
        try {
            return new DataTransfer();
        } catch (_error) {
            return null;
        }
    })();
    const store = [];
    window.__guestFiles = store;
    window.__guestDT = dataTransfer;

    function isAccepted(file) {
        try {
            if (file && file.type && (file.type.startsWith('image/') || file.type.startsWith('video/'))) {
                return true;
            }
        } catch (_error) {
            // Ignore mime sniff failures.
        }
        try {
            const name = file && file.name ? file.name.toLowerCase() : '';
            const extension = name.split('.').pop();
            const allowed = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'heic', 'heif', 'bmp', 'tiff', 'tif', 'mp4', 'mov', 'm4v', 'avi', 'mkv', 'webm'];
            return allowed.indexOf(extension) !== -1;
        } catch (_error) {
            return false;
        }
    }

    function render() {
        if (dataTransfer) {
            try {
                fileInput.files = dataTransfer.files;
            } catch (_error) {
                // Ignore file assignment failures.
            }
        }
        const count = store.length;
        if (fileCount) {
            fileCount.textContent = count === 0 ? '' : count === 1 ? '1 item selected' : `${count} items selected`;
        }
        if (clearButton) clearButton.style.display = count > 0 ? '' : 'none';
        try {
            document.dispatchEvent(new CustomEvent('epu-selection-change', { detail: { count } }));
        } catch (_error) {
            // Ignore unsupported CustomEvent issues.
        }
        window.__guestDT = dataTransfer;
        window.__guestFiles = store;
    }

    function addFiles(list) {
        if (!list) return;
        try {
            for (const file of list) {
                if (!isAccepted(file)) continue;
                store.push(file);
                if (dataTransfer) dataTransfer.items.add(file);
            }
        } catch (_error) {
            // Ignore partial file ingestion failures.
        }
        render();
    }

    if (chooseButton && fileInput) {
        chooseButton.addEventListener('click', () => fileInput.click());
    }
    if (clearButton) {
        clearButton.addEventListener('click', () => {
            store.splice(0, store.length);
            if (dataTransfer) {
                try {
                    dataTransfer = new DataTransfer();
                } catch (_error) {
                    dataTransfer = null;
                }
            }
            window.__guestDT = dataTransfer;
            window.__guestFiles = store;
            render();
        });
    }
    if (fileInput) {
        fileInput.addEventListener('change', () => {
            addFiles(fileInput.files);
            fileInput.value = '';
        });
    }

    if (dropzone && fileInput) {
        function setDrag(on) {
            dropzone.classList.toggle('is-drag', !!on);
        }

        dropzone.addEventListener('click', () => fileInput.click());
        dropzone.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                fileInput.click();
            }
        });
        dropzone.addEventListener('dragover', (event) => {
            event.preventDefault();
            setDrag(true);
        });
        dropzone.addEventListener('dragenter', (event) => {
            event.preventDefault();
            setDrag(true);
        });
        dropzone.addEventListener('dragleave', () => setDrag(false));
        dropzone.addEventListener('drop', (event) => {
            event.preventDefault();
            setDrag(false);
            addFiles(event.dataTransfer && event.dataTransfer.files);
        });
    }

    render();
})();

(function () {
    const terms = document.getElementById('terms');
    const uploadButton = document.getElementById('upload-btn');
    let count = 0;

    function apply() {
        if (uploadButton) uploadButton.disabled = !(terms && terms.checked && count > 0);
    }

    if (terms) terms.addEventListener('change', apply);
    document.addEventListener('epu-selection-change', (event) => {
        count = (event && event.detail && event.detail.count) || 0;
        apply();
    });
    apply();
})();

(function () {
    const message = document.getElementById('guest_message');
    const counter = document.getElementById('gm-counter');
    if (!message || !counter) return;

    function sync() {
        counter.textContent = `${(message.value || '').length}/300`;
    }

    message.addEventListener('input', sync);
    sync();
})();

(function () {
    const termsLink = document.getElementById('terms-link');
    const termsCheckbox = document.getElementById('terms');

    async function openSharedModal() {
        try {
            const response = await fetch('/terms/embed', { headers: { 'X-Requested-With': 'fetch' } });
            const html = await response.text();
            const footer = window.EPU && window.EPU.ui
                ? window.EPU.ui.renderBtnRow(
                    '<a href="/terms" target="_blank" class="btn" style="margin-right:auto;">Open full page</a>',
                    'style="justify-content:flex-end; margin-top:8px;"'
                )
                : '<div class="btn-row" style="justify-content:flex-end; margin-top:8px;"><a href="/terms" target="_blank" class="btn" style="margin-right:auto;">Open full page</a></div>';
            const body = `<div style="height:65vh; overflow:auto; padding:12px 16px;">${html}</div>${footer}`;
            if (window.EPU && window.EPU.modal) {
                window.EPU.modal.show({
                    title: 'Terms and Conditions',
                    body,
                    fit: true,
                    actions: [
                        { label: 'Cancel', role: 'cancel' },
                        {
                            label: 'I Agree',
                            onClick(hide) {
                                if (termsCheckbox) termsCheckbox.checked = true;
                                hide();
                            },
                        },
                    ],
                });
            }
        } catch (_error) {
            if (window.EPU && window.EPU.modal) {
                window.EPU.modal.show({
                    title: 'Terms and Conditions',
                    body: '<p class="muted">Could not load terms. Please open the full page: <a href="/terms" target="_blank">/terms</a></p>',
                    actions: [{ label: 'Close', role: 'cancel' }],
                    fit: true,
                });
            }
        }
    }

    if (termsLink) {
        termsLink.addEventListener('click', (event) => {
            event.preventDefault();
            openSharedModal();
        });
    }
})();

(function () {
    const form = document.getElementById('guest-upload-form');
    if (!form) return;
    const fill = document.getElementById('upload-fill');
    const progressContainer = document.getElementById('progress-container');
    const success = document.getElementById('upload-success');
    const uploadButton = document.getElementById('upload-btn');
    const terms = document.getElementById('terms');

    form.addEventListener('submit', (event) => {
        event.preventDefault();
        let filesList = Array.isArray(window.__guestFiles) ? window.__guestFiles : null;
        const input = document.getElementById('file');
        if ((!filesList || filesList.length === 0) && input && input.files) {
            filesList = Array.from(input.files);
        }
        if (!terms || !terms.checked || !filesList || filesList.length === 0) {
            if (uploadButton) {
                uploadButton.classList.add('shake');
                setTimeout(() => uploadButton.classList.remove('shake'), 350);
            }
            const fileHint = document.getElementById('file-hint');
            if (fileHint) {
                fileHint.style.display = !filesList || filesList.length === 0 ? '' : 'none';
                setTimeout(() => {
                    fileHint.style.display = 'none';
                }, 2000);
            }
            if (terms && !terms.checked) {
                const label = document.getElementById('terms-label');
                if (label) {
                    label.style.transition = 'outline-color .2s';
                    label.style.outline = '2px solid var(--accent)';
                    setTimeout(() => {
                        label.style.outline = '';
                    }, 700);
                }
            }
            return;
        }

        progressContainer.style.display = 'block';
        success.style.display = 'none';
        if (fill) fill.style.width = '0%';
        if (uploadButton) uploadButton.disabled = true;

        const xhr = new XMLHttpRequest();
        xhr.open('POST', window.location.pathname);
        xhr.upload.onprogress = (progressEvent) => {
            if (progressEvent.lengthComputable && fill) {
                const percent = Math.round((progressEvent.loaded / progressEvent.total) * 100);
                fill.style.width = `${percent}%`;
            }
        };
        xhr.onload = () => {
            if (xhr.status === 200) {
                success.style.display = 'block';
                if (fill) fill.style.width = '100%';
                const skipped = parseInt(xhr.getResponseHeader('X-Duplicates-Skipped') || '0', 10);
                const duplicates = document.getElementById('upload-duplicates');
                if (duplicates) {
                    duplicates.textContent = skipped > 0
                        ? skipped === 1
                            ? '1 duplicate was skipped.'
                            : `${skipped} duplicates were skipped.`
                        : '';
                    duplicates.style.display = skipped > 0 ? 'block' : 'none';
                }
                try {
                    refreshGrid(1);
                } catch (_error) {
                    // Ignore grid refresh failures.
                }
                try {
                    const clearButton = document.getElementById('clear-selection');
                    if (clearButton) clearButton.click();
                } catch (_error) {
                    // Ignore cleanup failures.
                }
            } else if (xhr.status === 400 || xhr.status === 403) {
                const card = document.querySelector('.guest-card');
                if (card) {
                    const error = document.createElement('div');
                    error.className = 'form-error';
                    error.setAttribute('role', 'alert');
                    const text = (xhr.responseText || '').toString();
                    error.innerHTML = text.includes('upgrade your plan')
                        ? 'Limit reached. Please <a href="/pricing">choose a package</a>.'
                        : 'Upload blocked.';
                    card.insertBefore(error, card.firstChild.nextSibling);
                }
            }
            setTimeout(() => {
                progressContainer.style.display = 'none';
            }, 800);
            if (uploadButton) uploadButton.disabled = false;
        };

        const formData = new FormData(form);
        try {
            const guestMessage = document.getElementById('guest_message');
            if (guestMessage) formData.set('guest_message', guestMessage.value || '');
            const displayName = document.getElementById('display_name');
            if (displayName) formData.set('display_name', displayName.value || '');
            const guestEmail = document.getElementById('guest_email');
            if (guestEmail) formData.set('guest_email', guestEmail.value || '');
        } catch (_error) {
            // Ignore field serialization failures.
        }
        try {
            for (let index = 0; index < filesList.length; index += 1) {
                formData.append('files', filesList[index]);
            }
        } catch (_error) {
            // Ignore explicit file append failures.
        }
        xhr.send(formData);
    });
})();

(function () {
    const grid = document.getElementById('guest-files');
    if (!grid) return;
    const csrfInput = document.querySelector('#guest-upload-form input[name="csrf_token"]');
    const csrfToken = csrfInput ? (csrfInput.value || '') : '';
    const bulkButton = document.getElementById('bulk-remove');
    const selectionCount = document.getElementById('sel-count');
    let currentFilter = 'all';
    let currentSort = 'newest';
    let page = 1;
    const selected = new Set();

    function addItem(file) {
        const item = document.createElement('div');
        item.className = 'thumb selectable theme-tile';
        item.setAttribute('data-id', file.id);
        item.setAttribute('data-type', (file.type || '').startsWith('image') ? 'image' : (file.type || '').startsWith('video') ? 'video' : 'other');

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'select';
        checkbox.setAttribute('aria-label', 'Select');
        checkbox.style.cssText = 'position:absolute; top:6px; left:6px; width:18px; height:18px;';

        let media;
        if ((file.type || '').startsWith('image')) {
            media = document.createElement('img');
            media.src = file.url;
            media.alt = file.name;
            media.loading = 'lazy';
            media.setAttribute('data-role', 'preview');
            media.style.cssText = 'width:100%; height:100px; object-fit:cover; border-radius:6px; cursor:pointer;';
        } else if ((file.type || '').startsWith('video')) {
            media = document.createElement('video');
            media.src = file.url;
            media.muted = true;
            media.preload = 'metadata';
            media.setAttribute('data-role', 'preview');
            media.style.cssText = 'width:100%; height:100px; object-fit:cover; border-radius:6px; cursor:pointer;';
        } else {
            media = document.createElement('div');
            media.className = 'name-fallback';
            media.textContent = file.name;
            media.style.cssText = 'height:100px; display:flex; align-items:center; justify-content:center; font-size:12px; text-align:center; padding:6px;';
        }

        item.appendChild(checkbox);
        item.appendChild(media);
        grid.appendChild(item);
    }

    function updateBulkState() {
        if (selectionCount) selectionCount.textContent = `${selected.size} selected`;
        if (bulkButton) bulkButton.disabled = selected.size === 0;
    }

    grid.addEventListener('change', (event) => {
        const checkbox = event.target.closest('input.select');
        if (!checkbox) return;
        const item = checkbox.closest('[data-id]');
        if (!item) return;
        const id = item.getAttribute('data-id');
        if (checkbox.checked) {
            selected.add(id);
            item.style.outline = '2px solid var(--accent)';
        } else {
            selected.delete(id);
            item.style.outline = '';
        }
        updateBulkState();
    });

    if (bulkButton) {
        bulkButton.addEventListener('click', () => {
            if (selected.size === 0 || !(window.EPU && window.EPU.modal)) return;
            window.EPU.modal.show({
                title: 'Remove selected?',
                body: `This will remove ${selected.size} file(s) from this event.`,
                actions: [
                    { label: 'Cancel', role: 'cancel' },
                    {
                        label: 'Remove',
                        danger: true,
                        async onClick(hide) {
                            try {
                                const ids = Array.from(selected);
                                for (const id of ids) {
                                    const formData = new FormData();
                                    formData.append('file_id', id);
                                    formData.append('csrf_token', csrfToken);
                                    await fetch(`${window.location.pathname}/delete`, { method: 'POST', body: formData });
                                    const node = grid.querySelector(`[data-id="${id}"]`);
                                    if (node) node.remove();
                                }
                                selected.clear();
                                updateBulkState();
                                if (window.EPU && window.EPU.snackbar) {
                                    window.EPU.snackbar.show(`Removed ${ids.length} item(s).`);
                                }
                            } finally {
                                hide();
                            }
                        },
                    },
                ],
            });
        });
    }

    grid.addEventListener('click', (event) => {
        const media = event.target.closest('[data-role="preview"]');
        if (!media || !(window.EPU && window.EPU.modal)) return;
        const isVideo = media.tagName.toLowerCase() === 'video';
        const body = isVideo
            ? `<div class="preview-body"><video src="${media.currentSrc}" controls style="max-width:90vw; max-height:80vh; display:block;"></video></div>`
            : `<div class="preview-body"><img src="${media.currentSrc}" alt="Preview" style="max-width:90vw; max-height:80vh; display:block;" /></div>`;
        window.EPU.modal.show({ title: 'Preview', body, actions: [{ label: 'Close', role: 'cancel' }], fit: true });
    });

    function applyFilter(type) {
        currentFilter = type;
        Array.from(document.querySelectorAll('#guest-files [data-type]')).forEach((element) => {
            if (type === 'all') element.style.display = '';
            else element.style.display = element.getAttribute('data-type') === type ? '' : 'none';
        });
    }

    function bind(button, type) {
        if (!button) return;
        button.addEventListener('click', (event) => {
            event.preventDefault();
            applyFilter(type);
            refreshGrid(1);
        });
    }

    bind(document.getElementById('filter-all'), 'all');
    bind(document.getElementById('filter-images'), 'image');
    bind(document.getElementById('filter-videos'), 'video');

    const sortSelect = document.getElementById('sort');
    if (sortSelect) {
        sortSelect.addEventListener('change', () => {
            currentSort = sortSelect.value || 'newest';
            refreshGrid(1);
        });
    }

    async function loadPages(options = {}) {
        const startPage = Number.isInteger(options.startPage) ? options.startPage : 1;
        const replace = !!options.replace;
        try {
            const loadedItems = [];
            let nextPage = startPage;
            let keepLoading = true;

            while (keepLoading) {
                const url = `${window.location.pathname}/list?page=${nextPage}${currentFilter === 'all' ? '' : `&type=${currentFilter}`}&sort=${encodeURIComponent(currentSort)}`;
                const response = await fetch(url);
                const payload = await response.json();
                const items = payload && payload.ok && Array.isArray(payload.items) ? payload.items : [];
                if (items.length) loadedItems.push(...items);
                keepLoading = !!(payload && payload.has_more);
                nextPage += 1;
            }

            if (replace) {
                grid.innerHTML = '';
                loadedItems.forEach(addItem);
                const card = document.getElementById('your-uploads-card');
                if (card) {
                    if (loadedItems.length > 0) card.classList.remove('is-hidden');
                    else card.classList.add('is-hidden');
                }
                const hint = document.getElementById('uploads-empty-hint');
                if (hint) {
                    if (loadedItems.length > 0) hint.classList.add('is-hidden');
                    else hint.classList.remove('is-hidden');
                }
                selected.clear();
                updateBulkState();
            } else if (loadedItems.length) {
                loadedItems.forEach(addItem);
            }

            page = Math.max(startPage, nextPage - 1);
        } catch (_error) {
            // Ignore list-load failures.
        }
    }

    (async function autoLoadAll() {
        await loadPages({ startPage: 2, replace: false });
    })();

    window.refreshGrid = async function refreshGrid(pageNum) {
        try {
            const startPage = Number.isInteger(pageNum) && pageNum > 0 ? pageNum : 1;
            await loadPages({ startPage, replace: true });
        } catch (_error) {
            // Ignore refresh failures.
        }
    };
})();
