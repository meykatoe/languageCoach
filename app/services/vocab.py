"""Vocabulary-book logic: deciding whether a selected snippet of text is a
single word worth saving, and generating/storing its dictionary entry.
"""

import re

from app.database import SessionLocal
from app.models import VocabEntry
from app.services.openai_service import generate_vocab_entry

_SINGLE_WORD_RE = re.compile(r"^[A-Za-z][A-Za-z'-]{0,39}$")


def is_single_word(text: str) -> bool:
    """True for a plain English word (letters, plus internal apostrophes/
    hyphens like "don't" or "well-known"), as opposed to a phrase, sentence,
    or non-English selection - only single words go into the vocab book."""
    return bool(_SINGLE_WORD_RE.match(text.strip()))


def normalize_word(word: str) -> str:
    return word.strip().lower()


def word_already_saved(db, word: str) -> bool:
    return db.query(VocabEntry).filter(VocabEntry.word == normalize_word(word)).first() is not None


def generate_and_store_entry(vocab_entry_id: int) -> None:
    """Best-effort background job: generate the dictionary entry for an
    already-created (detail=None) VocabEntry row and fill it in. Opens its
    own DB session since this runs after the triggering HTTP request has
    already completed. Never raises - a failed generation just leaves
    `detail` null for the user to retry later via the regenerate endpoint.
    """
    db = SessionLocal()
    try:
        entry = db.get(VocabEntry, vocab_entry_id)
        if entry is None:
            return
        try:
            detail = generate_vocab_entry(entry.word)
        except (RuntimeError, ValueError):
            return
        entry.detail = detail
        db.commit()
    finally:
        db.close()


def save_new_word_for_background_generation(word: str) -> VocabEntry:
    """Inserts a placeholder row (detail=None) for a not-yet-seen word so it
    shows up in the vocab book immediately; the caller is responsible for
    scheduling `generate_and_store_entry` to fill in the detail afterwards.
    Caller must have already checked `word_already_saved`.
    """
    db = SessionLocal()
    try:
        entry = VocabEntry(word=normalize_word(word), detail=None)
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry
    finally:
        db.close()
