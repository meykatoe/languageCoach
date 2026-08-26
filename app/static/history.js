function fmtDate(iso) {
  const d = new Date(iso + 'Z');
  return d.toLocaleString('zh-TW', { hour12: false });
}

// Builds a <tr> from plain-text cell values only (never HTML), so exam/
// section/part strings coming from user-supplied upload metadata can never
// be interpreted as markup.
function rowOf(values) {
  const tr = document.createElement('tr');
  values.forEach(v => {
    const td = document.createElement('td');
    td.textContent = v;
    tr.appendChild(td);
  });
  return tr;
}

function emptyRow(tbody, colspan, message) {
  const tr = document.createElement('tr');
  const td = document.createElement('td');
  td.colSpan = colspan;
  td.textContent = message;
  tr.appendChild(td);
  tbody.appendChild(tr);
}

fetch('/api/history?limit=50').then(r => r.json()).then(data => {
  document.getElementById('total-attempts').textContent = `目前累計作答 ${data.total_attempts} 次。`;

  const statsBody = document.querySelector('#stats-table tbody');
  data.stats.forEach(s => {
    const acc = s.accuracy !== null && s.accuracy !== undefined ? `${Math.round(s.accuracy * 100)}%` : '-';
    statsBody.appendChild(rowOf([s.exam, s.section, s.item_type, s.total, s.correct, acc]));
  });
  if (!data.stats.length) {
    emptyRow(statsBody, 6, '尚無作答紀錄,請先到練習頁面作答。');
  }

  const weaknessBody = document.querySelector('#weakness-table tbody');
  data.weaknesses.forEach(w => {
    weaknessBody.appendChild(rowOf([w.exam, w.section, w.part || '-', w.wrong_count]));
  });
  if (!data.weaknesses.length) {
    emptyRow(weaknessBody, 4, '目前沒有尚未答對的題目,做得很好!');
  }

  const recentBody = document.querySelector('#recent-table tbody');
  data.recent.forEach(a => {
    const result = a.item_type === 'objective'
      ? (a.is_correct ? '✓ 正確' : '✗ 錯誤')
      : (a.score ? `分數: ${a.score}` : '-');
    recentBody.appendChild(rowOf([fmtDate(a.created_at), a.exam, a.section, a.item_type, result]));
  });
  if (!data.recent.length) {
    emptyRow(recentBody, 5, '尚無作答紀錄。');
  }
});
