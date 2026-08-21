from typing import Any, Optional

from pydantic import BaseModel


class QuestionOut(BaseModel):
    id: int
    source_id: str
    exam: str
    section: str
    part: Optional[str]
    qtype: str
    content: Any

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
