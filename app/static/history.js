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

const SVG_NS = 'http://www.w3.org/2000/svg';

function svgEl(tag, attrs) {
  const el = document.createElementNS(SVG_NS, tag);
  Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
  return el;
}

function emptyChart(container, message) {
  const p = document.createElement('p');
  p.className = 'hint';
  p.textContent = message;
  container.appendChild(p);
}

// Line chart of daily accuracy (0-1) over time. Pure SVG, no chart library,
// so it inherits the page's CSS variables (incl. dark mode) via currentColor.
function renderTrendChart(container, points) {
  container.replaceChildren();
  if (!points.length) {
    emptyChart(container, '尚無客觀題作答紀錄,做完幾題後這裡會顯示每日正確率趨勢。');
    return;
  }

  const width = 640;
  const height = 220;
  const padL = 40;
  const padR = 12;
  const padT = 16;
  const padB = 28;
  const plotW = width - padL - padR;
  const plotH = height - padT - padB;

  const svg = svgEl('svg', {
    viewBox: `0 0 ${width} ${height}`,
    preserveAspectRatio: 'none',
    class: 'chart-svg',
    role: 'img',
    'aria-label': '每日正確率趨勢折線圖',
  });

  // Y-axis gridlines + labels at 0%, 50%, 100%
  [0, 0.5, 1].forEach(frac => {
    const y = padT + plotH * (1 - frac);
    svg.appendChild(svgEl('line', {
      x1: padL, x2: width - padR, y1: y, y2: y, class: 'chart-grid',
    }));
    const label = svgEl('text', { x: padL - 6, y: y + 4, class: 'chart-axis-label', 'text-anchor': 'end' });
    label.textContent = `${Math.round(frac * 100)}%`;
    svg.appendChild(label);
  });

  const n = points.length;
  const xFor = i => (n === 1 ? padL + plotW / 2 : padL + (plotW * i) / (n - 1));
  const yFor = acc => padT + plotH * (1 - acc);

  const linePoints = points.map((p, i) => `${xFor(i)},${yFor(p.accuracy)}`).join(' ');
  svg.appendChild(svgEl('polyline', { points: linePoints, class: 'chart-line' }));

  points.forEach((p, i) => {
    const cx = xFor(i);
    const cy = yFor(p.accuracy);
    const dot = svgEl('circle', { cx, cy, r: 3, class: 'chart-dot' });
    const title = svgEl('title', {});
    title.textContent = `${p.date}: ${p.correct}/${p.total} (${Math.round(p.accuracy * 100)}%)`;
    dot.appendChild(title);
    svg.appendChild(dot);

    // Thin out x-axis date labels so they don't overlap on a 30-day range.
    const step = Math.ceil(n / 6);
    if (i % step === 0 || i === n - 1) {
      const label = svgEl('text', { x: cx, y: height - 8, class: 'chart-axis-label', 'text-anchor': 'middle' });
      label.textContent = p.date.slice(5); // MM-DD
      svg.appendChild(label);
    }
  });

  container.appendChild(svg);
}

// Horizontal bar chart of accuracy per exam/section (objective items only).
function renderStatsChart(container, stats) {
  container.replaceChildren();
  const rows = stats.filter(s => s.item_type === 'objective' && s.accuracy !== null && s.accuracy !== undefined);
  if (!rows.length) {
    emptyChart(container, '尚無客觀題正確率資料。');
    return;
  }

  const width = 640;
  const rowH = 32;
  const padL = 140;
  const padR = 50;
  const height = rows.length * rowH + 8;
  const barMaxW = width - padL - padR;

  const svg = svgEl('svg', {
    viewBox: `0 0 ${width} ${height}`,
    preserveAspectRatio: 'none',
    class: 'chart-svg',
    role: 'img',
    'aria-label': '各考試/類別正確率長條圖',
  });

  rows.forEach((s, i) => {
    const y = i * rowH + 6;
    const barW = Math.max(barMaxW * s.accuracy, 2);

    const label = svgEl('text', { x: padL - 8, y: y + rowH / 2 - 6, class: 'chart-axis-label', 'text-anchor': 'end' });
    label.textContent = `${s.exam} ${s.section}`;
    svg.appendChild(label);

    svg.appendChild(svgEl('rect', {
      x: padL, y, width: barMaxW, height: rowH - 12, class: 'chart-bar-track', rx: 4,
    }));
    const bar = svgEl('rect', {
      x: padL, y, width: barW, height: rowH - 12, class: 'chart-bar', rx: 4,
    });
    const title = svgEl('title', {});
    title.textContent = `${s.correct}/${s.total} (${Math.round(s.accuracy * 100)}%)`;
    bar.appendChild(title);
    svg.appendChild(bar);

    const pct = svgEl('text', { x: padL + barMaxW + 6, y: y + rowH / 2 - 6, class: 'chart-axis-label' });
    pct.textContent = `${Math.round(s.accuracy * 100)}%`;
    svg.appendChild(pct);
  });

  container.appendChild(svg);
}

fetch('/api/history?limit=50').then(r => r.json()).then(data => {
  renderTrendChart(document.getElementById('trend-chart'), data.daily_accuracy);
  renderStatsChart(document.getElementById('stats-chart'), data.stats);

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
