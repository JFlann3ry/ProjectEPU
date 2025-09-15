// Event task toggling helper
(function(){
    async function toggleTask(e){
        var el = e.target.closest('.js-task-toggle');
        if (!el) return;
        // If this is a normal link (navigate), we still send toggle in background
        var taskKey = el.getAttribute('data-task-key');
        var eventId = el.getAttribute('data-event-id');
        if (!taskKey || !eventId) return;
        try {
            var body = new URLSearchParams();
            body.append('event_id', eventId);
            body.append('task_key', taskKey);
            var res = await fetch('/events/task/toggle', {
                method: 'POST',
                headers: { 'X-Requested-With': 'fetch' },
                body: body
            });
            if (res.ok){
                // Toggle UI state based on response JSON if present
                try {
                    var j = await res.json();
                    var done = !!j.done;
                    if (done){ el.classList.remove('pending'); el.classList.add('done'); }
                    else { el.classList.remove('done'); el.classList.add('pending'); }
                } catch(err){ /* ignore parse errors */ }
            }
        } catch(err){ /* network error - ignore */ }
    }

    document.addEventListener('click', function(e){
        var tgt = e.target.closest('.js-task-toggle');
        if (!tgt) return;
        // Let navigation happen for anchors, but still call toggle in background
        toggleTask(e);
    }, true);

})();
