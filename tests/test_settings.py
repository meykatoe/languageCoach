import os

import app.routers.generate as generate_module
from app.services import openai_service


def test_get_settings_defaults_to_env(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    res = client.get("/api/settings")
    assert res.status_code == 200
    data = res.json()
    assert data["has_api_key"] is False
    assert data["api_key_source"] == "none"
    assert data["openai_model"]  # falls back to DEFAULT_MODEL


def test_save_and_read_back_api_key(client):
    res = client.post("/api/settings", json={"openai_api_key": "sk-test-1234", "openai_model": "gpt-4o"})
    assert res.status_code == 200
    data = res.json()
    assert data["has_api_key"] is True
    assert data["api_key_source"] == "database"
    assert data["api_key_hint"] == "...1234"
    assert data["openai_model"] == "gpt-4o"

    res2 = client.get("/api/settings")
    data2 = res2.json()
    assert data2["has_api_key"] is True
    assert data2["openai_model"] == "gpt-4o"


def test_clear_api_key_falls_back_to_env(client, monkeypatch):
    client.post("/api/settings", json={"openai_api_key": "sk-test-5678"})
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env-fallback")

    res = client.post("/api/settings", json={"clear_api_key": True})
    data = res.json()
    assert data["has_api_key"] is True
    assert data["api_key_source"] == "environment"


def test_resolve_config_prefers_database_over_env(client, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env-should-not-be-used")
    client.post("/api/settings", json={"openai_api_key": "sk-db-should-win", "openai_model": "gpt-4.1"})

    api_key, model = openai_service.resolve_config()
    assert api_key == "sk-db-should-win"
    assert model == "gpt-4.1"


def test_generate_uses_saved_settings_without_error(client, monkeypatch):
    # Ensure a key is configured via the settings endpoint, then confirm the
    # generate router successfully calls through to the (mocked) OpenAI call
    # without raising the "not configured" RuntimeError.
    client.post("/api/settings", json={"openai_api_key": "sk-configured"})

    def fake_generate_questions(exam, section, part, example_item, count):
        return [
            {"id": f"ai-settings-test-{i}", "sentence": "x", "options": ["A. a", "B. b"], "answer": "A"}
            for i in range(count)
        ]

    monkeypatch.setattr(generate_module, "generate_questions", fake_generate_questions)

    res = client.post(
        "/api/generate",
        json={"exam": "TOEIC", "section": "Reading", "part": "Part 5: Incomplete Sentences", "count": 1},
    )
    assert res.status_code == 200


def test_grading_openai_apierror_returns_502(client, monkeypatch):
    import httpx
    from openai import APIError

    import app.routers.grading as grading_module

    def raise_api_error(*args, **kwargs):
        req = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
        raise APIError("boom", req, body=None)

    monkeypatch.setattr(grading_module, "grade_response", raise_api_error)

    res = client.post(
        "/api/grading/writing",
        json={"source_id": "ielts-w2-01", "exam": "IELTS", "essay": "test essay"},
    )
    assert res.status_code == 502
