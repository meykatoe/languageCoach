from fastapi import APIRouter, Depends, HTTPException
from openai import APIError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import VocabEntry
from app.schemas import VocabEntryOut
from app.services.openai_service import generate_vocab_entry

router = APIRouter(prefix="/api/vocab", tags=["vocab"])


@router.get("", response_model=list[VocabEntryOut])
def list_vocab(db: Session = Depends(get_db)):
    entries = db.query(VocabEntry).order_by(VocabEntry.created_at.desc()).all()
    return [VocabEntryOut.model_validate(e) for e in entries]


@router.delete("/{entry_id}", status_code=204)
def delete_vocab_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.get(VocabEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Vocab entry '{entry_id}' not found")
    db.delete(entry)
    db.commit()


@router.post("/{entry_id}/regenerate", response_model=VocabEntryOut)
def regenerate_vocab_entry(entry_id: int, db: Session = Depends(get_db)):
    """Retry generating the dictionary entry for a word whose first attempt
    failed (or hasn't run yet), e.g. because no OpenAI API key was
    configured at the time it was added to the vocab book.
    """
    entry = db.get(VocabEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Vocab entry '{entry_id}' not found")

    try:
        entry.detail = generate_vocab_entry(entry.word)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except APIError as exc:
        raise HTTPException(
            status_code=502, detail=f"OpenAI API 呼叫失敗,請確認 ⚙️ 設定頁的 API Key 是否正確: {exc}"
        ) from exc

    db.commit()
    db.refresh(entry)
    return VocabEntryOut.model_validate(entry)
