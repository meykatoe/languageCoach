from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Attempt, Question
from app.routers.practice import _find_node_by_id
from app.schemas import QuestionOut

router = APIRouter(prefix="/api/review", tags=["review"])


@router.get("", response_model=list[QuestionOut])
def get_review_questions(
    limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db)
):
    """Return the parent question items for objective sub-questions whose
    most recent attempt was incorrect, most recently missed first.
    """
    attempts = (
        db.query(Attempt)
        .filter(Attempt.item_type == "objective")
        .order_by(Attempt.created_at.desc())
        .all()
    )

    seen_source_ids: set[str] = set()
    wrong_source_ids: list[str] = []
    for a in attempts:
        if a.source_id in seen_source_ids:
            continue
        seen_source_ids.add(a.source_id)
        if a.is_correct is False:
            wrong_source_ids.append(a.source_id)

    if not wrong_source_ids:
        return []

    all_questions = db.query(Question).all()
    result: list[Question] = []
    included_parent_ids: set[int] = set()

    for sub_id in wrong_source_ids:
        for q in all_questions:
            if q.id in included_parent_ids:
                continue
            node = _find_node_by_id(q.content, sub_id)
            if node is not None:
                result.append(q)
                included_parent_ids.add(q.id)
                break
        if len(result) >= limit:
            break

    return result
