from sqlalchemy import JSON, Column, Integer, String, UniqueConstraint

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
