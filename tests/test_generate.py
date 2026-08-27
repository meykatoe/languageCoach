import app.routers.generate as generate_module


def test_generate_unknown_exam_section_404(client):
    res = client.post(
        "/api/generate",
        json={"exam": "TOEIC", "section": "DoesNotExist", "count": 1},
    )
    assert res.status_code == 404


def test_generate_creates_questions(client, monkeypatch):
    def fake_generate_questions(user_id, exam, section, part, example_item, count):
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

    # generated items should now be fetchable through the normal questions endpoint.
    # /api/questions samples randomly up to `limit`, so filter down to the part
    # (well under the 100-row cap) rather than the whole section, which can hold
    # far more than 100 questions once the real question bank is seeded.
    res2 = client.get(
        "/api/questions",
        params={"exam": "TOEIC", "section": "Reading", "part": "Part 5: Incomplete Sentences", "limit": 100},
    )
    fetched_ids = {q["source_id"] for q in res2.json()}
    assert ids <= fetched_ids


def test_generate_dedupes_nested_sub_question_ids(client, monkeypatch):
    """Regression test: the AI is prompted to imitate an existing item's JSON
    shape, and can reuse that item's *nested* sub-question ids verbatim even
    though its own top-level id is unique. Before the fix, only the
    top-level id was deduped, so answering the new item's sub-question could
    silently get graded against the unrelated original question that
    already owned that nested id.
    """

    def fake_generate_questions(user_id, exam, section, part, example_item, count):
        return [
            {
                "id": "toeic-r7-single-99",
                "passage": "Bake Sale Fundraiser at Lincoln Elementary to raise money for new playground equipment.",
                "questions": [
                    {
                        "id": "toeic-r7-single-01-q1",  # collides with an existing nested id
                        "question": "What is the fundraiser raising money for?",
                        "options": ["A. A field trip", "B. New playground equipment", "C. Books", "D. A trophy"],
                        "answer": "B",
                    }
                ],
            }
        ]

    monkeypatch.setattr(generate_module, "generate_questions", fake_generate_questions)

    res = client.post(
        "/api/generate",
        json={"exam": "TOEIC", "section": "Reading", "part": "Part 7: Reading Comprehension", "count": 1},
    )
    assert res.status_code == 200
    created = res.json()[0]
    nested_id = created["content"]["questions"][0]["id"]
    assert nested_id != "toeic-r7-single-01-q1"  # renamed so it can no longer shadow the original

    # the pre-existing question's own nested id still resolves to ITSELF
    original = client.post(
        "/api/practice/submit", json={"answers": [{"source_id": "toeic-r7-single-01-q1", "answer": "B"}]}
    )
    assert original.json()["results"][0]["correctAnswer"] == "B"  # "For scheduled renovations"

    # the new item's (renamed) nested id resolves to the NEW item's own answer
    new_item = client.post("/api/practice/submit", json={"answers": [{"source_id": nested_id, "answer": "B"}]})
    assert new_item.json()["results"][0]["correct"] is True


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
