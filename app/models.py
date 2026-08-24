import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, UniqueConstraint

from app.database import Base


class Question(Base):
    """One practice item (a single question, a conversation, a passage, a
    cue card, a writing prompt, ...). The full original JSON object is kept
    in `content` so the frontend can render any shape without the backend
    needing a table per question type.
    """

    __tablename__ = "questions"
    __table_args__ = (UniqueConstraint("source_id", name="uq_question_source_id"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
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


class AppSetting(Base):
    """Single-row table holding user-configurable app settings (currently
    just the OpenAI credentials), so they can be set from the frontend
    Settings page instead of editing the backend's .env file.
    """

    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    openai_api_key = Column(String, nullable=True)
    openai_model = Column(String, nullable=True)
    review_mode = Column(Boolean, nullable=True, default=False)
