import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)

from app.database import Base


class User(Base):
    """An account. Every other per-user table (Attempt, ExamSession,
    VocabEntry, AppSetting, and any AI-generated/uploaded Question) is
    scoped to a user via a `user_id` foreign key.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    email = Column(String, nullable=True, unique=True, index=True)
    google_sub = Column(String, nullable=True, unique=True, index=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
        index=True,
    )


class UserSession(Base):
    """A logged-in session, identified by an opaque token stored in an
    httponly cookie. Fixed expiry, no sliding refresh.
    """

    __tablename__ = "user_sessions"

    token = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
        index=True,
    )
    expires_at = Column(DateTime, nullable=False, index=True)


class Question(Base):
    """One practice item (a single question, a conversation, a passage, a
    cue card, a writing prompt, ...). The full original JSON object is kept
    in `content` so the frontend can render any shape without the backend
    needing a table per question type.

    `user_id` is null for the shared seed bank (imported from
    `examQuestions/create/`); it's set to the owning user for AI-generated
    (`source_file == "ai-generated"`) or uploaded
    (`source_file == "user-upload"`) content, which is private to them.
    """

    __tablename__ = "questions"
    __table_args__ = (UniqueConstraint("source_id", name="uq_question_source_id"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    source_id = Column(String, nullable=False, index=True)
    exam = Column(String, nullable=False, index=True)
    section = Column(String, nullable=False, index=True)
    part = Column(String, nullable=True, index=True)
    qtype = Column(String, nullable=False, index=True)
    source_file = Column(String, nullable=False)
    content = Column(JSON, nullable=False)


class Attempt(Base):
    """A record of one graded answer, objective or AI-graded, so practice
    history and progress can be shown to the user over time.
    """

    __tablename__ = "attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
        index=True,
    )
    exam = Column(String, nullable=False, index=True)
    section = Column(String, nullable=False, index=True)
    part = Column(String, nullable=True)
    source_id = Column(String, nullable=False, index=True)
    item_type = Column(String, nullable=False)  # "objective" | "writing" | "speaking"
    is_correct = Column(Boolean, nullable=True)  # objective only
    score = Column(String, nullable=True)  # AI-graded score/band, as text
    detail = Column(JSON, nullable=True)  # correctAnswer/submittedAnswer or full AI feedback


class ExamSession(Base):
    """One full timed mock-exam sitting (currently TOEIC): a fixed,
    real-exam-shaped set of questions assembled up front and stored in
    `content`, graded section-by-section as the user submits Listening then
    Reading within their time limits.
    """

    __tablename__ = "exam_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    exam = Column(String, nullable=False, index=True)
    mode = Column(String, nullable=False)  # "bank" | "ai_generated"
    status = Column(String, nullable=False, default="listening")  # listening|reading|completed
    created_at = Column(
        DateTime,
        default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
        index=True,
    )
    listening_deadline = Column(DateTime, nullable=True)
    reading_deadline = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)

    # {"Listening": [{"part", "qtype", "item"}, ...], "Reading": [...]}
    content = Column(JSON, nullable=False)

    raw_listening = Column(Integer, nullable=True)
    raw_listening_total = Column(Integer, nullable=True)
    raw_reading = Column(Integer, nullable=True)
    raw_reading_total = Column(Integer, nullable=True)
    scaled_listening = Column(Integer, nullable=True)
    scaled_reading = Column(Integer, nullable=True)
    scaled_total = Column(Integer, nullable=True)

    # list of GradedAnswer-shaped dicts, filled in once each section is graded
    listening_results = Column(JSON, nullable=True)
    reading_results = Column(JSON, nullable=True)

    # AI-generated study advice based on this sitting's results, filled in
    # once the reading section (and thus the whole exam) is submitted
    advice = Column(String, nullable=True)


class VocabEntry(Base):
    """A word the user selected for translation, auto-saved into their
    personal vocabulary book. `detail` holds a full dictionary-style entry
    (definitions per part of speech, examples, synonyms, etc., generated
    once via OpenAI in the style of the Oxford Learner's Dictionary) so the
    word can be revisited to memorize it properly, not just glanced at once.
    `detail` is null while generation is pending or has failed; the
    /api/vocab/{id}/regenerate endpoint lets the user retry it.
    """

    __tablename__ = "vocab_entries"
    __table_args__ = (UniqueConstraint("user_id", "word", name="uq_vocab_entries_user_word"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    word = Column(String, nullable=False, index=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
        index=True,
    )
    detail = Column(JSON, nullable=True)

    # Spaced-repetition scheduling (simplified SM-2). next_review_at is null
    # until the word is reviewed for the first time, which makes it due
    # immediately.
    interval_days = Column(Integer, nullable=False, default=0)
    ease_factor = Column(Float, nullable=False, default=2.5)
    repetitions = Column(Integer, nullable=False, default=0)
    next_review_at = Column(DateTime, nullable=True, index=True)


class AppSetting(Base):
    """User-configurable app settings (currently just the OpenAI
    credentials), one row per user, so they can be set from the frontend
    Settings page instead of editing the backend's .env file.
    """

    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, unique=True, index=True)
    openai_api_key = Column(String, nullable=True)
    openai_model = Column(String, nullable=True)
    review_mode = Column(Boolean, nullable=True, default=False)
