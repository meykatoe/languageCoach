from typing import Any, Optional

from fastapi import APIRouter, Depends
from openai import APIError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Attempt, Question
from app.schemas import GradedAnswer, PracticeSubmitRequest, PracticeSubmitResponse
from app.services.openai_service import explain_mistake

router = APIRouter(prefix="/api/practice", tags=["practice"])


def _generate_mistake_note(exam: str, node: dict, expected: Any, submitted: Any) -> Optional[str]:
    """Best-effort AI explanation of a wrong answer, for the error notebook.
    Never raises: if the AI call fails (no API key, network error, ...), the
    submission should still succeed without a note.
    """
    try:
        return explain_mistake(exam, node, expected, submitted)
    except (RuntimeError, APIError, ValueError):
        return None


def _find_node_by_id(node: Any, target_id: str) -> Optional[dict]:
    """Depth-first search for a dict with id == target_id anywhere inside a
    question's JSON content (handles nested sub-questions in conversations,
    passages, cue cards, etc.).
    """
    if isinstance(node, dict):
        if node.get("id") == target_id:
            return node
        for value in node.values():
            found = _find_node_by_id(value, target_id)
            if found is not None:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _find_node_by_id(item, target_id)
            if found is not None:
                return found
    return None


def _answers_match(expected: Any, submitted: Any) -> bool:
    if isinstance(expected, list):
        if isinstance(submitted, list):
            return sorted(str(x).strip().upper() for x in expected) == sorted(
                str(x).strip().upper() for x in submitted
            )
        return False
    return str(expected).strip().upper() == str(submitted).strip().upper()


@router.post("/submit", response_model=PracticeSubmitResponse)
def submit_practice(payload: PracticeSubmitRequest, db: Session = Depends(get_db)):
    results: list[GradedAnswer] = []
    correct_count = 0
    graded_count = 0

    all_questions = db.query(Question).all()

    for ans in payload.answers:
        node = None
        parent: Optional[Question] = None
        for q in all_questions:
            node = _find_node_by_id(q.content, ans.source_id)
            if node is not None:
                parent = q
                break

        expected = node.get("answer") if node else None
        is_correct: Optional[bool] = None
        note: Optional[str] = None
        if expected is not None:
            is_correct = _answers_match(expected, ans.answer)
            graded_count += 1
            if is_correct:
                correct_count += 1
            elif parent is not None:
                note = _generate_mistake_note(parent.exam, node, expected, ans.answer)

            if parent is not None:
                db.add(
                    Attempt(
                        exam=parent.exam,
                        section=parent.section,
                        part=parent.part,
                        source_id=ans.source_id,
                        item_type="objective",
                        is_correct=is_correct,
                        detail={
                            "correctAnswer": expected,
                            "submittedAnswer": ans.answer,
                            "note": note,
                        },
                    )
                )

        results.append(
            GradedAnswer(
                source_id=ans.source_id,
                correct=is_correct,
                correctAnswer=expected,
                submittedAnswer=ans.answer,
                note=note,
            )
        )

    db.commit()

    return PracticeSubmitResponse(
        total=len(payload.answers),
        graded=graded_count,
        correct=correct_count,
        results=results,
    )
