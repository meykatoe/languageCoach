import os
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = Path(os.environ["LANGCOACH_DB_PATH"]) if os.environ.get("LANGCOACH_DB_PATH") else DATA_DIR / "app.db"

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def migrate_schema() -> None:
    """Lightweight in-place migration for columns added after the table was
    first created (this project has no data/rows worth an Alembic setup).
    """
    inspector = inspect(engine)
    if "app_settings" in inspector.get_table_names():
        columns = {col["name"] for col in inspector.get_columns("app_settings")}
        if "review_mode" not in columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE app_settings ADD COLUMN review_mode BOOLEAN DEFAULT 0"))

    if "exam_sessions" in inspector.get_table_names():
        columns = {col["name"] for col in inspector.get_columns("exam_sessions")}
        if "advice" not in columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE exam_sessions ADD COLUMN advice VARCHAR"))
