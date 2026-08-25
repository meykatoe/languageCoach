import app.routers.translate as translate_module
import app.services.vocab as vocab_module


def _fake_entry_with_example(word):
    return {
        "word": word,
        "phonetic": "/test/",
        "entries": [
            {
                "partOfSpeech": "noun",
                "definitions": [
                    {
                        "meaning_en": "a test meaning",
                        "meaning_zh": "測試意思",
                        "example_en": f"The {word} was clear to everyone.",
                        "example_zh": "這對每個人來說都很清楚。",
                    }
                ],
            }
        ],
        "synonyms": [],
        "antonyms": [],
        "collocations": [],
        "wordFamily": [],
        "memoryTip": "",
    }


def _fake_entry_without_matching_example(word):
    return {
        "word": word,
        "phonetic": "/test/",
        "entries": [
            {
                "partOfSpeech": "noun",
                "definitions": [
                    {
                        "meaning_en": "a test meaning",
                        "meaning_zh": "測試意思",
                        "example_en": "This sentence never mentions the target.",
                        "example_zh": "這句話沒有提到目標詞。",
                    }
                ],
            }
        ],
        "synonyms": [],
        "antonyms": [],
        "collocations": [],
        "wordFamily": [],
        "memoryTip": "",
    }


def _add_word(client, monkeypatch, word, entry_fn=_fake_entry_with_example):
    monkeypatch.setattr(translate_module, "translate_text", lambda text: f"[譯] {text}")
    monkeypatch.setattr(vocab_module, "generate_vocab_entry", entry_fn)
    client.post("/api/translate/text", json={"text": word})
    return next(e for e in client.get("/api/vocab").json() if e["word"] == word.lower())


def test_new_word_is_due_immediately_and_blanks_it_out_of_the_example(client, monkeypatch):
    entry = _add_word(client, monkeypatch, "Lucidity")

    res = client.get("/api/vocab/review/queue")
    assert res.status_code == 200
    item = next(q for q in res.json() if q["id"] == entry["id"])
    assert "lucidity" not in item["sentence"].lower()
    assert "_____" in item["sentence"]
    assert item["phonetic"] == "/test/"


def test_word_without_usable_example_is_skipped_from_the_queue(client, monkeypatch):
    entry = _add_word(client, monkeypatch, "Obscurity", entry_fn=_fake_entry_without_matching_example)

    ids = {q["id"] for q in client.get("/api/vocab/review/queue").json()}
    assert entry["id"] not in ids


def test_correct_answer_advances_interval_and_reschedules_out_of_the_queue(client, monkeypatch):
    entry = _add_word(client, monkeypatch, "Tenacity")

    res = client.post(f"/api/vocab/{entry['id']}/review", json={"answer": "Tenacity"})
    assert res.status_code == 200
    body = res.json()
    assert body["correct"] is True
    assert body["interval_days"] == 1

    ids = {q["id"] for q in client.get("/api/vocab/review/queue").json()}
    assert entry["id"] not in ids


def test_incorrect_answer_resets_interval_and_reports_the_correct_word(client, monkeypatch):
    entry = _add_word(client, monkeypatch, "Candor")

    res = client.post(f"/api/vocab/{entry['id']}/review", json={"answer": "wrongword"})
    assert res.status_code == 200
    body = res.json()
    assert body["correct"] is False
    assert body["correct_answer"] == "candor"
    assert body["interval_days"] == 1


def test_second_correct_answer_extends_interval_further_than_the_first(client, monkeypatch):
    entry = _add_word(client, monkeypatch, "Fortitude")

    first = client.post(f"/api/vocab/{entry['id']}/review", json={"answer": "fortitude"}).json()
    second = client.post(f"/api/vocab/{entry['id']}/review", json={"answer": "fortitude"}).json()
    assert second["interval_days"] > first["interval_days"]


def test_review_unknown_entry_returns_404(client):
    res = client.post("/api/vocab/999999/review", json={"answer": "anything"})
    assert res.status_code == 404


def test_due_count_reflects_review_state(client, monkeypatch):
    before = client.get("/api/vocab/review/due-count").json()["due"]

    entry = _add_word(client, monkeypatch, "Verity")
    after_add = client.get("/api/vocab/review/due-count").json()["due"]
    assert after_add == before + 1

    client.post(f"/api/vocab/{entry['id']}/review", json={"answer": "verity"})
    after_review = client.get("/api/vocab/review/due-count").json()["due"]
    assert after_review == before
