from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from openai import APIError
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Question, User
from app.schemas import TranslateRequest, TranslateResponse, TranslateTextRequest
from app.services import vocab
from app.services.openai_service import translate_text

router = APIRouter(prefix="/api/translate", tags=["translate"])


def _save_to_vocab_book(user_id: int, text: str, db: Session, background_tasks: BackgroundTasks) -> bool:
    """If `text` is a single English word not already in the vocab book,
    saves a placeholder row and schedules its dictionary entry to be
    generated in the background (after this request returns, so the
    inline-translate popup isn't slowed down by the heavier lookup).
    Returns whether the word is now saved (whether by this call or already).
    """
    if not vocab.is_single_word(text):
        return False
    if vocab.word_already_saved(db, user_id, text):
        return True
    try:
        entry = vocab.save_new_word_for_background_generation(user_id, text)
    except IntegrityError:
        return True  # a concurrent request already saved this word
    background_tasks.add_task(vocab.generate_and_store_entry, entry.id)
    return True

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
def translate_selection(
    payload: TranslateTextRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Translate an arbitrary snippet of selected text, for the site-wide
    text-selection popup (not tied to any stored question). If the
    selection is a single word, it's also auto-saved into the vocabulary
    book (with its full dictionary entry generated in the background).
    """
    text = payload.text.strip()
    try:
        translation = translate_text(current_user.id, text)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except APIError as exc:
        raise HTTPException(
            status_code=502, detail=f"OpenAI API 呼叫失敗,請確認 ⚙️ 設定頁的 API Key 是否正確: {exc}"
        ) from exc

    added_to_vocab = _save_to_vocab_book(current_user.id, text, db, background_tasks)
    return TranslateResponse(translation=translation, added_to_vocab=added_to_vocab)


@router.post("", response_model=TranslateResponse)
def translate_question(
    payload: TranslateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    question = (
        db.query(Question)
        .filter(
            Question.source_id == payload.source_id,
            or_(Question.user_id.is_(None), Question.user_id == current_user.id),
        )
        .one_or_none()
    )
    if question is None:
        raise HTTPException(status_code=404, detail=f"Question '{payload.source_id}' not found")

    source_text = "\n".join(_flatten_text(question.content))
    if not source_text:
        raise HTTPException(status_code=422, detail="此題目沒有可翻譯的文字內容。")

    try:
        translation = translate_text(current_user.id, source_text)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except APIError as exc:
        raise HTTPException(
            status_code=502, detail=f"OpenAI API 呼叫失敗,請確認 ⚙️ 設定頁的 API Key 是否正確: {exc}"
        ) from exc

    return TranslateResponse(translation=translation)
