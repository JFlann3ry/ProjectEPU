const TOPIC_PLACEHOLDERS = {
  Account: 'Log in issues, email changes, profile…',
  'Abuse/report': 'Link to the event/file and what’s wrong…',
  Billing: 'Refund, invoice, VAT, or charge questions…',
  'Data/privacy': 'Data export/deletion, privacy questions…',
  'Event help': 'Share your event code and what you need…',
  'Feature request': 'What feature would help you most?…',
  'Technical issue': 'Describe the issue and steps to reproduce…',
  Other: 'Tell us how we can help…',
};

function bindCounter(input, counter, max) {
  if (!input || !counter) {
    return;
  }
  const sync = () => {
    counter.textContent = `${(input.value || '').length}/${max}`;
  };
  input.addEventListener('input', sync);
  sync();
}

function detectInserted(text) {
  const lines = (text || '').split(/\r?\n/);
  let index = 0;
  const hasId = !!(lines[index] && /^\s*Request ID\s*:/i.test(lines[index]));
  if (hasId) {
    index += 1;
  }
  const hasPage = !!(lines[index] && /^\s*Page\s*:/i.test(lines[index]));
  return hasId || hasPage;
}

function setupTopicBehavior(message) {
  const select = document.getElementById('contact_topic');
  const billingExtra = document.getElementById('billing-extra');
  const subjectWrap = document.getElementById('subject-other');
  if (!select) {
    return;
  }
  const sync = () => {
    const value = select.value || '';
    if (billingExtra) {
      billingExtra.style.display = value === 'Billing' ? 'block' : 'none';
    }
    if (subjectWrap) {
      subjectWrap.style.display = value === 'Other' ? 'block' : 'none';
    }
    if (message) {
      message.placeholder = TOPIC_PLACEHOLDERS[value] || TOPIC_PLACEHOLDERS.Other;
    }
  };
  select.addEventListener('change', sync);
  sync();
}

function setupRequestDetails(message) {
  const meta = document.getElementById('contact-meta');
  const clearButton = document.getElementById('clear-inserted');
  const messageCounter = document.getElementById('message-counter');
  if (!message) {
    return;
  }

  const syncClearState = () => {
    if (clearButton) {
      clearButton.hidden = !detectInserted(message.value);
    }
    if (messageCounter) {
      messageCounter.textContent = `${message.value.length}/2000`;
    }
  };

  const clearInserted = () => {
    const lines = (message.value || '').split(/\r?\n/);
    let start = 0;
    if (lines[start] && /^\s*Request ID\s*:/i.test(lines[start])) {
      start += 1;
    }
    if (lines[start] && /^\s*Page\s*:/i.test(lines[start])) {
      start += 1;
    }
    if (lines[start] === '') {
      start += 1;
    }
    message.value = lines.slice(start).join('\n');
    try {
      message.selectionStart = message.selectionEnd = message.value.length;
    } catch (_error) {
      // Ignore selection errors.
    }
    syncClearState();
  };

  if (clearButton) {
    clearButton.addEventListener('click', clearInserted);
  }

  message.addEventListener('input', syncClearState);

  const requestId = meta ? meta.dataset.requestId || '' : '';
  const requestUrl = meta ? meta.dataset.requestUrl || '' : '';
  if (requestId) {
    window.setTimeout(() => {
      const currentText = message.value || '';
      const parts = [];
      if (!/Request ID\s*:/i.test(currentText)) {
        parts.push(`Request ID: ${requestId}`);
      }
      if (requestUrl && !/Page\s*:/i.test(currentText)) {
        parts.push(`Page: ${requestUrl}`);
      }
      if (parts.length) {
        message.value = parts.join('\n') + (currentText ? `\n\n${currentText}` : '');
        try {
          message.selectionStart = message.selectionEnd = message.value.length;
        } catch (_error) {
          // Ignore selection errors.
        }
      }
      syncClearState();
    }, 800);
  }

  syncClearState();
}

function boot() {
  const message = document.getElementById('contact_message');
  bindCounter(document.getElementById('contact_name'), document.getElementById('name-counter'), 80);
  bindCounter(document.getElementById('contact_email'), document.getElementById('email-counter'), 254);
  bindCounter(document.getElementById('contact_subject'), document.getElementById('subject-counter'), 120);
  bindCounter(message, document.getElementById('message-counter'), 2000);
  setupTopicBehavior(message);
  setupRequestDetails(message);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot);
} else {
  boot();
}