import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from openai import APIError
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, VocabEntry
from app.schemas import VocabEntryOut, VocabReviewAnswerIn, VocabReviewDueCount, VocabReviewQuestion, VocabReviewResult
from app.services.openai_service import generate_vocab_entry
from app.services.vocab import apply_review_result, build_blank_sentence

router = APIRouter(prefix="/api/vocab", tags=["vocab"])


def _due_query(db: Session, user_id: int):
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    return db.query(VocabEntry).filter(
        VocabEntry.user_id == user_id,
        or_(VocabEntry.next_review_at.is_(None), VocabEntry.next_review_at <= now),
    )


def _get_owned_entry_or_404(db: Session, user: User, entry_id: int) -> VocabEntry:
    entry = db.get(VocabEntry, entry_id)
    if entry is None or entry.user_id != user.id:
        raise HTTPException(status_code=404, detail=f"Vocab entry '{entry_id}' not found")
    return entry


@router.get("", response_model=list[VocabEntryOut])
def list_vocab(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    entries = (
        db.query(VocabEntry)
        .filter(VocabEntry.user_id == current_user.id)
        .order_by(VocabEntry.created_at.desc())
        .all()
    )
    return [VocabEntryOut.model_validate(e) for e in entries]


@router.get("/review/due-count", response_model=VocabReviewDueCount)
def get_review_due_count(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Lightweight count of words currently due for review, for a home-page
    reminder widget that shouldn't pay the cost of building blank sentences
    for every due entry."""
    return VocabReviewDueCount(due=_due_query(db, current_user.id).count())


@router.get("/review/queue", response_model=list[VocabReviewQuestion])
def get_review_queue(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Words due for spaced-repetition review (never reviewed, or whose
    schedule has come due), each turned into a fill-in-the-blank question
    from one of its dictionary example sentences. Entries without a usable
    example (detail not generated yet, or no example contains the word) are
    skipped.
    """
    entries = (
        _due_query(db, current_user.id)
        .order_by(VocabEntry.next_review_at.asc().nulls_first())
        .limit(limit * 2)  # over-fetch since some entries may have no usable example
        .all()
    )
    questions = []
    for entry in entries:
        sentence = build_blank_sentence(entry)
        if sentence is None:
            continue
        phonetic = (entry.detail or {}).get("phonetic")
        questions.append(VocabReviewQuestion(id=entry.id, word=entry.word, phonetic=phonetic, sentence=sentence))
        if len(questions) >= limit:
            break
    return questions


@router.post("/{entry_id}/review", response_model=VocabReviewResult)
def submit_review_answer(
    entry_id: int,
    payload: VocabReviewAnswerIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entry = _get_owned_entry_or_404(db, current_user, entry_id)

    correct = payload.answer.strip().lower() == entry.word.lower()
    apply_review_result(entry, correct)
    db.commit()
    db.refresh(entry)

    return VocabReviewResult(
        correct=correct,
        correct_answer=entry.word,
        interval_days=entry.interval_days,
        next_review_at=entry.next_review_at,
    )


@router.delete("/{entry_id}", status_code=204)
def delete_vocab_entry(
    entry_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    entry = _get_owned_entry_or_404(db, current_user, entry_id)
    db.delete(entry)
    db.commit()


@router.post("/{entry_id}/regenerate", response_model=VocabEntryOut)
def regenerate_vocab_entry(
    entry_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Retry generating the dictionary entry for a word whose first attempt
    failed (or hasn't run yet), e.g. because no OpenAI API key was
    configured at the time it was added to the vocab book.
    """
    entry = _get_owned_entry_or_404(db, current_user, entry_id)

    try:
        entry.detail = generate_vocab_entry(current_user.id, entry.word)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except APIError as exc:
        raise HTTPException(
            status_code=502, detail=f"OpenAI API 呼叫失敗,請確認 ⚙️ 設定頁的 API Key 是否正確: {exc}"
        ) from exc

    db.commit()
    db.refresh(entry)
    return VocabEntryOut.model_validate(entry)
