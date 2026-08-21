from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

load_dotenv()

from app.database import Base, engine  # noqa: E402
from app.routers import exams, grading, practice  # noqa: E402
from app.seed import seed  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Language Coach")

Base.metadata.create_all(bind=engine)
seed(verbose=False)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

app.include_router(exams.router)
app.include_router(practice.router)
app.include_router(grading.router)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/practice", response_class=HTMLResponse)
def practice_page(request: Request):
    return templates.TemplateResponse(request, "practice.html")


@app.get("/health")
def health():
    return {"status": "ok"}
