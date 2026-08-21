// Language Coach practice page logic.
// Renders whatever question shape comes back from /api/questions, collects
// objective answers for local grading, and wires up AI grading for
// writing/speaking style items.

const examSel = document.getElementById('f-exam');
const sectionSel = document.getElementById('f-section');
const partSel = document.getElementById('f-part');
const limitSel = document.getElementById('f-limit');
const startBtn = document.getElementById('start-btn');
const generateBtn = document.getElementById('generate-btn');
const generateStatus = document.getElementById('generate-status');
const quizArea = document.getElementById('quiz-area');

let examData = [];
let currentQuestions = [];

const generateBtnIcon = document.getElementById('generate-btn-icon');
if (generateBtnIcon && typeof iconHtml === 'function') generateBtnIcon.innerHTML = iconHtml('sparkle');

// Display-only Traditional Chinese labels for the filter dropdowns and the
// per-question meta breadcrumb. The underlying exam/section/part *values*
// stay in English (unchanged) since they're the actual filter/API values.
const SECTION_LABELS = {
  Reading: '閱讀',
  Listening: '聽力',
  Speaking: '口說',
  Writing: '寫作',
};

const PART_LABELS = {
  // TOEIC
  'Part 1: Photographs': 'Part 1:圖片描述',
  'Part 2: Question-Response': 'Part 2:應答問題',
  'Part 3: Conversations': 'Part 3:簡短對話',
  'Part 4: Talks': 'Part 4:簡短獨白',
  'Part 5: Incomplete Sentences': 'Part 5:單句填空',
  'Part 6: Text Completion': 'Part 6:段落填空',
  'Part 7: Reading Comprehension': 'Part 7:閱讀理解',
  // IELTS
  'Section 1: Form/Note Completion (everyday social context, e.g. phone conversation, booking)': 'Section 1:表格/筆記填空(日常對話情境)',
  'Section 2: Multiple Choice / Monologue in everyday context (e.g. talk about local facilities)': 'Section 2:選擇題/日常情境獨白',
  'Section 3: Matching / Discussion between two or more speakers in an educational context': 'Section 3:配對題/教育情境多人對話',
  'Section 4: Sentence Completion / Academic lecture (single speaker)': 'Section 4:句子填空/學術講座',
  'Matching Headings': '配對標題',
  'Multiple Choice': '選擇題',
  'Summary Completion': '摘要填空',
  'True / False / Not Given': '是非/未提及判斷',
  'Part 1: Introduction and Interview': 'Part 1:自我介紹與訪談',
  'Part 2: Individual Long Turn (Cue Card)': 'Part 2:個人長篇口說(提示卡)',
  'Part 3: Two-Way Discussion': 'Part 3:雙向討論',
  'Task 1 (Academic) - Describe visual data (chart/graph/table/diagram/process)': 'Task 1(學術類):圖表資料描述',
  'Task 1 (General Training) - Letter Writing': 'Task 1(一般訓練類):書信寫作',
  'Task 2 - Essay': 'Task 2:文章寫作',
  // TOEFL
  'Independent Task (Task 1) - Personal Choice/Opinion': '獨立題(Task 1):個人意見',
  'Integrated Tasks (Task 2-4) - Reading/Listening + Speaking': '整合題(Task 2-4):閱讀/聽力+口說',
  'Academic Discussion Task (Writing for an Academic Discussion)': '學術討論寫作題',
  'Integrated Task - Read, Listen, then Write': '整合寫作題(閱讀+聽力寫作)',
};

function localizedLabel(value, labelMap) {
  return (value && labelMap[value]) || value;
}

function uniq(arr) { return [...new Set(arr)]; }

function fillSelect(sel, values, placeholder, labelMap) {
  sel.innerHTML = `<option value="">${placeholder}</option>` +
    values.map(v => `<option value="${v}">${labelMap ? localizedLabel(v, labelMap) : v}</option>`).join('');
}

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

// The filter toolbar only exists on /practice. Guard its wiring so app.js
// can also be loaded on pages (like /review) that only need renderQuiz().
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

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  Object.entries(attrs).forEach(([k, v]) => {
    if (k === 'class') node.className = v;
    else if (k === 'html') node.innerHTML = v;
    else node.setAttribute(k, v);
  });
  (Array.isArray(children) ? children : [children]).forEach(c => {
    if (c) node.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
  });
  return node;
}

function renderOptionsBlock(idPrefix, options, container) {
  const wrap = el('div', { class: 'options' });
  options.forEach(opt => {
    const letter = opt.trim().charAt(0);
    const label = el('label', {}, [
      el('input', { type: 'radio', name: `q-${idPrefix}`, value: letter }),
      ' ' + opt,
    ]);
    wrap.appendChild(label);
  });
  container.appendChild(wrap);
}

const SPEAK_LABEL = '播放語音';

function addSpeakButton(text, container) {
  if (!('speechSynthesis' in window)) return;
  const btn = el('button', { class: 'secondary speak-btn', html: iconHtml('speaker') + SPEAK_LABEL });
  btn.addEventListener('click', () => {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'en-US';
    utterance.rate = 0.95;
    btn.disabled = true;
    btn.textContent = '播放中...';
    utterance.onend = utterance.onerror = () => {
      btn.disabled = false;
      btn.innerHTML = iconHtml('speaker') + SPEAK_LABEL;
    };
    window.speechSynthesis.speak(utterance);
  });
  container.appendChild(btn);
}

function renderSingleMC(item, container, notes) {
  const questionText = item.sentence || item.prompt || item.question || item.photoDescription || '(聽力題,請根據音檔/情境作答)';
  container.appendChild(el('p', {}, questionText));
  renderOptionsBlock(item.id, item.options, container);
  appendResultMarker(container, item.id, notes);
}

function renderSubQuestions(subQuestions, container, notes) {
  subQuestions.forEach(sq => {
    const block = el('div', { class: 'question-block' });
    block.appendChild(el('p', {}, sq.question || sq.text));
    if (sq.options) renderOptionsBlock(sq.id, sq.options, block);
    appendResultMarker(block, sq.id, notes);
    container.appendChild(block);
  });
}

function renderBlanks(blanks, container, notes) {
  blanks.forEach((b, i) => {
    const row = el('div', { class: 'question-block' });
    row.appendChild(el('p', {}, `空格 ${i + 1}${b.text ? ': ' + b.text : ''}`));
    if (b.options) {
      renderOptionsBlock(b.id, b.options, row);
    } else {
      row.appendChild(el('input', { type: 'text', 'data-blank-id': b.id, placeholder: '輸入答案' }));
    }
    appendResultMarker(row, b.id, notes);
    container.appendChild(row);
  });
}

function collectFreeTextAnswers(container) {
  const answers = [];
  container.querySelectorAll('input[data-blank-id]').forEach(inp => {
    answers.push({ source_id: inp.dataset.blankId, answer: inp.value });
  });
  container.querySelectorAll('select[data-blank-select]').forEach(sel => {
    answers.push({ source_id: sel.dataset.blankSelect, answer: sel.value });
  });
  return answers;
}

function collectRadioAnswers(container, idMap) {
  // idMap: array of {name, sourceId}
  const answers = [];
  idMap.forEach(({ name, sourceId }) => {
    const checked = container.querySelector(`input[name="${name}"]:checked`);
    answers.push({ source_id: sourceId, answer: checked ? checked.value : null });
  });
  return answers;
}

async function submitObjective(container, radioIdMap) {
  const answers = [
    ...collectRadioAnswers(container, radioIdMap),
    ...collectFreeTextAnswers(container),
  ];
  const res = await fetch('/api/practice/submit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ answers }),
  }).then(r => r.json());

  res.results.forEach(r => {
    const marker = container.querySelector(`[data-result-for="${r.source_id}"]`);
    if (marker) {
      if (r.correct === null) return;
      let html = r.correct ? '✓ 正確' : `✗ 錯誤 (正確答案: ${JSON.stringify(r.correctAnswer)})`;
      if (r.note) html += `<div class="review-note">AI 解析: ${r.note}</div>`;
      marker.innerHTML = html;
      marker.className = r.correct ? 'result-correct' : 'result-wrong';
    }
  });
  const summary = el('p', { class: 'summary-bar' }, `得分: ${res.correct} / ${res.graded}`);
  container.appendChild(summary);
}

// Appends a sub-question's result marker (and, if present, its AI review
// note) directly into that sub-question's own container, so the answer
// feedback shows up right below the question it belongs to instead of
// clustered together at the bottom of the whole card.
function appendResultMarker(container, id, notes = {}) {
  container.appendChild(el('div', { 'data-result-for': id }));
  if (notes[id]) {
    container.appendChild(el('div', { class: 'review-note' }, `AI 解析: ${notes[id]}`));
  }
}

function addMicButton(textarea, container) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) return;

  const MIC_LABEL_IDLE = '開始錄音口說';
  const MIC_LABEL_ACTIVE = '停止錄音';
  const micBtn = el('button', { class: 'secondary mic-btn', html: iconHtml('mic') + MIC_LABEL_IDLE });
  let recognition = null;
  let listening = false;

  micBtn.addEventListener('click', () => {
    if (listening) {
      recognition.stop();
      return;
    }
    recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.continuous = true;
    recognition.interimResults = true;

    const baseText = textarea.value ? textarea.value.trim() + ' ' : '';
    let finalText = '';

    recognition.onresult = (event) => {
      let interim = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcriptPart = event.results[i][0].transcript;
        if (event.results[i].isFinal) finalText += transcriptPart + ' ';
        else interim += transcriptPart;
      }
      textarea.value = baseText + finalText + interim;
    };
    recognition.onerror = () => {
      listening = false;
      micBtn.innerHTML = iconHtml('mic') + MIC_LABEL_IDLE;
    };
    recognition.onend = () => {
      listening = false;
      micBtn.innerHTML = iconHtml('mic') + MIC_LABEL_IDLE;
    };

    recognition.start();
    listening = true;
    micBtn.innerHTML = iconHtml('stop') + MIC_LABEL_ACTIVE;
  });

  container.appendChild(micBtn);
}

function renderAiGradeWidget(item, exam, skill, promptText, container) {
  const textarea = el('textarea', { placeholder: skill === 'writing' ? '在此輸入你的寫作內容...' : '在此輸入你的口說內容文字稿(可點擊下方麥克風直接開口說,或手動輸入)...' });
  const btn = el('button', { class: 'secondary' }, skill === 'writing' ? 'AI 批改我的寫作' : 'AI 批改我的口說');
  const feedbackEl = el('div', { class: 'feedback' });

  btn.addEventListener('click', async () => {
    btn.disabled = true;
    btn.textContent = '評分中...';
    try {
      const endpoint = skill === 'writing' ? '/api/grading/writing' : '/api/grading/speaking';
      const bodyKey = skill === 'writing' ? 'essay' : 'transcript';
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_id: item.id, exam, [bodyKey]: textarea.value }),
      });
      if (!res.ok) {
        const err = await res.json();
        feedbackEl.innerHTML = `<p class="result-wrong">評分失敗: ${err.detail || res.status}</p>`;
        return;
      }
      const fb = await res.json();
      feedbackEl.innerHTML = `
        <p class="score">分數: ${fb.score}</p>
        <p><strong>優點</strong></p><ul>${fb.strengths.map(s => `<li>${s}</li>`).join('')}</ul>
        <p><strong>待改進</strong></p><ul>${fb.weaknesses.map(s => `<li>${s}</li>`).join('')}</ul>
        <p><strong>建議</strong></p><ul>${fb.suggestions.map(s => `<li>${s}</li>`).join('')}</ul>
        ${fb.revisedExample ? `<p><strong>範例修改</strong>: ${fb.revisedExample}</p>` : ''}
      `;
    } finally {
      btn.disabled = false;
      btn.textContent = skill === 'writing' ? 'AI 批改我的寫作' : 'AI 批改我的口說';
    }
  });

  container.appendChild(el('p', {}, promptText));
  container.appendChild(textarea);
  if (skill === 'speaking') addMicButton(textarea, container);
  container.appendChild(btn);
  container.appendChild(feedbackEl);
}

const TRANSLATE_LABEL = '翻譯此題';

function addTranslateButton(q, container) {
  const btn = el('button', { class: 'secondary translate-btn', html: iconHtml('translate') + TRANSLATE_LABEL });
  const box = el('div', { class: 'translation-box', style: 'display:none' });
  let translation = null;

  btn.addEventListener('click', async () => {
    if (translation !== null) {
      box.style.display = box.style.display === 'none' ? 'block' : 'none';
      return;
    }
    btn.disabled = true;
    btn.textContent = '翻譯中...';
    try {
      const res = await fetch('/api/translate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_id: q.source_id }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        box.textContent = `翻譯失敗: ${data.detail || res.status}`;
      } else {
        translation = data.translation;
        box.textContent = translation;
      }
      box.style.display = 'block';
    } finally {
      btn.disabled = false;
      btn.innerHTML = iconHtml('translate') + TRANSLATE_LABEL;
    }
  });

  container.appendChild(btn);
  container.appendChild(box);
}

function renderItem(q, wrapper) {
  const item = q.content;
  const card = el('div', { class: 'card' });
  const aiTag = q.source_file === 'ai-generated' ? ' <span class="ai-tag">· AI 產生</span>' : '';
  const metaRow = el('div', { class: 'question-meta-row' });
  const sectionLabel = localizedLabel(q.section, SECTION_LABELS);
  const partLabel = q.part ? localizedLabel(q.part, PART_LABELS) : '';
  metaRow.appendChild(el('div', {
    class: 'question-meta',
    html: `${q.exam} / ${sectionLabel}${partLabel ? ' / ' + partLabel : ''}${aiTag}`,
  }));
  card.appendChild(metaRow);
  addTranslateButton(q, metaRow);

  const radioIdMap = [];
  const objectiveIds = [];

  const notes = q.reviewNotes || {};

  if (item.options && item.answer !== undefined) {
    renderSingleMC(item, card, notes);
    radioIdMap.push({ name: `q-${item.id}`, sourceId: item.id });
    objectiveIds.push(item.id);
  } else if (item.transcript && Array.isArray(item.questions)) {
    addSpeakButton(item.transcript, card);
    card.appendChild(el('div', { class: 'transcript' }, item.transcript));
    renderSubQuestions(item.questions, card, notes);
    item.questions.forEach(sq => { radioIdMap.push({ name: `q-${sq.id}`, sourceId: sq.id }); objectiveIds.push(sq.id); });
  } else if (item.passage && Array.isArray(item.questions) && typeof item.passage === 'string') {
    card.appendChild(el('div', { class: 'passage-text' }, (item.title ? item.title + '\n\n' : '') + item.passage));
    renderSubQuestions(item.questions, card, notes);
    item.questions.forEach(sq => { radioIdMap.push({ name: `q-${sq.id}`, sourceId: sq.id }); objectiveIds.push(sq.id); });
  } else if (Array.isArray(item.passage) && Array.isArray(item.questions)) {
    // TOEFL reading: passage is an array of paragraph strings
    card.appendChild(el('div', { class: 'passage-text' }, (item.title ? item.title + '\n\n' : '') + item.passage.join('\n\n')));
    renderSubQuestions(item.questions, card, notes);
    item.questions.forEach(sq => { radioIdMap.push({ name: `q-${sq.id}`, sourceId: sq.id }); objectiveIds.push(sq.id); });
  } else if (Array.isArray(item.passages) && Array.isArray(item.questions)) {
    item.passages.forEach(p => {
      card.appendChild(el('div', { class: 'passage-text' }, `[${p.label}]\n${p.text}`));
    });
    renderSubQuestions(item.questions, card, notes);
    item.questions.forEach(sq => { radioIdMap.push({ name: `q-${sq.id}`, sourceId: sq.id }); objectiveIds.push(sq.id); });
  } else if (item.text && Array.isArray(item.blanks)) {
    card.appendChild(el('div', { class: 'passage-text' }, item.text));
    renderBlanks(item.blanks, card, notes);
    item.blanks.forEach(b => { if (b.options) { radioIdMap.push({ name: `q-${b.id}`, sourceId: b.id }); } objectiveIds.push(b.id); });
  } else if (item.summary && Array.isArray(item.blanks)) {
    card.appendChild(el('div', { class: 'passage-text' }, (item.passage || '') + '\n\n---\n' + item.summary));
    renderBlanks(item.blanks, card, notes);
    item.blanks.forEach(b => objectiveIds.push(b.id));
  } else if (Array.isArray(item.statements)) {
    card.appendChild(el('div', { class: 'passage-text' }, item.passage || ''));
    item.statements.forEach(s => {
      const row = el('div', { class: 'question-block' });
      row.appendChild(el('p', {}, s.statement));
      ['TRUE', 'FALSE', 'NOT GIVEN'].forEach(opt => {
        row.appendChild(el('label', {}, [el('input', { type: 'radio', name: `q-${s.id}`, value: opt }), ' ' + opt]));
      });
      appendResultMarker(row, s.id, notes);
      card.appendChild(row);
      radioIdMap.push({ name: `q-${s.id}`, sourceId: s.id });
      objectiveIds.push(s.id);
    });
  } else if (Array.isArray(item.paragraphs) && Array.isArray(item.headingList)) {
    card.appendChild(el('div', { class: 'passage-text' }, item.headingList.join('\n')));
    item.paragraphs.forEach(p => {
      const row = el('div', { class: 'question-block' });
      row.appendChild(el('p', {}, `${p.label}: ${p.text}`));
      const sel = el('select', { 'data-blank-select': p.id });
      sel.appendChild(el('option', { value: '' }, '選擇標題'));
      item.headingList.forEach(h => {
        const value = h.split('.')[0].trim();
        sel.appendChild(el('option', { value }, h));
      });
      row.appendChild(sel);
      appendResultMarker(row, p.id, notes);
      card.appendChild(row);
      objectiveIds.push(p.id);
    });
  } else if (item.form && Array.isArray(item.form.fields)) {
    if (item.transcript) addSpeakButton(item.transcript, card);
    card.appendChild(el('div', { class: 'transcript' }, item.transcript || ''));
    card.appendChild(el('p', {}, item.form.title || ''));
    item.form.fields.forEach(f => {
      const row = el('div', { class: 'question-block' });
      row.appendChild(el('p', {}, f.label));
      row.appendChild(el('input', { type: 'text', 'data-blank-id': f.id, placeholder: '輸入答案' }));
      appendResultMarker(row, f.id, notes);
      card.appendChild(row);
      objectiveIds.push(f.id);
    });
  } else if (Array.isArray(item.sentences)) {
    if (item.transcript) addSpeakButton(item.transcript, card);
    card.appendChild(el('div', { class: 'transcript' }, item.transcript || ''));
    item.sentences.forEach(s => {
      const row = el('div', { class: 'question-block' });
      row.appendChild(el('p', {}, s.text));
      row.appendChild(el('input', { type: 'text', 'data-blank-id': s.id, placeholder: '輸入答案' }));
      appendResultMarker(row, s.id, notes);
      card.appendChild(row);
      objectiveIds.push(s.id);
    });
  } else if (Array.isArray(item.questions) && item.questions.every(x => typeof x === 'string')) {
    // IELTS speaking Part 1 (topic + question list) / Part 3 (topicGroups)
    card.appendChild(el('p', {}, item.topic || item.relatedCueCard || ''));
    const list = el('ul', {}, item.questions.map(qq => el('li', {}, qq)));
    card.appendChild(list);
    renderAiGradeWidget(item, q.exam, 'speaking', '請針對以上問題口頭作答(可貼上你的回答文字稿):', card);
  } else if (item.topic && Array.isArray(item.bulletPoints)) {
    card.appendChild(el('p', {}, item.topic));
    card.appendChild(el('ul', {}, item.bulletPoints.map(b => el('li', {}, b))));
    renderAiGradeWidget(item, q.exam, 'speaking', '請依提示卡口頭作答(可貼上你的回答文字稿):', card);
  } else if (item.prompt && (item.chartType || item.letterType || item.essayType)) {
    if (item.dataDescription) card.appendChild(el('p', { class: 'passage-text' }, item.dataDescription));
    renderAiGradeWidget(item, q.exam, 'writing', item.prompt, card);
  } else if (item.readingPassage || item.listeningTranscript || item.professorPrompt) {
    if (item.readingPassage) card.appendChild(el('div', { class: 'passage-text' }, '[閱讀] ' + item.readingPassage));
    if (item.listeningTranscript) {
      addSpeakButton(item.listeningTranscript, card);
      card.appendChild(el('div', { class: 'transcript' }, '[聽力文字稿] ' + item.listeningTranscript));
    }
    if (item.professorPrompt) card.appendChild(el('div', { class: 'passage-text' }, item.professorPrompt));
    if (Array.isArray(item.studentResponses)) {
      item.studentResponses.forEach(sr => card.appendChild(el('p', {}, `${sr.name}: ${sr.response}`)));
    }
    const skill = q.section === 'Writing' ? 'writing' : 'speaking';
    renderAiGradeWidget(item, q.exam, skill, item.prompt, card);
  } else if (item.prompt) {
    renderAiGradeWidget(item, q.exam, q.section === 'Writing' ? 'writing' : 'speaking', item.prompt, card);
  } else {
    card.appendChild(el('pre', {}, JSON.stringify(item, null, 2)));
  }

  wrapper.appendChild(card);
  return { radioIdMap, objectiveIds };
}

function renderQuiz(questions) {
  currentQuestions = questions;
  quizArea.innerHTML = '';
  if (!questions.length) {
    quizArea.appendChild(el('div', { class: 'card' }, '沒有符合條件的題目,請調整篩選條件。'));
    return;
  }
  const wrapper = el('div', {});
  let allRadioMap = [];
  questions.forEach(q => {
    const { radioIdMap } = renderItem(q, wrapper);
    allRadioMap = allRadioMap.concat(radioIdMap);
  });

  const submitBtn = el('button', {}, '送出客觀題答案');
  submitBtn.addEventListener('click', () => submitObjective(wrapper, allRadioMap));
  wrapper.appendChild(el('div', { class: 'card' }, [submitBtn]));

  quizArea.appendChild(wrapper);
}
