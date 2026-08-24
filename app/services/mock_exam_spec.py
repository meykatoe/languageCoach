"""Full-length TOEIC mock exam assembly: the fixed part/question-count
structure of a real TOEIC test form, and the two ways to fill it (sample
from the existing question bank, or have AI generate an entirely fresh set
of items in the same shape).
"""
import random
from dataclasses import dataclass

from openai import APIError
from sqlalchemy.orm import Session

from app.models import Question
from app.services.id_dedup import collect_all_ids, dedupe_all_ids
from app.services.openai_service import generate_questions

LISTENING_MINUTES = 45
READING_MINUTES = 75

AI_BATCH_SIZE = 5


@dataclass(frozen=True)
class PartSpec:
    section: str
    part: str
    qtype: str
    count: int  # number of bank rows / conversations / passages, not sub-questions


# Approximates the real TOEIC test form: Listening 100Q/45min (Parts 1-4),
# Reading 100Q/75min (Parts 5-7). Counts are of top-level items (a single
# photo/question, a conversation, a passage) since Part 3/4/6/7 items each
# carry multiple sub-questions of their own.
TOEIC_SPEC: dict[str, list[PartSpec]] = {
    "Listening": [
        PartSpec("Listening", "Part 1: Photographs", "questions", 6),
        PartSpec("Listening", "Part 2: Question-Response", "questions", 25),
        PartSpec("Listening", "Part 3: Conversations", "conversations", 13),
        PartSpec("Listening", "Part 4: Talks", "talks", 10),
    ],
    "Reading": [
        PartSpec("Reading", "Part 5: Incomplete Sentences", "questions", 30),
        PartSpec("Reading", "Part 6: Text Completion", "passages", 4),
        PartSpec("Reading", "Part 7: Reading Comprehension", "singlePassages", 10),
        PartSpec("Reading", "Part 7: Reading Comprehension", "doublePassages", 2),
        PartSpec("Reading", "Part 7: Reading Comprehension", "triplePassages", 3),
    ],
}


class AssemblyError(RuntimeError):
    """Raised when a full mock exam can't be assembled (bank pool too
    small, or the underlying AI generation call failed)."""


def _bank_items(db: Session, exam: str, spec: PartSpec) -> list[dict]:
    rows = (
        db.query(Question)
        .filter(Question.exam == exam, Question.part == spec.part, Question.qtype == spec.qtype)
        .all()
    )
    if len(rows) < spec.count:
        raise AssemblyError(
            f"題庫中「{spec.part}」({spec.qtype})目前只有 {len(rows)} 題,"
            f"不足以組成完整考卷所需的 {spec.count} 題。"
        )
    chosen = random.sample(rows, spec.count)
    return [dict(row.content) for row in chosen]


def _ai_items(db: Session, exam: str, spec: PartSpec, existing_ids: set[str]) -> list[dict]:
    template = (
        db.query(Question)
        .filter(Question.exam == exam, Question.part == spec.part, Question.qtype == spec.qtype)
        .first()
    )
    if template is None:
        raise AssemblyError(f"找不到「{spec.part}」({spec.qtype})的現有題目可作為 AI 出題的格式範本。")

    items: list[dict] = []
    remaining = spec.count
    while remaining > 0:
        batch = min(AI_BATCH_SIZE, remaining)
        try:
            generated = generate_questions(exam, spec.section, spec.part, template.content, batch)
        except RuntimeError as exc:
            raise AssemblyError(str(exc)) from exc
        except APIError as exc:
            raise AssemblyError(
                f"OpenAI API 呼叫失敗,請確認 ⚙️ 設定頁的 API Key 是否正確: {exc}"
            ) from exc
        except (ValueError, TypeError) as exc:
            raise AssemblyError(f"AI 出題回傳格式錯誤: {exc}") from exc

        for item in generated:
            if not isinstance(item, dict):
                continue
            if not isinstance(item.get("id"), str) or not item["id"]:
                item["id"] = f"mockexam-{spec.qtype}-{len(items)}"
            dedupe_all_ids(item, existing_ids)
            items.append(item)
        remaining -= batch

    return items[: spec.count]


def assemble_section(
    db: Session, exam: str, section: str, mode: str, existing_ids: set[str] | None = None
) -> list[dict]:
    """Returns a flat list of {part, qtype, item} dicts for every top-level
    item (photo/question/conversation/passage/...) in this section, per
    TOEIC_SPEC. `existing_ids` (required for mode="ai_generated") is the
    growing set of ids already used anywhere in this exam session, so ids
    stay unique across every part/section assembled for the same sitting.
    """
    out: list[dict] = []
    for spec in TOEIC_SPEC[section]:
        if mode == "ai_generated":
            assert existing_ids is not None
            items = _ai_items(db, exam, spec, existing_ids)
        else:
            items = _bank_items(db, exam, spec)
        for item in items:
            out.append({"part": spec.part, "qtype": spec.qtype, "item": item})
    return out


def assemble_full_exam(db: Session, exam: str, mode: str) -> dict[str, list[dict]]:
    """Assembles both sections of a full mock exam up front, so the reading
    section is guaranteed ready by the time the listening section is
    submitted (no risk of AI generation failing mid-exam).
    """
    existing_ids = collect_all_ids(db) if mode == "ai_generated" else None
    return {
        "Listening": assemble_section(db, exam, "Listening", mode, existing_ids),
        "Reading": assemble_section(db, exam, "Reading", mode, existing_ids),
    }

