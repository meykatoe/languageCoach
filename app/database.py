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

    if "vocab_entries" in inspector.get_table_names():
        columns = {col["name"] for col in inspector.get_columns("vocab_entries")}
        with engine.begin() as conn:
            if "interval_days" not in columns:
                conn.execute(text("ALTER TABLE vocab_entries ADD COLUMN interval_days INTEGER DEFAULT 0"))
            if "ease_factor" not in columns:
                conn.execute(text("ALTER TABLE vocab_entries ADD COLUMN ease_factor FLOAT DEFAULT 2.5"))
            if "repetitions" not in columns:
                conn.execute(text("ALTER TABLE vocab_entries ADD COLUMN repetitions INTEGER DEFAULT 0"))
            if "next_review_at" not in columns:
                conn.execute(text("ALTER TABLE vocab_entries ADD COLUMN next_review_at DATETIME"))
            if "user_id" not in columns:
                conn.execute(text("ALTER TABLE vocab_entries ADD COLUMN user_id INTEGER"))
                # `word` was globally unique pre-multi-user; now it's unique
                # per (user_id, word), so two users can each save the same
                # word. Replace the old single-column unique index.
                conn.execute(text("DROP INDEX IF EXISTS ix_vocab_entries_word"))
                conn.execute(text("CREATE INDEX ix_vocab_entries_word ON vocab_entries (word)"))
                conn.execute(
                    text(
                        "CREATE UNIQUE INDEX uq_vocab_entries_user_word "
                        "ON vocab_entries (user_id, word)"
                    )
                )

    # Multi-user support: attach an owning user_id to previously single-owner
    # tables. Existing rows are left NULL here; the first account ever
    # registered claims them (see app/routers/auth.py _claim_orphaned_data).
    for table, index_sql in (
        ("attempts", "CREATE INDEX ix_attempts_user_id ON attempts (user_id)"),
        ("exam_sessions", "CREATE INDEX ix_exam_sessions_user_id ON exam_sessions (user_id)"),
        ("questions", "CREATE INDEX ix_questions_user_id ON questions (user_id)"),
        ("app_settings", "CREATE UNIQUE INDEX ix_app_settings_user_id ON app_settings (user_id)"),
    ):
        if table not in inspector.get_table_names():
            continue
        columns = {col["name"] for col in inspector.get_columns(table)}
        if "user_id" not in columns:
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER"))
                conn.execute(text(index_sql))

    # Google login: users may not have an email/google_sub if they registered
    # with a username/password before this was added.
    if "users" in inspector.get_table_names():
        columns = {col["name"] for col in inspector.get_columns("users")}
        with engine.begin() as conn:
            if "email" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR"))
                conn.execute(text("CREATE UNIQUE INDEX ix_users_email ON users (email)"))
            if "google_sub" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN google_sub VARCHAR"))
                conn.execute(text("CREATE UNIQUE INDEX ix_users_google_sub ON users (google_sub)"))
