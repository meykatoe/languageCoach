// Populates the nav bar's username + wires up the logout link. Included on
// every logged-in page (not /login or /register).
fetch('/api/auth/me').then(r => (r.ok ? r.json() : null)).then(data => {
  const label = document.getElementById('nav-user');
  if (label && data) {
    label.textContent = data.username;
  }
});

document.getElementById('logout-link')?.addEventListener('click', async e => {
  e.preventDefault();
  await fetch('/api/auth/logout', { method: 'POST' });
  location.href = '/login';
});
