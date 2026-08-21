import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class QuestionOut(BaseModel):
    id: int
    source_id: str
    exam: str
    section: str
    part: Optional[str]
    qtype: str
    source_file: str
    content: Any
    reviewNotes: Optional[dict[str, str]] = None

    model_config = {"from_attributes": True}


class ExamSummary(BaseModel):
    exam: str
    section: str
    part: Optional[str]
    qtype: str
    count: int


class AnswerSubmission(BaseModel):
    source_id: str
    answer: Any


class PracticeSubmitRequest(BaseModel):
    answers: list[AnswerSubmission]


class GradedAnswer(BaseModel):
    source_id: str
    correct: Optional[bool]
    correctAnswer: Any
    submittedAnswer: Any
    note: Optional[str] = None


class PracticeSubmitResponse(BaseModel):
    total: int
    graded: int
    correct: int
    results: list[GradedAnswer]


class WritingGradingRequest(BaseModel):
    source_id: str
    exam: str
    essay: str


class SpeakingGradingRequest(BaseModel):
    source_id: str
    exam: str
    transcript: str


class GradingFeedback(BaseModel):
    score: str
    strengths: list[str]
    weaknesses: list[str]
    suggestions: list[str]
    revisedExample: Optional[str] = None


class GenerateRequest(BaseModel):
    exam: str
    section: str
    part: Optional[str] = None
    count: int = Field(default=3, ge=1, le=5)


class AttemptOut(BaseModel):
    id: int
    created_at: datetime.datetime
    exam: str
    section: str
    part: Optional[str]
    source_id: str
    item_type: str
    is_correct: Optional[bool]
    score: Optional[str]

    model_config = {"from_attributes": True}


class ExamStat(BaseModel):
    exam: str
    section: str
    item_type: str
    total: int
    correct: int
    accuracy: Optional[float]


class HistorySummary(BaseModel):
    total_attempts: int
    stats: list[ExamStat]
    recent: list[AttemptOut]


class SettingsUpdateRequest(BaseModel):
    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = None
    clear_api_key: bool = False


class SettingsOut(BaseModel):
    has_api_key: bool
    api_key_hint: Optional[str] = None
    api_key_source: str  # "database" | "environment" | "none"
    openai_model: str


class TestConnectionRequest(BaseModel):
    openai_api_key: Optional[str] = None


class TestConnectionResponse(BaseModel):
    ok: bool
    message: str
