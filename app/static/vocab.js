// /vocab page: lists words auto-saved by the site-wide "select text to
// translate" feature (see selection-translate.js), each with a full
// dictionary-style entry generated via OpenAI. Cards expand on click to
// show the detail; a search box filters client-side.

function fmtDate(iso) {
  const d = new Date(iso + 'Z');
  return d.toLocaleString('zh-TW', { hour12: false });
}

function escapeHtml(s) {
  const div = document.createElement('div');
  div.textContent = s == null ? '' : String(s);
  return div.innerHTML;
}

function renderDefinitionList(defs) {
  return (defs || [])
    .map(
      (def) => `
        <li>
          <p>${escapeHtml(def.meaning_en)}<br><span class="hint">${escapeHtml(def.meaning_zh)}</span></p>
          ${def.example_en ? `<p class="vocab-example">"${escapeHtml(def.example_en)}"${def.example_zh ? `<br>${escapeHtml(def.example_zh)}` : ''}</p>` : ''}
        </li>`
    )
    .join('');
}

function renderWordList(label, items) {
  if (!items || !items.length) return '';
  return `<p><strong>${label}:</strong> ${items.map(escapeHtml).join('、')}</p>`;
}

function renderDetail(word) {
  const d = word.detail;
  if (!d) {
    return `
      <div class="vocab-detail">
        <p class="hint">詳細釋義生成中,或先前生成失敗,請稍後重新整理查看,或點下方按鈕重試。</p>
        <div class="vocab-actions">
          <button class="secondary regen-btn" data-id="${word.id}">重新產生釋義</button>
        </div>
      </div>`;
  }
  const posBlocks = (d.entries || [])
    .map(
      (e) => `
        <div class="vocab-pos-block">
          <p class="vocab-pos">${escapeHtml(e.partOfSpeech)}</p>
          <ol>${renderDefinitionList(e.definitions)}</ol>
        </div>`
    )
    .join('');

  return `
    <div class="vocab-detail">
      ${posBlocks}
      ${renderWordList('同義詞', d.synonyms)}
      ${renderWordList('反義詞', d.antonyms)}
      ${renderWordList('常見搭配', d.collocations)}
      ${renderWordList('相關詞形', d.wordFamily)}
      ${d.memoryTip ? `<div class="vocab-tip">💡 ${escapeHtml(d.memoryTip)}</div>` : ''}
      <div class="vocab-actions">
        <button class="secondary regen-btn" data-id="${word.id}">重新產生釋義</button>
        <button class="secondary delete-btn" data-id="${word.id}">移除單字</button>
      </div>
    </div>`;
}

function renderCard(word) {
  const card = document.createElement('div');
  card.className = 'card vocab-word-card';
  card.dataset.word = word.word;

  const phonetic = word.detail && word.detail.phonetic ? `<span class="vocab-phonetic">${escapeHtml(word.detail.phonetic)}</span>` : '';
  card.innerHTML = `
    <div class="vocab-word-head">
      <div><span class="vocab-word">${escapeHtml(word.word)}</span>${phonetic}</div>
      <span class="vocab-date">${fmtDate(word.created_at)}</span>
    </div>
  `;

  let expanded = false;
  const head = card.querySelector('.vocab-word-head');
  head.addEventListener('click', () => {
    expanded = !expanded;
    let detailEl = card.querySelector('.vocab-detail');
    if (expanded) {
      if (!detailEl) {
        card.insertAdjacentHTML('beforeend', renderDetail(word));
        detailEl = card.querySelector('.vocab-detail');
      }
    } else if (detailEl) {
      detailEl.remove();
    }
  });

  card.addEventListener('click', async (e) => {
    const target = e.target;
    if (target.classList.contains('delete-btn')) {
      e.stopPropagation();
      target.disabled = true;
      await fetch(`/api/vocab/${target.dataset.id}`, { method: 'DELETE' });
      card.remove();
    } else if (target.classList.contains('regen-btn')) {
      e.stopPropagation();
      target.disabled = true;
      target.textContent = '生成中...';
      try {
        const res = await fetch(`/api/vocab/${target.dataset.id}/regenerate`, { method: 'POST' });
        const data = await res.json().catch(() => ({}));
        if (res.ok) {
          word.detail = data.detail;
          card.querySelector('.vocab-detail').remove();
          card.insertAdjacentHTML('beforeend', renderDetail(word));
          if (data.detail && data.detail.phonetic && !card.querySelector('.vocab-phonetic')) {
            card.querySelector('.vocab-word').insertAdjacentHTML(
              'afterend',
              `<span class="vocab-phonetic">${escapeHtml(data.detail.phonetic)}</span>`
            );
          }
        } else {
          alert(`生成失敗: ${data.detail || res.status}`);
          target.disabled = false;
          target.textContent = '重新產生釋義';
        }
      } catch (err) {
        target.disabled = false;
        target.textContent = '重新產生釋義';
      }
    }
  });

  return card;
}

let allWords = [];

function applyFilter() {
  const q = document.getElementById('vocab-search').value.trim().toLowerCase();
  const listEl = document.getElementById('vocab-list');
  listEl.innerHTML = '';
  const filtered = q ? allWords.filter((w) => w.word.includes(q)) : allWords;
  filtered.forEach((w) => listEl.appendChild(renderCard(w)));
  if (!filtered.length) {
    listEl.innerHTML = `<div class="card">${allWords.length ? '沒有符合搜尋的單字。' : '單字本目前是空的。到練習頁面選取(反白)任何英文單字並放開,就會自動加入這裡。'}</div>`;
  }
}

fetch('/api/vocab')
  .then((r) => r.json())
  .then((data) => {
    allWords = data;
    document.getElementById('vocab-count').textContent = `目前共收錄 ${data.length} 個單字。`;
    applyFilter();
  });

document.getElementById('vocab-search').addEventListener('input', applyFilter);
