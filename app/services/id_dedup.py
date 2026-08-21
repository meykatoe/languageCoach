"""Shared helpers for keeping question ids unique across the whole bank.

Every id in a question's JSON content (the top-level item id, and any
nested sub-question/blank id) is used as a `source_id` for matching a
submitted answer back to its question (see `_find_node_by_id` in
app/routers/practice.py, which returns the *first* row containing a
matching id). If two different rows ever share an id -- even a nested
one two levels deep -- answers submitted for one can silently get graded
against the other, unrelated question. AI-generated/uploaded content is
especially prone to this because the model is prompted to imitate an
existing item's JSON shape (including its id naming pattern).
"""
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models import Question


def _walk_ids(node: Any, ids: set[str]) -> None:
    if isinstance(node, dict):
        if isinstance(node.get("id"), str):
            ids.add(node["id"])
        for v in node.values():
            _walk_ids(v, ids)
    elif isinstance(node, list):
        for item in node:
            _walk_ids(item, ids)


def collect_all_ids(db: Session) -> set[str]:
    """Every id (top-level and nested) currently used anywhere in the bank."""
    ids: set[str] = set()
    for (content,) in db.query(Question.content).all():
        _walk_ids(content, ids)
    return ids


def dedupe_all_ids(item: Any, existing_ids: set[str]) -> None:
    """Recursively rename every id in `item` that collides with one already
    in `existing_ids`, and register all of item's (possibly renamed) ids
    into `existing_ids` so later items in the same batch can't collide
    with this one either.
    """
    if isinstance(item, dict):
        if isinstance(item.get("id"), str) and item["id"]:
            candidate = item["id"]
            while candidate in existing_ids:
                candidate = f"{item['id']}-{uuid.uuid4().hex[:4]}"
            item["id"] = candidate
            existing_ids.add(candidate)
        for v in item.values():
            dedupe_all_ids(v, existing_ids)
    elif isinstance(item, list):
        for x in item:
            dedupe_all_ids(x, existing_ids)
