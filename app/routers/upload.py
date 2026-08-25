import re
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from openai import APIError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Question
from app.schemas import QuestionOut
from app.services.file_extract import UnsupportedFileType, extract_text
from app.services.id_dedup import collect_all_ids, dedupe_all_ids
from app.services.openai_service import generate_from_reference

router = APIRouter(prefix="/api/upload", tags=["upload"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
MIN_COUNT = 1
MAX_COUNT = 10


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "item"


def _infer_qtype(item: dict) -> str:
    if "blanks" in item:
        return "passages"
    if "passage" in item and "questions" in item:
        return "passages"
    if "transcript" in item and "questions" in item:
        return "conversations"
    if "options" in item:
        return "questions"
    return "prompts"


def _infer_section(item: dict) -> str:
    # Only the "open prompt" shape (no options/blanks/sub-questions) needs a
    # section value the frontend recognizes to pick the writing AI-grading
    # skill; everything else is objectively graded so the label mainly
    # matters for organizing/filtering in the UI.
    if "options" in item or "blanks" in item or "questions" in item:
        return "Reading"
    return "Writing"


@router.post("", response_model=list[QuestionOut])
async def upload_and_generate(
    file: UploadFile = File(...),
    count: int = Form(3),
    exam: str = Form("Custom"),
    db: Session = Depends(get_db),
):
    if count < MIN_COUNT or count > MAX_COUNT:
        raise HTTPException(
            status_code=400, detail=f"題目數量須介於 {MIN_COUNT} 到 {MAX_COUNT} 之間。"
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="檔案過大,請上傳 10MB 以下的檔案。")

    try:
        text = extract_text(file.filename or "", content)
    except UnsupportedFileType as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"檔案解析失敗: {exc}") from exc

    if not text:
        raise HTTPException(
            status_code=400,
            detail="無法從檔案中擷取到文字內容,請確認檔案不是純圖片掃描檔。",
        )

    try:
        items = generate_from_reference(text, count)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except APIError as exc:
        raise HTTPException(
            status_code=502, detail=f"OpenAI API 呼叫失敗,請確認 ⚙️ 設定頁的 API Key 是否正確: {exc}"
        ) from exc
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=502, detail=f"AI 產生的內容格式錯誤: {exc}") from exc

    existing_ids = collect_all_ids(db)
    created: list[Question] = []
    part_label = file.filename or "上傳題庫"

    for item in items:
        if not isinstance(item, dict):
            continue
        if not isinstance(item.get("id"), str) or not item["id"]:
            item["id"] = f"upload-{_slugify(part_label)}-{uuid.uuid4().hex[:8]}"
        dedupe_all_ids(item, existing_ids)
        source_id = item["id"]

        row = Question(
            source_id=source_id,
            exam=exam.strip() or "Custom",
            section=_infer_section(item),
            part=part_label,
            qtype=_infer_qtype(item),
            source_file="user-upload",
            content=item,
        )
        db.add(row)
        created.append(row)

    if not created:
        raise HTTPException(status_code=502, detail="AI 未產生任何有效題目,請再試一次。")

    db.commit()
    for row in created:
        db.refresh(row)

    return created
