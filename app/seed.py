"""Import the JSON question bank in examQuestions/create/ into the database.

Every JSON file has metadata at the top level (exam, section, part /
instructions) plus one or more list-valued keys holding the actual items
(questions, conversations, talks, passages, singlePassages, doublePassages,
triplePassages, tasks, prompts, cueCards, topics, topicGroups, ...). Each
item in those lists becomes one row in the `questions` table, keyed by its
own `id` field as `source_id`. Re-running this script is idempotent.
"""

import json
from pathlib import Path

from app.database import Base, SessionLocal, engine
from app.models import Question

QUESTIONS_ROOT = Path(__file__).resolve().parent.parent / "examQuestions" / "create"

# Keys at the top level of a question-bank JSON file that hold a list of
# individual practice items (as opposed to plain metadata).
ITEM_LIST_KEYS = [
    "questions",
    "conversations",
    "talks",
    "lectures",
    "passages",
    "singlePassages",
    "doublePassages",
    "triplePassages",
    "tasks",
    "prompts",
    "cueCards",
    "topics",
    "topicGroups",
]


def load_bank_files():
    return sorted(QUESTIONS_ROOT.rglob("*.json"))


def seed(verbose: bool = True) -> int:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    count = 0
    try:
        for path in load_bank_files():
            data = json.loads(path.read_text(encoding="utf-8"))
            exam = data.get("exam", "UNKNOWN")
            section = data.get("section", "UNKNOWN")
            part = data.get("part")

            for list_key in ITEM_LIST_KEYS:
                items = data.get(list_key)
                if not isinstance(items, list):
                    continue
                for item in items:
                    if not isinstance(item, dict) or "id" not in item:
                        continue
                    source_id = item["id"]
                    existing = (
                        db.query(Question)
                        .filter(Question.source_id == source_id)
                        .one_or_none()
                    )
                    if existing:
                        existing.exam = exam
                        existing.section = section
                        existing.part = part
                        existing.qtype = list_key
                        existing.source_file = str(path.relative_to(QUESTIONS_ROOT))
                        existing.content = item
                    else:
                        db.add(
                            Question(
                                source_id=source_id,
                                exam=exam,
                                section=section,
                                part=part,
                                qtype=list_key,
                                source_file=str(path.relative_to(QUESTIONS_ROOT)),
                                content=item,
                            )
                        )
                        count += 1
        db.commit()
    finally:
        db.close()
    if verbose:
        print(f"Seeded {count} new questions (existing rows updated in place).")
    return count


if __name__ == "__main__":
    seed()
