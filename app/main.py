from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

load_dotenv()

from app.logging_config import setup_logging  # noqa: E402

setup_logging()

from app.database import Base, SessionLocal, engine, migrate_schema  # noqa: E402
from app.dependencies import NotAuthenticated, get_current_user  # noqa: E402
from app.models import User  # noqa: E402
from app.routers import (  # noqa: E402
    auth,
    exams,
    generate,
    grading,
    history,
    image,
    mock_exam,
    practice,
    review,
    settings,
    translate,
    tts,
    upload,
    vocab,
)
from app.seed import seed  # noqa: E402
from app.services.crypto import migrate_legacy_plaintext_key  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Language Coach")

Base.metadata.create_all(bind=engine)
migrate_schema()

_db = SessionLocal()
try:
    migrate_legacy_plaintext_key(_db)
finally:
    _db.close()

seed(verbose=False)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.exception_handler(NotAuthenticated)
def handle_not_authenticated(request: Request, exc: NotAuthenticated):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "尚未登入。"}, status_code=401)
    return RedirectResponse(f"/login?next={request.url.path}")


app.include_router(auth.router)
app.include_router(exams.router)
app.include_router(practice.router)
app.include_router(grading.router)
app.include_router(history.router)
app.include_router(generate.router)
app.include_router(review.router)
app.include_router(settings.router)
app.include_router(translate.router)
app.include_router(tts.router)
app.include_router(image.router)
app.include_router(mock_exam.router)
app.include_router(upload.router)
app.include_router(vocab.router)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html")


@app.get("/", response_class=HTMLResponse)
def index(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse(request, "index.html")


@app.get("/practice", response_class=HTMLResponse)
def practice_page(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse(request, "practice.html")


@app.get("/mock-exam", response_class=HTMLResponse)
def mock_exam_page(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse(request, "mock-exam.html")


@app.get("/history", response_class=HTMLResponse)
def history_page(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse(request, "history.html")


@app.get("/review", response_class=HTMLResponse)
def review_page(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse(request, "review.html")


@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse(request, "settings.html")


@app.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse(request, "upload.html")


@app.get("/vocab", response_class=HTMLResponse)
def vocab_page(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse(request, "vocab.html")


@app.get("/vocab/review", response_class=HTMLResponse)
def vocab_review_page(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse(request, "vocab-review.html")


@app.get("/health")
def health():
    return {"status": "ok"}
