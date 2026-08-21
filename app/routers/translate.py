from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from openai import APIError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Question
from app.schemas import TranslateRequest, TranslateResponse, TranslateTextRequest
from app.services.openai_service import translate_text

router = APIRouter(prefix="/api/translate", tags=["translate"])

_SKIP_KEYS = {"id", "answer", "qtype"}


def _flatten_text(node: Any) -> list[str]:
    """Collect the human-readable English strings out of a question's JSON
    content, in document order, skipping ids/answer keys that aren't prose.
    """
    lines: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key in _SKIP_KEYS:
                continue
            lines.extend(_flatten_text(value))
    elif isinstance(node, list):
        for item in node:
            lines.extend(_flatten_text(item))
    elif isinstance(node, str):
        if node.strip():
            lines.append(node.strip())
    return lines


@router.post("/text", response_model=TranslateResponse)
def translate_selection(payload: TranslateTextRequest):
    """Translate an arbitrary snippet of selected text, for the site-wide
    text-selection popup (not tied to any stored question).
    """
    try:
        translation = translate_text(payload.text.strip())
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except APIError as exc:
        raise HTTPException(
            status_code=502, detail=f"OpenAI API 呼叫失敗,請確認 ⚙️ 設定頁的 API Key 是否正確: {exc}"
        ) from exc

    return TranslateResponse(translation=translation)


@router.post("", response_model=TranslateResponse)
def translate_question(payload: TranslateRequest, db: Session = Depends(get_db)):
    question = db.query(Question).filter(Question.source_id == payload.source_id).one_or_none()
    if question is None:
        raise HTTPException(status_code=404, detail=f"Question '{payload.source_id}' not found")

    source_text = "\n".join(_flatten_text(question.content))
    if not source_text:
        raise HTTPException(status_code=422, detail="此題目沒有可翻譯的文字內容。")

    try:
        translation = translate_text(source_text)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except APIError as exc:
        raise HTTPException(
            status_code=502, detail=f"OpenAI API 呼叫失敗,請確認 ⚙️ 設定頁的 API Key 是否正確: {exc}"
        ) from exc

    return TranslateResponse(translation=translation)
