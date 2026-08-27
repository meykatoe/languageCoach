"""Shared objective-answer grading helpers used by both ad-hoc practice
submission (app/routers/practice.py) and full mock-exam grading
(app/routers/mock_exam.py).
"""
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models import Attempt


def find_node_by_id(node: Any, target_id: str) -> Optional[dict]:
    """Depth-first search for a dict with id == target_id anywhere inside a
    question's JSON content (handles nested sub-questions in conversations,
    passages, cue cards, etc.).
    """
    if isinstance(node, dict):
        if node.get("id") == target_id:
            return node
        for value in node.values():
            found = find_node_by_id(value, target_id)
            if found is not None:
                return found
    elif isinstance(node, list):
        for item in node:
            found = find_node_by_id(item, target_id)
            if found is not None:
                return found
    return None


def latest_objective_attempts(db: Session, user_id: int) -> list[Attempt]:
    """One row per objective source_id: its most recent attempt, newest
    overall first. This is "current state" (did the student get it right
    the last time they tried it), used by both the error-notebook review
    list and the history page's weakness breakdown so the two stay in sync.
    """
    attempts = (
        db.query(Attempt)
        .filter(Attempt.user_id == user_id, Attempt.item_type == "objective")
        .order_by(Attempt.created_at.desc())
        .all()
    )
    seen: set[str] = set()
    latest: list[Attempt] = []
    for a in attempts:
        if a.source_id in seen:
            continue
        seen.add(a.source_id)
        latest.append(a)
    return latest


def answers_match(expected: Any, submitted: Any) -> bool:
    if isinstance(expected, list):
        if isinstance(submitted, list):
            return sorted(str(x).strip().upper() for x in expected) == sorted(
                str(x).strip().upper() for x in submitted
            )
        return False
    return str(expected).strip().upper() == str(submitted).strip().upper()
