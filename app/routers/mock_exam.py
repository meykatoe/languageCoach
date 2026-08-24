import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ExamSession
from app.schemas import (
    GradedAnswer,
    MockExamFinalResult,
    MockExamHistoryItem,
    MockExamListeningSubmitResponse,
    MockExamQuestion,
    MockExamSectionPayload,
    MockExamSectionScore,
    MockExamSectionSubmitRequest,
    MockExamStartRequest,
    MockExamStartResponse,
    MockExamStateResponse,
)
from app.services.grading import answers_match, find_node_by_id
from app.services.mock_exam_spec import (
    LISTENING_MINUTES,
    READING_MINUTES,
    AssemblyError,
    assemble_full_exam,
)
from app.services.scoring import toeic_scaled_score

router = APIRouter(prefix="/api/mock-exam", tags=["mock-exam"])


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def _to_mock_questions(section: str, entries: list[dict], mode: str) -> list[MockExamQuestion]:
    source_file = "mock-exam-ai" if mode == "ai_generated" else "mock-exam-bank"
    return [
        MockExamQuestion(
            source_id=entry["item"].get("id", ""),
            exam="TOEIC",
            section=section,
            part=entry["part"],
            qtype=entry["qtype"],
            source_file=source_file,
            content=entry["item"],
        )
        for entry in entries
    ]


def _section_payload(session: ExamSession, section: str) -> MockExamSectionPayload:
    entries = session.content[section]
    deadline = session.listening_deadline if section == "Listening" else session.reading_deadline
    return MockExamSectionPayload(
        section=section,
        deadline=deadline,
        questions=_to_mock_questions(section, entries, session.mode),
    )


def _grade_section(entries: list[dict], answers: list) -> tuple[int, int, list[GradedAnswer]]:
    results: list[GradedAnswer] = []
    correct = 0
    graded = 0
    for ans in answers:
        node = None
        for entry in entries:
            node = find_node_by_id(entry["item"], ans.source_id)
            if node is not None:
                break
        expected = node.get("answer") if node else None
        is_correct: Optional[bool] = None
        if expected is not None:
            is_correct = answers_match(expected, ans.answer)
            graded += 1
            if is_correct:
                correct += 1
        results.append(
            GradedAnswer(
                source_id=ans.source_id,
                correct=is_correct,
                correctAnswer=expected,
                submittedAnswer=ans.answer,
            )
        )
    return correct, graded, results


def _get_session(db: Session, session_id: int) -> ExamSession:
    session = db.get(ExamSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="找不到這場模考。")
    return session


@router.post("/start", response_model=MockExamStartResponse)
def start_mock_exam(payload: MockExamStartRequest, db: Session = Depends(get_db)):
    if payload.exam != "TOEIC":
        raise HTTPException(status_code=400, detail="目前僅支援 TOEIC 正式模考模式。")

    try:
        content = assemble_full_exam(db, payload.exam, payload.mode)
    except AssemblyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    now = _now()
    session = ExamSession(
        exam=payload.exam,
        mode=payload.mode,
        status="listening",
        created_at=now,
        listening_deadline=now + datetime.timedelta(minutes=LISTENING_MINUTES),
        content=content,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return MockExamStartResponse(
        id=session.id,
        exam=session.exam,
        mode=session.mode,
        status=session.status,
        listening=_section_payload(session, "Listening"),
    )


@router.get("/history", response_model=list[MockExamHistoryItem])
def mock_exam_history(limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db)):
    rows = db.query(ExamSession).order_by(ExamSession.created_at.desc()).limit(limit).all()
    return rows


@router.get("/{session_id}", response_model=MockExamStateResponse)
def get_mock_exam(session_id: int, db: Session = Depends(get_db)):
    session = _get_session(db, session_id)

    result = None
    if session.status == "completed":
        result = MockExamFinalResult(
            id=session.id,
            exam=session.exam,
            status=session.status,
            listening=MockExamSectionScore(
                raw_correct=session.raw_listening,
                raw_total=session.raw_listening_total,
                scaled_score=session.scaled_listening,
            ),
            reading=MockExamSectionScore(
                raw_correct=session.raw_reading,
                raw_total=session.raw_reading_total,
                scaled_score=session.scaled_reading,
            ),
            scaled_total=session.scaled_total,
            listening_results=session.listening_results or [],
            reading_results=session.reading_results or [],
        )

    return MockExamStateResponse(
        id=session.id,
        exam=session.exam,
        mode=session.mode,
        status=session.status,
        listening_deadline=session.listening_deadline,
        reading_deadline=session.reading_deadline,
        listening=_section_payload(session, "Listening") if session.status == "listening" else None,
        reading=_section_payload(session, "Reading") if session.status == "reading" else None,
        result=result,
    )


@router.post("/{session_id}/submit-listening", response_model=MockExamListeningSubmitResponse)
def submit_listening(session_id: int, payload: MockExamSectionSubmitRequest, db: Session = Depends(get_db)):
    session = _get_session(db, session_id)
    if session.status != "listening":
        raise HTTPException(status_code=409, detail="這場模考的聽力測驗已經送出過了。")

    correct, graded, results = _grade_section(session.content["Listening"], payload.answers)
    session.raw_listening = correct
    session.raw_listening_total = graded
    session.scaled_listening = toeic_scaled_score(correct, graded)
    session.listening_results = [r.model_dump() for r in results]

    now = _now()
    session.status = "reading"
    session.reading_deadline = now + datetime.timedelta(minutes=READING_MINUTES)
    db.commit()
    db.refresh(session)

    return MockExamListeningSubmitResponse(
        id=session.id,
        status=session.status,
        reading=_section_payload(session, "Reading"),
    )


@router.post("/{session_id}/submit-reading", response_model=MockExamFinalResult)
def submit_reading(session_id: int, payload: MockExamSectionSubmitRequest, db: Session = Depends(get_db)):
    session = _get_session(db, session_id)
    if session.status != "reading":
        raise HTTPException(status_code=409, detail="這場模考的閱讀測驗尚未開始，或已經送出過了。")

    correct, graded, results = _grade_section(session.content["Reading"], payload.answers)
    session.raw_reading = correct
    session.raw_reading_total = graded
    session.scaled_reading = toeic_scaled_score(correct, graded)
    session.reading_results = [r.model_dump() for r in results]

    session.scaled_total = session.scaled_listening + session.scaled_reading
    session.status = "completed"
    session.submitted_at = _now()
    db.commit()
    db.refresh(session)

    return MockExamFinalResult(
        id=session.id,
        exam=session.exam,
        status=session.status,
        listening=MockExamSectionScore(
            raw_correct=session.raw_listening,
            raw_total=session.raw_listening_total,
            scaled_score=session.scaled_listening,
        ),
        reading=MockExamSectionScore(
            raw_correct=session.raw_reading,
            raw_total=session.raw_reading_total,
            scaled_score=session.scaled_reading,
        ),
        scaled_total=session.scaled_total,
        listening_results=session.listening_results,
        reading_results=session.reading_results,
    )
