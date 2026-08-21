# Language Coach

以 Python (FastAPI) + OpenAI API 打造的網頁版智慧語言教練，提供 TOEIC / IELTS /
TOEFL 模擬題練習：客觀題(選擇題、填空、配對等)自動批改，寫作與口說(文字稿)
則由 OpenAI API 依各考試評分規準給出分數與回饋。

## 快速開始

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# 編輯 .env，填入 OPENAI_API_KEY(寫作/口說 AI 評分功能需要；客觀題練習不需要)

uvicorn app.main:app --reload
```

啟動後開啟 http://127.0.0.1:8000 即可使用。伺服器啟動時會自動將
`examQuestions/create/` 底下的題庫 JSON 匯入 SQLite (`data/app.db`)。

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
│   └── generate.py            POST /api/generate (AI 動態出題)
├── services/openai_service.py   OpenAI API 呼叫與評分規準
├── templates/            首頁 / 練習頁面 / 學習紀錄頁面 (Jinja2)
└── static/                app.js (題目渲染+語音播放/口說語音輸入) / history.js / style.css

examQuestions/
├── create/               模擬題庫(依 TOEIC/IELTS/TOEFL 分資料夾,詳見其 README)
└── upload/                (預留給使用者上傳作答/題目用)

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
- 練習頁面提供「🤖 AI 產生新題目」按鈕：選定考試+類別(部分可選)後，以現有
  題庫中一題作為「格式範本」(僅取其 JSON 結構,不取其內容)，呼叫 OpenAI API
  產生全新原創題目並加入當次練習列表，同時存入資料庫(`source_file` 標記為
  `ai-generated`)供之後練習抽題使用。

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
