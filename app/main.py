from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

load_dotenv()

from app.database import Base, engine, migrate_schema  # noqa: E402
from app.routers import (  # noqa: E402
    exams,
    generate,
    grading,
    history,
    practice,
    review,
    settings,
    translate,
    upload,
)
from app.seed import seed  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Language Coach")

Base.metadata.create_all(bind=engine)
migrate_schema()
seed(verbose=False)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

app.include_router(exams.router)
app.include_router(practice.router)
app.include_router(grading.router)
app.include_router(history.router)
app.include_router(generate.router)
app.include_router(review.router)
app.include_router(settings.router)
app.include_router(translate.router)
app.include_router(upload.router)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/practice", response_class=HTMLResponse)
def practice_page(request: Request):
    return templates.TemplateResponse(request, "practice.html")


@app.get("/history", response_class=HTMLResponse)
def history_page(request: Request):
    return templates.TemplateResponse(request, "history.html")


@app.get("/review", response_class=HTMLResponse)
def review_page(request: Request):
    return templates.TemplateResponse(request, "review.html")


@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    return templates.TemplateResponse(request, "settings.html")


@app.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    return templates.TemplateResponse(request, "upload.html")


@app.get("/health")
def health():
    return {"status": "ok"}
