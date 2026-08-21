from typing import Any, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Question
from app.schemas import GradedAnswer, PracticeSubmitRequest, PracticeSubmitResponse

router = APIRouter(prefix="/api/practice", tags=["practice"])


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
        for q in all_questions:
            node = _find_node_by_id(q.content, ans.source_id)
            if node is not None:
                break

        expected = node.get("answer") if node else None
        is_correct: Optional[bool] = None
        if expected is not None:
            is_correct = _answers_match(expected, ans.answer)
            graded_count += 1
            if is_correct:
                correct_count += 1

        results.append(
            GradedAnswer(
                source_id=ans.source_id,
                correct=is_correct,
                correctAnswer=expected,
                submittedAnswer=ans.answer,
            )
        )

    return PracticeSubmitResponse(
        total=len(payload.answers),
        graded=graded_count,
        correct=correct_count,
        results=results,
    )
