// /practice page bootstrap: the exam/section/part/limit filter toolbar,
// the "start" button that fetches questions, and the AI-generate button
// that adds freshly generated questions into the current practice list.
// Relies on renderQuiz()/currentQuestions from quiz-render.js.

const examSel = document.getElementById('f-exam');
const sectionSel = document.getElementById('f-section');
const partSel = document.getElementById('f-part');
const limitSel = document.getElementById('f-limit');
const startBtn = document.getElementById('start-btn');
const generateBtn = document.getElementById('generate-btn');
const generateStatus = document.getElementById('generate-status');

let examData = [];

const generateBtnIcon = document.getElementById('generate-btn-icon');
if (generateBtnIcon && typeof iconHtml === 'function') generateBtnIcon.innerHTML = iconHtml('sparkle');

function refreshSectionOptions() {
  const exam = examSel.value;
  const sections = uniq(examData.filter(r => !exam || r.exam === exam).map(r => r.section));
  fillSelect(sectionSel, sections, '類別', SECTION_LABELS);
  refreshPartOptions();
}

function refreshPartOptions() {
  const exam = examSel.value, section = sectionSel.value;
  const parts = uniq(
    examData
      .filter(r => (!exam || r.exam === exam) && (!section || r.section === section) && r.part)
      .map(r => r.part)
  );
  fillSelect(partSel, parts, '部分(可不選)', PART_LABELS);
}

// The filter toolbar only exists on /practice. Guard its wiring so this
// script can also be loaded on pages (like /review) that only need
// renderQuiz() from quiz-render.js.
if (examSel && sectionSel && partSel && limitSel && startBtn && generateBtn) {
  fetch('/api/exams').then(r => r.json()).then(rows => {
    examData = rows;
    fillSelect(examSel, uniq(rows.map(r => r.exam)), '考試');
    refreshSectionOptions();
  });

  examSel.addEventListener('change', refreshSectionOptions);
  sectionSel.addEventListener('change', refreshPartOptions);

  startBtn.addEventListener('click', async () => {
    const params = new URLSearchParams({ limit: limitSel.value });
    if (examSel.value) params.set('exam', examSel.value);
    if (sectionSel.value) params.set('section', sectionSel.value);
    if (partSel.value) params.set('part', partSel.value);
    const questions = await fetch('/api/questions?' + params.toString()).then(r => r.json());
    renderQuiz(questions);
  });

  generateBtn.addEventListener('click', async () => {
    if (!examSel.value || !sectionSel.value) {
      generateStatus.textContent = '請先選擇「考試」與「類別」再產生新題目。';
      return;
    }
    generateBtn.disabled = true;
    generateStatus.textContent = 'AI 出題中,請稍候...';
    try {
      const res = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          exam: examSel.value,
          section: sectionSel.value,
          part: partSel.value || null,
          count: 3,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        generateStatus.textContent = `出題失敗: ${err.detail || res.status}`;
        return;
      }
      const newQuestions = await res.json();
      generateStatus.textContent = `已產生 ${newQuestions.length} 題新題目,已加入下方練習列表。`;
      currentQuestions = currentQuestions.concat(newQuestions);
      renderQuiz(currentQuestions);
    } finally {
      generateBtn.disabled = false;
    }
  });
}
