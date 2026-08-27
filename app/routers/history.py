import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Attempt
from app.schemas import (
    AttemptOut,
    DailyActivity,
    DailyStat,
    ExamStat,
    HistorySummary,
    WeaknessStat,
)
from app.services.grading import latest_objective_attempts

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

    # Weakness breakdown: among currently-unresolved wrong answers (the same
    # "latest attempt per question" definition /api/review uses), which
    # exam/section/part has the most, worst first — so the user can see at a
    # glance where to focus, and jump to /review to actually work through them.
    wrong_counts: dict[tuple[str, str, Optional[str]], int] = {}
    for a in latest_objective_attempts(db):
        if a.is_correct is False:
            key = (a.exam, a.section, a.part)
            wrong_counts[key] = wrong_counts.get(key, 0) + 1

    weaknesses = sorted(
        (
            WeaknessStat(exam=exam, section=section, part=part, wrong_count=count)
            for (exam, section, part), count in wrong_counts.items()
        ),
        key=lambda w: w.wrong_count,
        reverse=True,
    )

    recent = (
        db.query(Attempt).order_by(Attempt.created_at.desc()).limit(limit).all()
    )

    # Daily accuracy trend for objective questions only (writing/speaking use
    # a text score/band, not right-or-wrong), last 30 calendar days by date
    # of the attempt so the chart shows recent progress over time. Filtered
    # by a date cutoff (not just ordered + limited) so once history exceeds
    # the window this returns the most RECENT days, not the oldest.
    today = datetime.date.today()
    day = func.date(Attempt.created_at)
    accuracy_cutoff = (today - datetime.timedelta(days=29)).isoformat()
    daily_rows = (
        db.query(
            day,
            func.count(Attempt.id),
            func.sum(func.coalesce(Attempt.is_correct, 0)),
        )
        .filter(Attempt.item_type == "objective", day >= accuracy_cutoff)
        .group_by(day)
        .order_by(day)
        .all()
    )
    daily_accuracy = [
        DailyStat(
            date=date_str,
            total=total,
            correct=correct or 0,
            accuracy=round((correct or 0) / total, 3) if total else 0.0,
        )
        for date_str, total, correct in daily_rows
    ]

    # Activity heatmap data: attempt count per day across all item types
    # (objective/writing/speaking), last 371 days (53 weeks) so the frontend
    # can lay out a GitHub-style year grid.
    activity_cutoff = (today - datetime.timedelta(days=370)).isoformat()
    activity_rows = (
        db.query(day, func.count(Attempt.id))
        .filter(day >= activity_cutoff)
        .group_by(day)
        .order_by(day)
        .all()
    )
    daily_activity = [
        DailyActivity(date=date_str, count=count) for date_str, count in activity_rows
    ]

    return HistorySummary(
        total_attempts=total_attempts,
        stats=stats,
        weaknesses=weaknesses,
        daily_accuracy=daily_accuracy,
        daily_activity=daily_activity,
        recent=[AttemptOut.model_validate(r) for r in recent],
    )
