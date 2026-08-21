import app.routers.generate as generate_module


def test_generate_unknown_exam_section_404(client):
    res = client.post(
        "/api/generate",
        json={"exam": "TOEIC", "section": "DoesNotExist", "count": 1},
    )
    assert res.status_code == 404


def test_generate_creates_questions(client, monkeypatch):
    def fake_generate_questions(exam, section, part, example_item, count):
        assert exam == "TOEIC"
        assert section == "Reading"
        return [
            {
                "id": "toeic-r5-001",  # deliberately collides with an existing source_id
                "sentence": "New sentence ______ testing.",
                "options": ["A. for", "B. to", "C. at", "D. in"],
                "answer": "A",
            }
            for _ in range(count)
        ]

    monkeypatch.setattr(generate_module, "generate_questions", fake_generate_questions)

    res = client.post(
        "/api/generate",
        json={"exam": "TOEIC", "section": "Reading", "part": "Part 5: Incomplete Sentences", "count": 2},
    )
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 2
    ids = {i["source_id"] for i in items}
    assert len(ids) == 2  # collisions were resolved to unique ids
    assert all(i["source_file"] == "ai-generated" for i in items)
    assert all(i["exam"] == "TOEIC" and i["section"] == "Reading" for i in items)

    # generated items should now be fetchable through the normal questions endpoint
    res2 = client.get("/api/questions", params={"exam": "TOEIC", "section": "Reading", "limit": 100})
    fetched_ids = {q["source_id"] for q in res2.json()}
    assert ids <= fetched_ids


def test_generate_service_unavailable_returns_503(client, monkeypatch):
    def raise_runtime(*args, **kwargs):
        raise RuntimeError("OPENAI_API_KEY is not set.")

    monkeypatch.setattr(generate_module, "generate_questions", raise_runtime)

    res = client.post(
        "/api/generate",
        json={"exam": "IELTS", "section": "Writing", "count": 1},
    )
    assert res.status_code == 503


def test_generate_malformed_ai_response_returns_502(client, monkeypatch):
    def raise_value_error(*args, **kwargs):
        raise ValueError("bad json")

    monkeypatch.setattr(generate_module, "generate_questions", raise_value_error)

    res = client.post(
        "/api/generate",
        json={"exam": "IELTS", "section": "Writing", "count": 1},
    )
    assert res.status_code == 502
