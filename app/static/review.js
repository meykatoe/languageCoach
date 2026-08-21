// Loads questions the user has previously answered incorrectly and reuses
// app.js's renderQuiz()/renderItem() to display and re-grade them.

fetch('/api/review?limit=20').then(r => r.json()).then(questions => {
  const intro = document.getElementById('review-intro');
  if (!questions.length) {
    intro.textContent = '目前沒有需要複習的錯題,先到練習頁面作答一些客觀題吧!';
    return;
  }
  intro.textContent = `以下是你最近答錯的 ${questions.length} 組題目,再試一次吧。`;
  renderQuiz(questions);
});
