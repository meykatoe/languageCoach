from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Question, User
from app.schemas import ExamSummary, QuestionOut

router = APIRouter(prefix="/api", tags=["exams"])


def _visible_questions(db: Session, user: User):
    return db.query(Question).filter(or_(Question.user_id.is_(None), Question.user_id == user.id))


@router.get("/exams", response_model=list[ExamSummary])
def list_exams(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (
        _visible_questions(db, current_user)
        .with_entities(
            Question.exam,
            Question.section,
            Question.part,
            Question.qtype,
            func.count(Question.id).label("count"),
        )
        .group_by(Question.exam, Question.section, Question.part, Question.qtype)
        .order_by(Question.exam, Question.section, Question.part)
        .all()
    )
    return [
        ExamSummary(exam=r[0], section=r[1], part=r[2], qtype=r[3], count=r[4])
        for r in rows
    ]


@router.get("/questions", response_model=list[QuestionOut])
def list_questions(
    exam: str | None = Query(default=None),
    section: str | None = Query(default=None),
    part: str | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = _visible_questions(db, current_user)
    if exam:
        q = q.filter(Question.exam == exam)
    if section:
        q = q.filter(Question.section == section)
    if part:
        q = q.filter(Question.part == part)
    rows = q.order_by(func.random()).limit(limit).all()
    return rows
