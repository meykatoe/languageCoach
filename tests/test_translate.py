import app.routers.translate as translate_module


def test_translate_text_returns_translation(client, monkeypatch):
    monkeypatch.setattr(translate_module, "translate_text", lambda text: f"[譯] {text}")

    res = client.post("/api/translate/text", json={"text": "The report is due tomorrow."})
    assert res.status_code == 200
    assert res.json() == {"translation": "[譯] The report is due tomorrow.", "added_to_vocab": False}


def test_translate_text_rejects_empty_text(client):
    res = client.post("/api/translate/text", json={"text": ""})
    assert res.status_code == 422


def test_translate_text_without_api_key_returns_503(client, monkeypatch):
    client.post("/api/settings", json={"clear_api_key": True})
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    res = client.post("/api/translate/text", json={"text": "hello"})
    assert res.status_code == 503


def test_translate_unknown_question_404(client):
    res = client.post("/api/translate", json={"source_id": "does-not-exist"})
    assert res.status_code == 404


def test_translate_without_api_key_returns_503(client, monkeypatch):
    # other tests in this session may have saved a key via /api/settings;
    # clear it explicitly so this test is independent of ordering.
    client.post("/api/settings", json={"clear_api_key": True})
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    res = client.post("/api/translate", json={"source_id": "toeic-r5-001"})
    assert res.status_code == 503


def test_translate_returns_translation(client, monkeypatch):
    def fake_translate_text(text):
        assert "handbook" in text
        assert "\nB\n" not in text  # the top-level "answer" key should be excluded from the source text
        return "新進員工手冊概述了所有公司政策..."

    monkeypatch.setattr(translate_module, "translate_text", fake_translate_text)

    res = client.post("/api/translate", json={"source_id": "toeic-r5-001"})
    assert res.status_code == 200
    assert res.json() == {"translation": "新進員工手冊概述了所有公司政策...", "added_to_vocab": None}
