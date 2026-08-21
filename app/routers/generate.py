import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Question
from app.schemas import GenerateRequest, QuestionOut
from app.services.openai_service import generate_questions

router = APIRouter(prefix="/api/generate", tags=["generate"])


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "item"


@router.post("", response_model=list[QuestionOut])
def generate(payload: GenerateRequest, db: Session = Depends(get_db)):
    q = db.query(Question).filter(Question.exam == payload.exam, Question.section == payload.section)
    if payload.part:
        q = q.filter(Question.part == payload.part)
    template = q.first()
    if template is None:
        raise HTTPException(
            status_code=404,
            detail="No existing question found to use as a format template for this exam/section/part.",
        )

    try:
        items = generate_questions(
            payload.exam, payload.section, payload.part or payload.section, template.content, payload.count
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=502, detail=f"AI generation returned malformed data: {exc}") from exc

    existing_ids = {row[0] for row in db.query(Question.source_id).all()}
    created: list[Question] = []

    for item in items:
        if not isinstance(item, dict):
            continue
        source_id = item.get("id")
        if not source_id or not isinstance(source_id, str):
            source_id = f"ai-{_slugify(payload.part or payload.section)}-{uuid.uuid4().hex[:8]}"
        while source_id in existing_ids:
            source_id = f"{source_id}-{uuid.uuid4().hex[:4]}"
        item["id"] = source_id
        existing_ids.add(source_id)

        row = Question(
            source_id=source_id,
            exam=payload.exam,
            section=payload.section,
            part=payload.part or template.part,
            qtype=template.qtype,
            source_file="ai-generated",
            content=item,
        )
        db.add(row)
        created.append(row)

    db.commit()
    for row in created:
        db.refresh(row)

    return created
