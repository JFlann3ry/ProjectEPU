(function () {
    'use strict';
    document.addEventListener('DOMContentLoaded', function () {
        var btn = document.getElementById('confirm-delete');
        var form = document.getElementById('delete-form');
        if (btn && form && window.EPU && window.EPU.modal) {
            btn.addEventListener('click', function () {
                // Ensure checkbox is ticked or show message
                var check = form.querySelector('input[name="confirm"]');
                if (!check || !check.checked) {
                    window.EPU.modal.show({ title: 'Missing confirmation', body: '<p class="muted">Please tick the confirmation checkbox before proceeding.</p>', actions: [{ label: 'OK', role: 'cancel', onClick: function (h) { h(); } }] });
                    return;
                }
                window.EPU.modal.show({
                    title: 'Delete Account?',
                    body: '<p class="muted">This will permanently delete your account and all associated data. This action cannot be undone. Are you sure you want to continue?</p>',
                    actions: [
                        { label: 'Cancel', role: 'cancel', onClick: function (hide) { hide(); } },
                        { label: 'Yes, delete', danger: true, onClick: function () { form.submit(); } }
                    ]
                });
            });
        }
    });
})();
