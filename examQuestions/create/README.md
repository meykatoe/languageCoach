# 題庫說明 (Pre-generated Exam Questions)

此資料夾存放依 TOEIC / IELTS / TOEFL 三大考試分別建立的模擬題庫，供 Language Coach 應用程式匯入使用。所有題目皆為原創仿真內容(模仿官方考試題型與難度撰寫)，並非真實考古題。

## 資料夾結構

```
examQuestions/create/
├── TOEIC/
│   ├── listening/
│   │   ├── part1_photographs.json        (Part 1: 照片描述, 10 題)
│   │   ├── part2_question_response.json  (Part 2: 應答問題, 15 題)
│   │   ├── part3_conversations.json      (Part 3: 簡短對話, 5 篇 x 3 題)
│   │   └── part4_talks.json              (Part 4: 簡短獨白, 5 篇 x 3 題)
│   └── reading/
│       ├── part5_incomplete_sentences.json   (Part 5: 句子填空, 15 題)
│       ├── part6_text_completion.json        (Part 6: 短文填空, 3 篇 x 4 題)
│       └── part7_reading_comprehension.json  (Part 7: 單篇/雙篇/三篇閱讀理解)
│
├── IELTS/
│   ├── listening/
│   │   ├── section1_form_completion.json   (Section 1: 表格/筆記填空)
│   │   ├── section2_multiple_choice.json   (Section 2: 選擇題)
│   │   ├── section3_matching.json          (Section 3: 配對/多人對話)
│   │   └── section4_sentence_completion.json (Section 4: 學術講座句子填空)
│   ├── reading/
│   │   ├── multiple_choice.json
│   │   ├── true_false_not_given.json
│   │   ├── matching_headings.json
│   │   └── summary_completion.json
│   ├── writing/
│   │   ├── task1_academic.json   (學術版 Task 1: 圖表描述)
│   │   ├── task1_general.json    (一般訓練版 Task 1: 書信寫作)
│   │   └── task2_essay.json      (Task 2: 議論文)
│   └── speaking/
│       ├── part1_introduction.json  (Part 1: 個人問答)
│       ├── part2_cue_card.json      (Part 2: 話題卡)
│       └── part3_discussion.json    (Part 3: 延伸討論, 對應 Part 2 話題)
│
└── TOEFL/
    ├── reading/
    │   └── passage_questions.json   (含 factual / vocabulary / inference / insertion / prose summary 題型)
    ├── listening/
    │   └── lecture_conversation.json (校園對話 + 學術講座)
    ├── speaking/
    │   ├── independent_tasks.json   (Task 1: 個人意見)
    │   └── integrated_tasks.json    (Task 2-4: 閱讀/聽力整合口說)
    └── writing/
        ├── integrated_task.json           (閱讀+聽力整合寫作)
        └── academic_discussion_task.json  (學術討論寫作, 新版 TOEFL 題型)
```

## 資料格式

每個 JSON 檔案皆包含 `exam`、`section`、`part`/`instructions` 等中繼資料，題目本體依題型不同而有不同的巢狀結構(例如單題陣列 `questions`、篇章陣列 `passages`/`conversations`/`talks`，或表單/摘要填空使用 `fields`/`blanks`)。所有題目皆含有 `id` 欄位，方便未來資料庫匯入與追蹤作答紀錄。

聽力題型的音檔目前以 `transcript` 文字腳本表示；後續可將 `transcript` 交由 TTS (例如 OpenAI TTS API) 產生對應音檔，或在前端直接以文字轉語音方式播放。

## 後續規劃

此為系統第一階段的靜態題庫。後續開發 Python + OpenAI API 服務時，可以：
1. 將題目匯入資料庫(如 SQLite/PostgreSQL)，供出題引擎隨機抽題、依難度分級。
2. 使用 OpenAI API 動態生成更多變化題目，並以此題庫作為 few-shot 範例，確保格式與難度一致。
3. 針對寫作與口說題型，串接 OpenAI API 進行自動評分與回饋(對應 `examQuestions/upload` 使用者作答上傳)。
