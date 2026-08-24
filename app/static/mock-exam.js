// TOEIC "正式模考" (full mock exam) page logic: starts a timed session via
// /api/mock-exam, reuses app.js's renderItem()/collect*Answers() to render
// and collect each section's questions, runs a countdown per section, and
// auto-submits when time runs out.

const STORAGE_KEY = 'mockExamSessionId';

const introEl = document.getElementById('mock-exam-intro');
const statusEl = document.getElementById('mock-exam-status');
const modeSel = document.getElementById('mock-exam-mode');
const startBtn = document.getElementById('mock-exam-start-btn');
const timerBar = document.getElementById('mock-exam-timer-bar');
const timerEl = document.getElementById('mock-exam-timer');
const sectionLabelEl = document.getElementById('mock-exam-section-label');
const progressNoteEl = document.getElementById('mock-exam-progress-note');
const submitBtn = document.getElementById('mock-exam-submit-btn');
const areaEl = document.getElementById('mock-exam-area');
const resultEl = document.getElementById('mock-exam-result');

let sessionId = null;
let currentSection = null; // "Listening" | "Reading"
let currentRadioIdMap = [];
let timerInterval = null;
let submitting = false;

const SECTION_LABEL_ZH = { Listening: '聽力測驗', Reading: '閱讀測驗' };

function fmtRemaining(ms) {
  const totalSec = Math.max(0, Math.floor(ms / 1000));
  const m = String(Math.floor(totalSec / 60)).padStart(2, '0');
  const s = String(totalSec % 60).padStart(2, '0');
  return `${m}:${s}`;
}

function parseDeadline(iso) {
  return new Date(iso + 'Z');
}

function stopTimer() {
  if (timerInterval) clearInterval(timerInterval);
  timerInterval = null;
}

function startTimer(deadlineIso, onExpire) {
  stopTimer();
  const deadline = parseDeadline(deadlineIso);
  const tick = () => {
    const remaining = deadline.getTime() - Date.now();
    timerEl.textContent = fmtRemaining(remaining);
    timerEl.classList.toggle('mock-exam-timer-low', remaining <= 5 * 60 * 1000);
    if (remaining <= 0) {
      stopTimer();
      onExpire();
    }
  };
  tick();
  timerInterval = setInterval(tick, 1000);
}

function renderSection(section, questions) {
  areaEl.innerHTML = '';
  currentRadioIdMap = [];
  const wrapper = el('div', {});
  questions.forEach(q => {
    const { radioIdMap } = renderItem(q, wrapper);
    currentRadioIdMap = currentRadioIdMap.concat(radioIdMap);
  });
  areaEl.appendChild(wrapper);
  sectionLabelEl.textContent = SECTION_LABEL_ZH[section] || section;
  progressNoteEl.textContent = `共 ${questions.length} 大題,時間到會自動送出`;
  timerBar.style.display = 'flex';
}

function collectSectionAnswers() {
  return [
    ...collectRadioAnswers(areaEl, currentRadioIdMap),
    ...collectFreeTextAnswers(areaEl),
  ];
}

async function submitCurrentSection() {
  if (submitting || !sessionId) return;
  submitting = true;
  submitBtn.disabled = true;
  stopTimer();

  const answers = collectSectionAnswers();
  const endpoint = currentSection === 'Listening'
    ? `/api/mock-exam/${sessionId}/submit-listening`
    : `/api/mock-exam/${sessionId}/submit-reading`;

  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ answers }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      statusEl.textContent = `送出失敗: ${err.detail || res.status}`;
      submitting = false;
      submitBtn.disabled = false;
      return;
    }
    const data = await res.json();
    if (currentSection === 'Listening') {
      currentSection = 'Reading';
      renderSection('Reading', data.reading.questions);
      startTimer(data.reading.deadline, submitCurrentSection);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      showResult(data);
    }
  } finally {
    submitting = false;
    submitBtn.disabled = false;
  }
}

function scoreRow(labelText, score) {
  return el('div', { class: 'mock-exam-score-row' }, [
    el('span', {}, labelText),
    el('strong', {}, `${score.raw_correct} / ${score.raw_total} 題正確　→　約 ${score.scaled_score} 分`),
  ]);
}

function showResult(result) {
  timerBar.style.display = 'none';
  areaEl.innerHTML = '';
  localStorage.removeItem(STORAGE_KEY);

  resultEl.innerHTML = '';
  resultEl.appendChild(el('h2', {}, 'TOEIC 正式模考結果'));
  resultEl.appendChild(scoreRow('聽力(Listening)', result.listening));
  resultEl.appendChild(scoreRow('閱讀(Reading)', result.reading));
  resultEl.appendChild(el('p', { class: 'mock-exam-total' }, `總分約 ${result.scaled_total} / 990`));
  resultEl.appendChild(el('p', { class: 'question-meta' }, result.disclaimer));

  if (result.advice) {
    const adviceBox = el('div', { class: 'mock-exam-advice' }, [
      el('h3', {}, 'AI 學習建議'),
      el('p', {}, result.advice),
    ]);
    resultEl.appendChild(adviceBox);
  }

  const retryBtn = el('button', { class: 'secondary' }, '再考一次');
  retryBtn.addEventListener('click', () => location.reload());
  resultEl.appendChild(retryBtn);

  resultEl.style.display = 'block';
}

function startExamUI(section, sectionPayload) {
  introEl.style.display = 'none';
  resultEl.style.display = 'none';
  currentSection = section;
  renderSection(section, sectionPayload.questions);
  startTimer(sectionPayload.deadline, submitCurrentSection);
}

startBtn.addEventListener('click', async () => {
  startBtn.disabled = true;
  statusEl.textContent = modeSel.value === 'ai_generated'
    ? 'AI 正在生成完整考卷,這可能需要一段時間,請稍候...'
    : '正在組卷,請稍候...';
  try {
    const res = await fetch('/api/mock-exam/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ exam: 'TOEIC', mode: modeSel.value }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      statusEl.textContent = `無法開始模考: ${err.detail || res.status}`;
      return;
    }
    const data = await res.json();
    sessionId = data.id;
    localStorage.setItem(STORAGE_KEY, String(sessionId));
    startExamUI('Listening', data.listening);
  } finally {
    startBtn.disabled = false;
  }
});

submitBtn.addEventListener('click', () => {
  if (confirm('確定要提前交卷嗎?尚未作答的題目將視為未答對。')) {
    submitCurrentSection();
  }
});

async function tryResume() {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (!stored) return;
  const res = await fetch(`/api/mock-exam/${stored}`);
  if (!res.ok) {
    localStorage.removeItem(STORAGE_KEY);
    return;
  }
  const data = await res.json();
  sessionId = data.id;
  if (data.status === 'completed') {
    introEl.style.display = 'none';
    showResult(data.result);
  } else if (data.status === 'listening') {
    startExamUI('Listening', data.listening);
  } else if (data.status === 'reading') {
    startExamUI('Reading', data.reading);
  }
}

tryResume();
