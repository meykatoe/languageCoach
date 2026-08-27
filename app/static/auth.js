function nextUrlParam() {
  return new URLSearchParams(location.search).get('next') || '/';
}

async function submitAuthForm(form, url, errorEl) {
  errorEl.textContent = '';
  const body = {
    username: form.username.value.trim(),
    password: form.password.value,
  };
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    errorEl.textContent = data.detail || '發生錯誤,請稍後再試。';
    return;
  }
  location.href = nextUrlParam();
}

document.getElementById('login-form')?.addEventListener('submit', e => {
  e.preventDefault();
  submitAuthForm(e.target, '/api/auth/login', document.getElementById('login-error'));
});

document.getElementById('register-form')?.addEventListener('submit', e => {
  e.preventDefault();
  submitAuthForm(e.target, '/api/auth/register', document.getElementById('register-error'));
});
