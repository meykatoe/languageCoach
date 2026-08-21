import json

from app.database import SessionLocal
from app.models import Question
from app.seed import ITEM_LIST_KEYS, QUESTIONS_ROOT


def test_every_top_level_list_key_is_seeded():
    """Regression test: every list-valued key at the top level of every
    question-bank JSON file must be in ITEM_LIST_KEYS, otherwise those items
    silently never get imported (this happened once with TOEFL's "lectures"
    key).
    """
    missing = []
    for path in QUESTIONS_ROOT.rglob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        for key, value in data.items():
            if isinstance(value, list) and value and isinstance(value[0], dict) and "id" in value[0]:
                if key not in ITEM_LIST_KEYS:
                    missing.append(f"{path.name}:{key}")
    assert not missing, f"Top-level item lists not in ITEM_LIST_KEYS: {missing}"


def test_seeded_question_count_matches_bank_files():
    expected = 0
    for path in QUESTIONS_ROOT.rglob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        for key in ITEM_LIST_KEYS:
            items = data.get(key)
            if isinstance(items, list):
                expected += sum(1 for i in items if isinstance(i, dict) and "id" in i)

    db = SessionLocal()
    try:
        actual = db.query(Question).count()
    finally:
        db.close()

    assert actual == expected
