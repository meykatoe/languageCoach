def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_list_exams(client):
    res = client.get("/api/exams")
    assert res.status_code == 200
    rows = res.json()
    exams = {r["exam"] for r in rows}
    assert exams == {"TOEIC", "IELTS", "TOEFL"}
    assert sum(r["count"] for r in rows) > 100


def test_list_questions_filtered(client):
    res = client.get("/api/questions", params={"exam": "TOEIC", "section": "Reading", "limit": 5})
    assert res.status_code == 200
    rows = res.json()
    assert 0 < len(rows) <= 5
    assert all(r["exam"] == "TOEIC" and r["section"] == "Reading" for r in rows)


def test_toefl_listening_includes_lectures(client):
    res = client.get("/api/questions", params={"exam": "TOEFL", "section": "Listening", "limit": 20})
    assert res.status_code == 200
    qtypes = {r["qtype"] for r in res.json()}
    assert "lectures" in qtypes
    assert "conversations" in qtypes


def test_practice_submit_grades_correctly(client):
    res = client.post(
        "/api/practice/submit",
        json={"answers": [{"source_id": "toeic-r5-001", "answer": "B"}, {"source_id": "toeic-r5-001", "answer": "A"}]},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 2
    assert body["graded"] == 2
    assert body["correct"] == 1
    results = {i: r for i, r in enumerate(body["results"])}
    assert results[0]["correct"] is True
    assert results[1]["correct"] is False
    assert results[0]["correctAnswer"] == "B"


def test_practice_submit_unknown_id_not_graded(client):
    res = client.post(
        "/api/practice/submit",
        json={"answers": [{"source_id": "does-not-exist", "answer": "A"}]},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["graded"] == 0
    assert body["results"][0]["correct"] is None


def test_grading_writing_without_api_key_returns_503(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    res = client.post(
        "/api/grading/writing",
        json={"source_id": "ielts-w2-01", "exam": "IELTS", "essay": "test essay"},
    )
    assert res.status_code == 503


def test_grading_writing_unknown_question_404(client):
    res = client.post(
        "/api/grading/writing",
        json={"source_id": "does-not-exist", "exam": "IELTS", "essay": "test"},
    )
    assert res.status_code == 404


def test_history_reflects_submitted_attempts(client):
    before = client.get("/api/history").json()["total_attempts"]
    client.post(
        "/api/practice/submit",
        json={"answers": [{"source_id": "toeic-r5-002", "answer": "A"}]},
    )
    after = client.get("/api/history").json()["total_attempts"]
    assert after == before + 1
