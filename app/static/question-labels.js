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
