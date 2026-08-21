# Language Coach

以 Python (FastAPI) + OpenAI API 打造的網頁版智慧語言教練，提供 TOEIC / IELTS /
TOEFL 模擬題練習：客觀題(選擇題、填空、配對等)自動批改，寫作與口說(文字稿)
則由 OpenAI API 依各考試評分規準給出分數與回饋。

## 快速開始

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --reload
```

啟動後開啟 http://127.0.0.1:8000 即可使用。伺服器啟動時會自動將
`examQuestions/create/` 底下的題庫 JSON 匯入 SQLite (`data/app.db`)。

客觀題練習(選擇題/填空等)不需要 API Key 就能用。若要使用寫作/口說 AI 評分
或 AI 動態出題功能，點網頁右上角的 ⚙️ 進入 `/settings` 頁面直接貼上 OpenAI
API Key 並按「🔌 測試連線」確認即可,不需要編輯後端檔案。(也可以改用
`cp .env.example .env` 編輯 `OPENAI_API_KEY`／`OPENAI_MODEL` 的方式設定；
`/settings` 頁面存的值優先生效。)

## 專案結構

```
app/
├── main.py            FastAPI 進入點,掛載路由與樣板
├── database.py         SQLAlchemy engine/session
├── models.py            Question / Attempt 資料表定義
├── schemas.py            Pydantic 請求/回應模型
├── seed.py               題庫 JSON 匯入腳本
├── routers/
│   ├── exams.py           GET /api/exams, /api/questions
│   ├── practice.py         POST /api/practice/submit (客觀題批改+寫入紀錄)
│   ├── grading.py           POST /api/grading/writing, /speaking (AI 評分+寫入紀錄)
│   ├── history.py            GET /api/history (學習進度統計)
│   ├── generate.py            POST /api/generate (AI 動態出題)
│   ├── review.py               GET /api/review (錯題複習清單)
│   ├── settings.py              GET/POST /api/settings, /api/settings/test
│   └── upload.py                 POST /api/upload (上傳檔案 + AI 出相似題)
├── services/
│   ├── openai_service.py         OpenAI API 呼叫、評分規準、出題 prompt
│   └── file_extract.py            PDF/DOCX/TXT 文字擷取
├── templates/            首頁 / 練習頁面 / 學習紀錄頁面 (Jinja2)
└── static/                app.js (題目渲染+語音播放/口說語音輸入) / history.js / style.css

examQuestions/
├── create/               模擬題庫(依 TOEIC/IELTS/TOEFL 分資料夾,詳見其 README)
└── upload/                (預留目錄,目前未使用——使用者上傳的檔案只在記憶體中
                            解析，不會寫入磁碟，詳見下方「上傳出題」說明)

tests/                  pytest 測試套件 (API 端點、題庫匯入完整性)
```

## 功能一覽

- 客觀題(選擇題/填空/配對/T-F-NG)自動批改,並記錄到學習紀錄。
- 寫作與口說由 OpenAI API 依考試評分規準(IELTS 級分 / TOEFL 0-5 分 / TOEIC)評分。
- 聽力題目提供「🔊 播放語音」按鈕(瀏覽器 Web Speech API TTS)。
- 口說題目提供「🎙️ 開始錄音口說」按鈕(瀏覽器 Web Speech API STT,自動轉文字稿),
  僅 Chrome/Edge 等支援 `SpeechRecognition` 的瀏覽器可用,不支援時按鈕不會出現,
  仍可手動輸入文字稿。
- `/history` 頁面顯示累計作答數、各考試/類別正確率與最近作答紀錄。
- `/review` 錯題複習頁面：根據作答紀錄找出「最近一次作答仍然答錯」的客觀題,
  彙整成一份複習清單重新練習；一旦該題後來被答對,就會自動從複習清單移除。
- 練習頁面提供「🤖 AI 產生新題目」按鈕：選定考試+類別(部分可選)後，以現有
  題庫中一題作為「格式範本」(僅取其 JSON 結構,不取其內容)，呼叫 OpenAI API
  產生全新原創題目並加入當次練習列表，同時存入資料庫(`source_file` 標記為
  `ai-generated`)供之後練習抽題使用。
- `/settings` 設定頁：可直接在網頁設定 OpenAI API Key 與模型(儲存在後端本機
  SQLite,不會外流),並提供「測試連線」按鈕即時驗證金鑰是否有效。
- `/upload` 上傳出題頁：上傳自己的 PDF、Word(.docx)或 TXT 檔案(10MB 以內),
  AI 會分析檔案內容判斷合適的題型(選擇題/文章閱讀/填空/寫作或口說提示),
  並依指定數量(1-10 題)產生全新原創的相似題目。檔案內容僅在該次請求中於
  記憶體解析、傳給 OpenAI API,伺服器不會保存原始檔案；產生的題目會存入
  資料庫(`source_file` 標記為 `user-upload`),之後在練習頁選擇對應「分類
  名稱」即可繼續練習。舊版 .doc(非 .docx)Word 格式不支援。

## 手動重新匯入題庫

```bash
python -m app.seed
```

## 執行測試

```bash
pip install -r requirements.txt   # 已包含 pytest
pytest
```

測試會使用暫存資料庫(不會動到 `data/app.db`),涵蓋 API 端點行為，以及一項
回歸測試：確保 `examQuestions/create/` 中每個 JSON 檔案裡任何一個「題目清單」
欄位都有被 `app/seed.py` 的 `ITEM_LIST_KEYS` 涵蓋到(避免像先前 TOEFL
`lectures` 欄位被漏匯入的問題再次發生)。
