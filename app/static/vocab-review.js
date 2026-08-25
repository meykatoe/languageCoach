// /vocab/review page: spaced-repetition fill-in-the-blank review, driven by
// GET /api/vocab/review/queue and POST /api/vocab/{id}/review.

function escapeHtml(s) {
  const div = document.createElement('div');
  div.textContent = s == null ? '' : String(s);
  return div.innerHTML;
}

let queue = [];
let current = 0;

const area = document.getElementById('vocab-review-area');
const progress = document.getElementById('vocab-review-progress');

function renderDone() {
  progress.textContent = '';
  area.innerHTML = `<div class="card"><p>目前沒有到期需要複習的單字。</p><a href="/vocab">回單字本</a></div>`;
}

function renderQuestion() {
  const item = queue[current];
  progress.textContent = `第 ${current + 1} / ${queue.length} 題`;

  const sentenceHtml = escapeHtml(item.sentence).replace('_____', '<strong>_____</strong>');
  const phonetic = item.phonetic ? `<span class="vocab-phonetic">${escapeHtml(item.phonetic)}</span>` : '';

  area.innerHTML = `
    <div class="card">
      <p class="vocab-example">${sentenceHtml}</p>
      ${phonetic}
      <input type="text" id="review-answer" placeholder="請填入缺空的單字" autocomplete="off" />
      <div class="vocab-actions">
        <button id="review-submit">送出</button>
      </div>
      <div id="review-feedback" class="feedback"></div>
    </div>`;

  const input = document.getElementById('review-answer');
  input.focus();

  const submit = async () => {
    const answer = input.value.trim();
    if (!answer) return;
    document.getElementById('review-submit').disabled = true;
    input.disabled = true;

    const res = await fetch(`/api/vocab/${item.id}/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ answer }),
    });
    const data = await res.json().catch(() => ({}));

    const feedback = document.getElementById('review-feedback');
    if (res.ok) {
      feedback.innerHTML = data.correct
        ? `<p>✅ 答對了！下次複習：${data.interval_days} 天後。</p>`
        : `<p>❌ 答錯了，正確答案是 <strong>${escapeHtml(data.correct_answer)}</strong>。已重新排入近期複習。</p>`;
    } else {
      feedback.innerHTML = `<p>提交失敗：${escapeHtml(data.detail || res.status)}</p>`;
    }

    const nextBtn = document.createElement('button');
    nextBtn.textContent = current + 1 < queue.length ? '下一題' : '完成';
    nextBtn.className = 'secondary';
    nextBtn.addEventListener('click', () => {
      current += 1;
      if (current < queue.length) {
        renderQuestion();
      } else {
        renderDone();
      }
    });
    feedback.appendChild(nextBtn);
  };

  document.getElementById('review-submit').addEventListener('click', submit);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') submit();
  });
}

fetch('/api/vocab/review/queue')
  .then((r) => r.json())
  .then((data) => {
    queue = data;
    if (!queue.length) {
      renderDone();
    } else {
      renderQuestion();
    }
  });
