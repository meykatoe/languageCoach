from typing import Any, Optional

from fastapi import APIRouter, Depends
from openai import APIError
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import AppSetting, Attempt, Question, User
from app.schemas import GradedAnswer, PracticeSubmitRequest, PracticeSubmitResponse
from app.services.grading import answers_match, find_node_by_id
from app.services.openai_service import explain_mistake, review_progress_comment

router = APIRouter(prefix="/api/practice", tags=["practice"])


def _is_review_mode(db: Session, user_id: int) -> bool:
    setting = db.query(AppSetting).filter(AppSetting.user_id == user_id).first()
    return bool(setting and setting.review_mode)


def _latest_note(db: Session, user_id: int, source_id: str) -> Optional[str]:
    """The note attached to this source_id's most recent objective attempt,
    if any, used as the "previous record" in review mode.
    """
    prev = (
        db.query(Attempt)
        .filter(Attempt.user_id == user_id, Attempt.source_id == source_id, Attempt.item_type == "objective")
        .order_by(Attempt.created_at.desc())
        .first()
    )
    return (prev.detail or {}).get("note") if prev and prev.detail else None


def _generate_mistake_note(user_id: int, exam: str, node: dict, expected: Any, submitted: Any) -> Optional[str]:
    """Best-effort AI explanation of a wrong answer, for the error notebook.
    Never raises: if the AI call fails (no API key, network error, ...), the
    submission should still succeed without a note.
    """
    try:
        return explain_mistake(user_id, exam, node, expected, submitted)
    except (RuntimeError, APIError, ValueError):
        return None


def _generate_review_comment(
    user_id: int, exam: str, node: dict, expected: Any, submitted: Any, is_correct: bool, previous_note: str
) -> Optional[str]:
    """Best-effort AI comment for a review-mode repeat attempt, taking the
    previous record into account. Never raises, same reasoning as above.
    """
    try:
        return review_progress_comment(user_id, exam, node, expected, submitted, is_correct, previous_note)
    except (RuntimeError, APIError, ValueError):
        return None


@router.post("/submit", response_model=PracticeSubmitResponse)
def submit_practice(
    payload: PracticeSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    results: list[GradedAnswer] = []
    correct_count = 0
    graded_count = 0
    review_mode = _is_review_mode(db, current_user.id)

    all_questions = (
        db.query(Question)
        .filter(or_(Question.user_id.is_(None), Question.user_id == current_user.id))
        .all()
    )

    for ans in payload.answers:
        node = None
        parent: Optional[Question] = None
        for q in all_questions:
            node = find_node_by_id(q.content, ans.source_id)
            if node is not None:
                parent = q
                break

        expected = node.get("answer") if node else None
        is_correct: Optional[bool] = None
        note: Optional[str] = None
        if expected is not None:
            is_correct = answers_match(expected, ans.answer)
            graded_count += 1
            if is_correct:
                correct_count += 1

            if parent is not None:
                previous_note = _latest_note(db, current_user.id, ans.source_id) if review_mode else None
                if review_mode and previous_note:
                    note = _generate_review_comment(
                        current_user.id, parent.exam, node, expected, ans.answer, is_correct, previous_note
                    )
                elif not is_correct:
                    note = _generate_mistake_note(current_user.id, parent.exam, node, expected, ans.answer)

            if parent is not None:
                db.add(
                    Attempt(
                        user_id=current_user.id,
                        exam=parent.exam,
                        section=parent.section,
                        part=parent.part,
                        source_id=ans.source_id,
                        item_type="objective",
                        is_correct=is_correct,
                        detail={
                            "correctAnswer": expected,
                            "submittedAnswer": ans.answer,
                            "note": note,
                        },
                    )
                )

        results.append(
            GradedAnswer(
                source_id=ans.source_id,
                correct=is_correct,
                correctAnswer=expected,
                submittedAnswer=ans.answer,
                note=note,
            )
        )

    db.commit()

    return PracticeSubmitResponse(
        total=len(payload.answers),
        graded=graded_count,
        correct=correct_count,
        results=results,
    )
