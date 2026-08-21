import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from openai import APIError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Question
from app.schemas import GenerateRequest, QuestionOut
from app.services.id_dedup import collect_all_ids, dedupe_all_ids
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
    except APIError as exc:
        raise HTTPException(
            status_code=502, detail=f"OpenAI API 呼叫失敗,請確認 ⚙️ 設定頁的 API Key 是否正確: {exc}"
        ) from exc
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=502, detail=f"AI generation returned malformed data: {exc}") from exc

    # The full set of ids already used ANYWHERE in the bank, top-level and
    # nested (not just Question.source_id), so a newly generated item's sub-
    # question ids can never silently shadow an unrelated existing question.
    existing_ids = collect_all_ids(db)
    created: list[Question] = []

    for item in items:
        if not isinstance(item, dict):
            continue
        if not isinstance(item.get("id"), str) or not item["id"]:
            item["id"] = f"ai-{_slugify(payload.part or payload.section)}-{uuid.uuid4().hex[:8]}"
        dedupe_all_ids(item, existing_ids)
        source_id = item["id"]

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
