// Renders whatever question shape comes back from /api/questions (or
// /api/generate, /api/mock-exam, /api/upload), collects objective answers
// for local grading, and wires up AI grading for writing/speaking style
// items. Shared by the practice, review, upload and mock-exam pages.

const quizArea = document.getElementById('quiz-area');
let currentQuestions = [];

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

function renderSingleMC(item, container, notes) {
  const questionText = item.sentence || item.prompt || item.question || '(聽力題,請根據音檔/情境作答)';
  if (item.photoDescription) {
    addPhotoImage(item.photoDescription, container);
  } else {
    container.appendChild(el('p', {}, questionText));
  }
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
  container.querySelectorAll('.transcript').forEach(t => { t.style.display = 'block'; });
  container.querySelectorAll('.transcript-hint').forEach(h => { h.style.display = 'none'; });

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
    card.appendChild(el('p', { class: 'transcript-hint' }, '(送出答案後顯示聽力文字稿)'));
    card.appendChild(el('div', { class: 'transcript', style: 'display:none' }, item.transcript));
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
    if (item.transcript) card.appendChild(el('p', { class: 'transcript-hint' }, '(送出答案後顯示聽力文字稿)'));
    card.appendChild(el('div', { class: 'transcript', style: 'display:none' }, item.transcript || ''));
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
    if (item.transcript) card.appendChild(el('p', { class: 'transcript-hint' }, '(送出答案後顯示聽力文字稿)'));
    card.appendChild(el('div', { class: 'transcript', style: 'display:none' }, item.transcript || ''));
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
