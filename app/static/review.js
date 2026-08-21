// Loads questions the user has previously answered incorrectly and reuses
// app.js's renderQuiz()/renderItem() to display and re-grade them. Also
// wires up the "review mode" toggle, which withholds previously recorded
// AI notes so the user can re-attempt a question without seeing spoilers.

const reviewModeCheckbox = document.getElementById('review-mode-checkbox');
const intro = document.getElementById('review-intro');

function introText(reviewMode, count) {
  if (!count) {
    return '目前沒有需要複習的錯題,先到練習頁面作答一些客觀題吧!';
  }
  if (reviewMode) {
    return `複習模式已啟用:以下是你最近答錯的 ${count} 組題目(AI 先前的提示已隱藏),再試一次吧。送出答案後 AI 會依這次的表現給你新的講評。`;
  }
  return `以下是你最近答錯的 ${count} 組題目,再試一次吧。`;
}

async function loadReview() {
  const [settings, questions] = await Promise.all([
    fetch('/api/settings').then(r => r.json()),
    fetch('/api/review?limit=20').then(r => r.json()),
  ]);
  reviewModeCheckbox.checked = !!settings.review_mode;
  intro.textContent = introText(settings.review_mode, questions.length);
  if (questions.length) renderQuiz(questions);
}

reviewModeCheckbox.addEventListener('change', async () => {
  reviewModeCheckbox.disabled = true;
  try {
    await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ review_mode: reviewModeCheckbox.checked }),
    });
    await loadReview();
  } finally {
    reviewModeCheckbox.disabled = false;
  }
});

loadReview();
