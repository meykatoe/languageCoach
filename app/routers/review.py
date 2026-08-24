from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AppSetting, Attempt, Question
from app.services.grading import find_node_by_id
from app.schemas import QuestionOut

router = APIRouter(prefix="/api/review", tags=["review"])


@router.get("", response_model=list[QuestionOut])
def get_review_questions(
    limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db)
):
    """Return the parent question items for objective sub-questions whose
    most recent attempt was incorrect, most recently missed first.

    In review mode, previously recorded AI notes are withheld so the user
    can attempt the question again without seeing the earlier hint spoiled.
    """
    setting = db.query(AppSetting).first()
    review_mode = bool(setting and setting.review_mode)

    attempts = (
        db.query(Attempt)
        .filter(Attempt.item_type == "objective")
        .order_by(Attempt.created_at.desc())
        .all()
    )

    seen_source_ids: set[str] = set()
    wrong_source_ids: list[str] = []
    wrong_notes: dict[str, str] = {}
    for a in attempts:
        if a.source_id in seen_source_ids:
            continue
        seen_source_ids.add(a.source_id)
        if a.is_correct is False:
            wrong_source_ids.append(a.source_id)
            note = (a.detail or {}).get("note") if a.detail else None
            if note:
                wrong_notes[a.source_id] = note

    if not wrong_source_ids:
        return []

    all_questions = db.query(Question).all()
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
