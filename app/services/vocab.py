"""Vocabulary-book logic: deciding whether a selected snippet of text is a
single word worth saving, generating/storing its dictionary entry, and the
spaced-repetition (simplified SM-2) fill-in-the-blank review flow.
"""

import datetime
import random
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


def word_already_saved(db, user_id: int, word: str) -> bool:
    return (
        db.query(VocabEntry)
        .filter(VocabEntry.user_id == user_id, VocabEntry.word == normalize_word(word))
        .first()
        is not None
    )


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
            detail = generate_vocab_entry(entry.user_id, entry.word)
        except (RuntimeError, ValueError):
            return
        entry.detail = detail
        db.commit()
    finally:
        db.close()


def save_new_word_for_background_generation(user_id: int, word: str) -> VocabEntry:
    """Inserts a placeholder row (detail=None) for a not-yet-seen word so it
    shows up in the vocab book immediately; the caller is responsible for
    scheduling `generate_and_store_entry` to fill in the detail afterwards.
    Caller must have already checked `word_already_saved`.
    """
    db = SessionLocal()
    try:
        entry = VocabEntry(user_id=user_id, word=normalize_word(word), detail=None)
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry
    finally:
        db.close()


def build_blank_sentence(entry: VocabEntry) -> str | None:
    """Pick one example sentence from the entry's generated dictionary
    detail and blank out the target word, for a fill-in-the-blank review
    prompt. Returns None if there's no usable example (detail not generated
    yet, or none of the examples actually contain the word).
    """
    if not entry.detail:
        return None
    examples = [
        d.get("example_en", "")
        for e in entry.detail.get("entries", [])
        for d in e.get("definitions", [])
        if d.get("example_en")
    ]
    random.shuffle(examples)

    word_re = re.compile(re.escape(entry.word), re.IGNORECASE)
    for example in examples:
        if word_re.search(example):
            return word_re.sub("_____", example, count=1)
    return None


def _srs_defaults(entry: VocabEntry) -> None:
    """SQLAlchemy column defaults only apply on flush, so a freshly loaded
    row from a pre-migration DB can still have None here; treat that the
    same as "never reviewed"."""
    if entry.repetitions is None:
        entry.repetitions = 0
    if entry.ease_factor is None:
        entry.ease_factor = 2.5
    if entry.interval_days is None:
        entry.interval_days = 0


def apply_review_result(entry: VocabEntry, correct: bool) -> None:
    """Update an entry's spaced-repetition schedule (simplified SM-2) after
    a review attempt. Mutates `entry` in place; caller commits.
    """
    _srs_defaults(entry)

    if correct:
        entry.repetitions += 1
        if entry.repetitions == 1:
            entry.interval_days = 1
        elif entry.repetitions == 2:
            entry.interval_days = 6
        else:
            entry.interval_days = round(entry.interval_days * entry.ease_factor)
        entry.ease_factor = min(2.5, entry.ease_factor + 0.1)
    else:
        entry.repetitions = 0
        entry.interval_days = 1
        entry.ease_factor = max(1.3, entry.ease_factor - 0.2)

    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    entry.next_review_at = now + datetime.timedelta(days=entry.interval_days)
