import app.routers.translate as translate_module
import app.services.vocab as vocab_module


def _fake_entry(word):
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
                        "example_en": "This is a test.",
                        "example_zh": "這是一個測試。",
                    }
                ],
            }
        ],
        "synonyms": ["sample"],
        "antonyms": [],
        "collocations": [],
        "wordFamily": [],
        "memoryTip": "記憶技巧",
    }


def test_selecting_a_single_word_adds_it_to_vocab_with_full_detail(client, monkeypatch):
    monkeypatch.setattr(translate_module, "translate_text", lambda text: f"[譯] {text}")
    monkeypatch.setattr(vocab_module, "generate_vocab_entry", _fake_entry)

    res = client.post("/api/translate/text", json={"text": "Persistence"})
    assert res.status_code == 200
    assert res.json()["added_to_vocab"] is True

    list_res = client.get("/api/vocab")
    entry = next(e for e in list_res.json() if e["word"] == "persistence")
    assert entry["detail"]["phonetic"] == "/test/"
    assert entry["detail"]["entries"][0]["partOfSpeech"] == "noun"


def test_selecting_a_phrase_is_not_added_to_vocab(client, monkeypatch):
    monkeypatch.setattr(translate_module, "translate_text", lambda text: f"[譯] {text}")
    monkeypatch.setattr(vocab_module, "generate_vocab_entry", _fake_entry)

    res = client.post("/api/translate/text", json={"text": "due tomorrow"})
    assert res.status_code == 200
    assert res.json()["added_to_vocab"] is False

    list_res = client.get("/api/vocab")
    assert all(e["word"] != "due tomorrow" for e in list_res.json())


def test_selecting_the_same_word_twice_does_not_duplicate(client, monkeypatch):
    monkeypatch.setattr(translate_module, "translate_text", lambda text: f"[譯] {text}")
    monkeypatch.setattr(vocab_module, "generate_vocab_entry", _fake_entry)

    client.post("/api/translate/text", json={"text": "Resilience"})
    client.post("/api/translate/text", json={"text": "resilience"})

    matches = [e for e in client.get("/api/vocab").json() if e["word"] == "resilience"]
    assert len(matches) == 1


def test_delete_vocab_entry(client, monkeypatch):
    monkeypatch.setattr(translate_module, "translate_text", lambda text: f"[譯] {text}")
    monkeypatch.setattr(vocab_module, "generate_vocab_entry", _fake_entry)
    client.post("/api/translate/text", json={"text": "Ephemeral"})
    entry = next(e for e in client.get("/api/vocab").json() if e["word"] == "ephemeral")

    del_res = client.delete(f"/api/vocab/{entry['id']}")
    assert del_res.status_code == 204
    assert all(e["word"] != "ephemeral" for e in client.get("/api/vocab").json())


def test_regenerate_vocab_entry(client, monkeypatch):
    # First generation "fails" (simulating no API key at add-time), leaving detail null.
    def raise_runtime(word):
        raise RuntimeError("尚未設定 API Key")

    monkeypatch.setattr(translate_module, "translate_text", lambda text: f"[譯] {text}")
    monkeypatch.setattr(vocab_module, "generate_vocab_entry", raise_runtime)
    client.post("/api/translate/text", json={"text": "Diligence"})
    entry = next(e for e in client.get("/api/vocab").json() if e["word"] == "diligence")
    assert entry["detail"] is None

    monkeypatch.setattr(vocab_module, "generate_vocab_entry", _fake_entry)
    import app.routers.vocab as vocab_router

    monkeypatch.setattr(vocab_router, "generate_vocab_entry", _fake_entry)
    res = client.post(f"/api/vocab/{entry['id']}/regenerate")
    assert res.status_code == 200
    assert res.json()["detail"]["phonetic"] == "/test/"
