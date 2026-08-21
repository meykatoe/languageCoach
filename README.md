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
├── models.py            Question 資料表定義
├── schemas.py            Pydantic 請求/回應模型
├── seed.py               題庫 JSON 匯入腳本
├── routers/
│   ├── exams.py           GET /api/exams, /api/questions
│   ├── practice.py         POST /api/practice/submit (客觀題批改)
│   └── grading.py           POST /api/grading/writing, /speaking (AI 評分)
├── services/openai_service.py   OpenAI API 呼叫與評分規準
├── templates/            首頁 / 練習頁面 (Jinja2)
└── static/                app.js (題目渲染邏輯) / style.css

examQuestions/
├── create/               模擬題庫(依 TOEIC/IELTS/TOEFL 分資料夾,詳見其 README)
└── upload/                (預留給使用者上傳作答/題目用)
```

## 手動重新匯入題庫

```bash
python -m app.seed
```
