from fastapi import APIRouter, Depends, HTTPException
from openai import APIError
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Attempt, Question, User
from app.schemas import GradingFeedback, SpeakingGradingRequest, WritingGradingRequest
from app.services.openai_service import grade_response

router = APIRouter(prefix="/api/grading", tags=["grading"])


def _find_prompt_text(content: dict) -> str:
    for key in ("prompt", "topic", "sentence", "question"):
        if key in content and isinstance(content[key], str):
            return content[key]
    return str(content)


def _get_question_or_404(db: Session, user: User, source_id: str) -> Question:
    q = (
        db.query(Question)
        .filter(
            Question.source_id == source_id,
            or_(Question.user_id.is_(None), Question.user_id == user.id),
        )
        .one_or_none()
    )
    if q is None:
        raise HTTPException(status_code=404, detail=f"Question '{source_id}' not found")
    return q


def _record_attempt(db: Session, user: User, question: Question, item_type: str, feedback: dict) -> None:
    db.add(
        Attempt(
            user_id=user.id,
            exam=question.exam,
            section=question.section,
            part=question.part,
            source_id=question.source_id,
            item_type=item_type,
            score=str(feedback.get("score")),
            detail=feedback,
        )
    )
    db.commit()


@router.post("/writing", response_model=GradingFeedback)
def grade_writing(
    payload: WritingGradingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    question = _get_question_or_404(db, current_user, payload.source_id)
    prompt_text = _find_prompt_text(question.content)
    try:
        result = grade_response(current_user.id, payload.exam, prompt_text, payload.essay, skill="writing")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except APIError as exc:
        raise HTTPException(
            status_code=502, detail=f"OpenAI API 呼叫失敗,請確認 ⚙️ 設定頁的 API Key 是否正確: {exc}"
        ) from exc
    _record_attempt(db, current_user, question, "writing", result)
    return GradingFeedback(**result)


@router.post("/speaking", response_model=GradingFeedback)
def grade_speaking(
    payload: SpeakingGradingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    question = _get_question_or_404(db, current_user, payload.source_id)
    prompt_text = _find_prompt_text(question.content)
    try:
        result = grade_response(
            current_user.id, payload.exam, prompt_text, payload.transcript, skill="speaking"
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except APIError as exc:
        raise HTTPException(
            status_code=502, detail=f"OpenAI API 呼叫失敗,請確認 ⚙️ 設定頁的 API Key 是否正確: {exc}"
        ) from exc
    _record_attempt(db, current_user, question, "speaking", result)
    return GradingFeedback(**result)
