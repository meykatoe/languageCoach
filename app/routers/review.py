from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import AppSetting, Question, User
from app.schemas import QuestionOut
from app.services.grading import find_node_by_id, latest_objective_attempts

router = APIRouter(prefix="/api/review", tags=["review"])


@router.get("", response_model=list[QuestionOut])
def get_review_questions(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the parent question items for objective sub-questions whose
    most recent attempt was incorrect, most recently missed first.

    In review mode, previously recorded AI notes are withheld so the user
    can attempt the question again without seeing the earlier hint spoiled.
    """
    setting = db.query(AppSetting).filter(AppSetting.user_id == current_user.id).first()
    review_mode = bool(setting and setting.review_mode)

    wrong_source_ids: list[str] = []
    wrong_notes: dict[str, str] = {}
    for a in latest_objective_attempts(db, current_user.id):
        if a.is_correct is False:
            wrong_source_ids.append(a.source_id)
            note = (a.detail or {}).get("note") if a.detail else None
            if note:
                wrong_notes[a.source_id] = note

    if not wrong_source_ids:
        return []

    all_questions = (
        db.query(Question)
        .filter(or_(Question.user_id.is_(None), Question.user_id == current_user.id))
        .all()
    )
    result: list[QuestionOut] = []
    included_parent_ids: set[int] = set()

    for sub_id in wrong_source_ids:
        for q in all_questions:
            if q.id in included_parent_ids:
                continue
            node = find_node_by_id(q.content, sub_id)
            if node is not None:
                out = QuestionOut.model_validate(q)
                if not review_mode:
                    out.reviewNotes = {
                        other_id: wrong_notes[other_id]
                        for other_id in wrong_source_ids
                        if other_id in wrong_notes and find_node_by_id(q.content, other_id) is not None
                    } or None
                result.append(out)
                included_parent_ids.add(q.id)
                break
        if len(result) >= limit:
            break

    return result
