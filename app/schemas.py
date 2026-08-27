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


class WeaknessStat(BaseModel):
    exam: str
    section: str
    part: Optional[str]
    wrong_count: int


class DailyStat(BaseModel):
    date: str
    total: int
    correct: int
    accuracy: float


class DailyActivity(BaseModel):
    date: str
    count: int


class HistorySummary(BaseModel):
    total_attempts: int
    stats: list[ExamStat]
    weaknesses: list[WeaknessStat]
    daily_accuracy: list[DailyStat]
    daily_activity: list[DailyActivity]
    recent: list[AttemptOut]


class MockExamStartRequest(BaseModel):
    exam: str = "TOEIC"
    mode: str = Field(default="bank", pattern="^(bank|ai_generated)$")


class MockExamQuestion(BaseModel):
    source_id: str
    exam: str
    section: str
    part: Optional[str]
    qtype: str
    source_file: str
    content: Any
    reviewNotes: Optional[dict[str, str]] = None


class MockExamSectionPayload(BaseModel):
    section: str
    deadline: datetime.datetime
    questions: list[MockExamQuestion]


class MockExamStartResponse(BaseModel):
    id: int
    exam: str
    mode: str
    status: str
    listening: MockExamSectionPayload


class MockExamSectionSubmitRequest(BaseModel):
    answers: list[AnswerSubmission]


class MockExamListeningSubmitResponse(BaseModel):
    id: int
    status: str
    reading: MockExamSectionPayload


class MockExamSectionScore(BaseModel):
    raw_correct: int
    raw_total: int
    scaled_score: int


class MockExamFinalResult(BaseModel):
    id: int
    exam: str
    status: str
    listening: MockExamSectionScore
    reading: MockExamSectionScore
    scaled_total: int
    listening_results: list[GradedAnswer]
    reading_results: list[GradedAnswer]
    advice: Optional[str] = None
    disclaimer: str = "換算分數為依答對題數所做的近似估算，並非官方正式成績，僅供練習參考。"


class MockExamStateResponse(BaseModel):
    id: int
    exam: str
    mode: str
    status: str
    listening_deadline: Optional[datetime.datetime]
    reading_deadline: Optional[datetime.datetime]
    listening: Optional[MockExamSectionPayload] = None
    reading: Optional[MockExamSectionPayload] = None
    result: Optional[MockExamFinalResult] = None


class MockExamHistoryItem(BaseModel):
    id: int
    exam: str
    mode: str
    status: str
    created_at: datetime.datetime
    scaled_listening: Optional[int]
    scaled_reading: Optional[int]
    scaled_total: Optional[int]

    model_config = {"from_attributes": True}


class SettingsUpdateRequest(BaseModel):
    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = None
    clear_api_key: bool = False
    review_mode: Optional[bool] = None


class SettingsOut(BaseModel):
    has_api_key: bool
    api_key_hint: Optional[str] = None
    api_key_source: str  # "database" | "environment" | "none"
    openai_model: str
    review_mode: bool = False


class TranslateRequest(BaseModel):
    source_id: str


class TranslateTextRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


class TtsRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class ImageRequest(BaseModel):
    description: str = Field(min_length=1, max_length=4000)


class TranslateResponse(BaseModel):
    translation: str
    added_to_vocab: Optional[bool] = None


class TestConnectionRequest(BaseModel):
    openai_api_key: Optional[str] = None


class TestConnectionResponse(BaseModel):
    ok: bool
    message: str


class VocabEntryOut(BaseModel):
    id: int
    word: str
    created_at: datetime.datetime
    detail: Optional[dict] = None
    interval_days: int
    repetitions: int
    next_review_at: Optional[datetime.datetime] = None

    model_config = {"from_attributes": True}


class VocabReviewQuestion(BaseModel):
    id: int
    word: str
    phonetic: Optional[str] = None
    sentence: str

    model_config = {"from_attributes": True}


class VocabReviewAnswerIn(BaseModel):
    answer: str


class VocabReviewDueCount(BaseModel):
    due: int


class VocabReviewResult(BaseModel):
    correct: bool
    correct_answer: str
    interval_days: int
    next_review_at: datetime.datetime
