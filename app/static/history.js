function fmtDate(iso) {
  const d = new Date(iso + 'Z');
  return d.toLocaleString('zh-TW', { hour12: false });
}

fetch('/api/history?limit=50').then(r => r.json()).then(data => {
  document.getElementById('total-attempts').textContent = `目前累計作答 ${data.total_attempts} 次。`;

  const statsBody = document.querySelector('#stats-table tbody');
  data.stats.forEach(s => {
    const tr = document.createElement('tr');
    const acc = s.accuracy !== null && s.accuracy !== undefined ? `${Math.round(s.accuracy * 100)}%` : '-';
    tr.innerHTML = `<td>${s.exam}</td><td>${s.section}</td><td>${s.item_type}</td><td>${s.total}</td><td>${s.correct}</td><td>${acc}</td>`;
    statsBody.appendChild(tr);
  });
  if (!data.stats.length) {
    statsBody.innerHTML = '<tr><td colspan="6">尚無作答紀錄,請先到練習頁面作答。</td></tr>';
  }

  const recentBody = document.querySelector('#recent-table tbody');
  data.recent.forEach(a => {
    const result = a.item_type === 'objective'
      ? (a.is_correct ? '✓ 正確' : '✗ 錯誤')
      : (a.score ? `分數: ${a.score}` : '-');
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${fmtDate(a.created_at)}</td><td>${a.exam}</td><td>${a.section}</td><td>${a.item_type}</td><td>${result}</td>`;
    recentBody.appendChild(tr);
  });
  if (!data.recent.length) {
    recentBody.innerHTML = '<tr><td colspan="5">尚無作答紀錄。</td></tr>';
  }
});
