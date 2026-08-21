from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Attempt
from app.schemas import AttemptOut, ExamStat, HistorySummary

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("", response_model=HistorySummary)
def get_history(
    limit: int = Query(default=30, ge=1, le=200), db: Session = Depends(get_db)
):
    total_attempts = db.query(func.count(Attempt.id)).scalar() or 0

    rows = (
        db.query(
            Attempt.exam,
            Attempt.section,
            Attempt.item_type,
            func.count(Attempt.id),
            func.sum(func.coalesce(Attempt.is_correct, 0)),
        )
        .group_by(Attempt.exam, Attempt.section, Attempt.item_type)
        .order_by(Attempt.exam, Attempt.section)
        .all()
    )
    stats = []
    for exam, section, item_type, total, correct in rows:
        correct = correct or 0
        accuracy = round(correct / total, 3) if item_type == "objective" and total else None
        stats.append(
            ExamStat(
                exam=exam,
                section=section,
                item_type=item_type,
                total=total,
                correct=correct,
                accuracy=accuracy,
            )
        )

    recent = (
        db.query(Attempt).order_by(Attempt.created_at.desc()).limit(limit).all()
    )

    return HistorySummary(
        total_attempts=total_attempts,
        stats=stats,
        recent=[AttemptOut.model_validate(r) for r in recent],
    )
