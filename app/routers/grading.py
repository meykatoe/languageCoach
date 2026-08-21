from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Question
from app.schemas import GradingFeedback, SpeakingGradingRequest, WritingGradingRequest
from app.services.openai_service import grade_response

router = APIRouter(prefix="/api/grading", tags=["grading"])


def _find_prompt_text(content: dict) -> str:
    for key in ("prompt", "topic", "sentence", "question"):
        if key in content and isinstance(content[key], str):
            return content[key]
    return str(content)


def _get_question_or_404(db: Session, source_id: str) -> Question:
    q = db.query(Question).filter(Question.source_id == source_id).one_or_none()
    if q is None:
        raise HTTPException(status_code=404, detail=f"Question '{source_id}' not found")
    return q


@router.post("/writing", response_model=GradingFeedback)
def grade_writing(payload: WritingGradingRequest, db: Session = Depends(get_db)):
    question = _get_question_or_404(db, payload.source_id)
    prompt_text = _find_prompt_text(question.content)
    try:
        result = grade_response(payload.exam, prompt_text, payload.essay, skill="writing")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return GradingFeedback(**result)


@router.post("/speaking", response_model=GradingFeedback)
def grade_speaking(payload: SpeakingGradingRequest, db: Session = Depends(get_db)):
    question = _get_question_or_404(db, payload.source_id)
    prompt_text = _find_prompt_text(question.content)
    try:
        result = grade_response(
            payload.exam, prompt_text, payload.transcript, skill="speaking"
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return GradingFeedback(**result)
