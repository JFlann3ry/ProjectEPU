const PASSWORD_CHECKS = [
  { id: 'length-check', test: (pwd) => pwd.length >= 8 },
  { id: 'number-check', test: (pwd) => /\d/.test(pwd) },
  { id: 'capital-check', test: (pwd) => /[A-Z]/.test(pwd) },
  { id: 'special-check', test: (pwd) => /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>/?]/.test(pwd) },
];

function getEl(id) {
  return document.getElementById(id);
}

function updatePasswordPolicy(passwordInput, passwordPolicy) {
  if (!passwordInput || !passwordPolicy) {
    return;
  }
  const pwd = passwordInput.value || '';
  let unmet = 0;
  PASSWORD_CHECKS.forEach(({ id, test }) => {
    const item = getEl(id);
    if (!item) {
      return;
    }
    const ok = test(pwd);
    item.style.display = ok ? 'none' : '';
    if (!ok) {
      unmet += 1;
    }
  });
  passwordPolicy.style.display = pwd && unmet > 0 ? '' : 'none';
}

function validateEmail(value) {
  if (!value) {
    return false;
  }
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

function setupEmailValidation() {
  const emailInput = getEl('email');
  const emailFeedback = getEl('email-feedback');
  if (!emailInput || !emailFeedback) {
    return;
  }
  emailInput.addEventListener('input', () => {
    const value = emailInput.value || '';
    const invalid = value.trim() !== '' && !validateEmail(value);
    emailFeedback.style.display = invalid ? '' : 'none';
    if (invalid) {
      emailInput.setAttribute('aria-invalid', 'true');
    } else {
      emailInput.removeAttribute('aria-invalid');
    }
  });
}

function setupPasswordConfirm(passwordInput) {
  const confirmInput = getEl('password_confirm') || getEl('password2');
  const confirmFeedback = getEl('confirm-feedback');
  const matchMessage = getEl('match-msg');
  if (!passwordInput || !confirmInput) {
    return;
  }

  const renderConfirmState = () => {
    const password = passwordInput.value || '';
    const confirm = confirmInput.value || '';
    const showState = confirm.length > 0 || password.length > 0;
    const match = password === confirm;
    const hasMismatch = showState && !match;

    confirmInput.setCustomValidity(hasMismatch ? 'Passwords do not match' : '');

    if (confirmFeedback) {
      confirmFeedback.style.display = hasMismatch ? '' : 'none';
    }

    if (matchMessage) {
      if (!showState) {
        matchMessage.style.display = 'none';
      } else {
        matchMessage.style.display = '';
        matchMessage.style.color = match ? '#1b8a1b' : '#b00020';
        matchMessage.textContent = match ? 'Passwords match' : 'Passwords do not match';
      }
    }
  };

  confirmInput.addEventListener('input', renderConfirmState);
  confirmInput.addEventListener('focus', renderConfirmState);
  confirmInput.addEventListener('blur', () => {
    if (!matchMessage) {
      return;
    }
    window.setTimeout(() => {
      matchMessage.style.display = 'none';
    }, 100);
  });
  passwordInput.addEventListener('input', renderConfirmState);

  renderConfirmState();
}

function boot() {
  const passwordInput = getEl('password');
  const passwordPolicy = getEl('password-policy');

  if (passwordInput && passwordPolicy) {
    const refreshPolicy = () => updatePasswordPolicy(passwordInput, passwordPolicy);
    passwordInput.addEventListener('focus', refreshPolicy);
    passwordInput.addEventListener('input', refreshPolicy);
    passwordInput.addEventListener('blur', () => {
      window.setTimeout(() => {
        passwordPolicy.style.display = 'none';
      }, 100);
    });
    refreshPolicy();
  }

  setupEmailValidation();
  setupPasswordConfirm(passwordInput);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot);
} else {
  boot();
}