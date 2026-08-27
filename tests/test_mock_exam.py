import app.routers.mock_exam as mock_exam_router
import app.services.mock_exam_spec as spec_module


def _start(client, mode="bank"):
    res = client.post("/api/mock-exam/start", json={"exam": "TOEIC", "mode": mode})
    assert res.status_code == 200, res.text
    return res.json()


def _answers_for(questions):
    """Answer every gradeable node correctly, using the stored `answer`."""
    answers = []

    def walk(node):
        if isinstance(node, dict):
            if "id" in node and "answer" in node:
                answers.append({"source_id": node["id"], "answer": node["answer"]})
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for x in node:
                walk(x)

    for q in questions:
        walk(q["content"])
    return answers


def test_start_assembles_full_toeic_form_from_bank(client):
    data = _start(client)
    assert data["exam"] == "TOEIC"
    assert data["mode"] == "bank"
    assert data["status"] == "listening"

    listening = data["listening"]["questions"]
    # Part 1(6) + Part 2(25) + Part 3(13 conversations) + Part 4(10 talks)
    assert len(listening) == 6 + 25 + 13 + 10
    parts = {q["part"] for q in listening}
    assert parts == {
        "Part 1: Photographs",
        "Part 2: Question-Response",
        "Part 3: Conversations",
        "Part 4: Talks",
    }


def test_full_mock_exam_flow_and_scoring(client):
    data = _start(client)
    session_id = data["id"]
    listening_questions = data["listening"]["questions"]

    answers = _answers_for(listening_questions)
    res = client.post(f"/api/mock-exam/{session_id}/submit-listening", json={"answers": answers})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "reading"
    reading_questions = body["reading"]["questions"]
    assert len(reading_questions) == 30 + 4 + 10 + 2 + 3

    reading_answers = _answers_for(reading_questions)
    res2 = client.post(f"/api/mock-exam/{session_id}/submit-reading", json={"answers": reading_answers})
    assert res2.status_code == 200, res2.text
    result = res2.json()
    assert result["status"] == "completed"
    # every answer was correct -> full scaled score both sections
    assert result["listening"]["scaled_score"] == 495
    assert result["reading"]["scaled_score"] == 495
    assert result["scaled_total"] == 990
    assert result["listening"]["raw_correct"] == result["listening"]["raw_total"]

    # resuming a completed session returns the same final result
    res3 = client.get(f"/api/mock-exam/{session_id}")
    assert res3.status_code == 200
    assert res3.json()["result"]["scaled_total"] == 990


def test_completed_exam_includes_ai_advice(client, monkeypatch):
    captured = {}

    def fake_advice(user_id, exam, listening_score, reading_score, part_breakdown):
        captured["args"] = (exam, listening_score, reading_score, part_breakdown)
        return "先加強 Part 5 文法題,聽力表現不錯。"

    monkeypatch.setattr(mock_exam_router, "generate_mock_exam_advice", fake_advice)

    data = _start(client)
    session_id = data["id"]
    res = client.post(
        f"/api/mock-exam/{session_id}/submit-listening",
        json={"answers": _answers_for(data["listening"]["questions"])},
    )
    reading_questions = res.json()["reading"]["questions"]
    res2 = client.post(
        f"/api/mock-exam/{session_id}/submit-reading",
        json={"answers": _answers_for(reading_questions)},
    )
    result = res2.json()
    assert result["advice"] == "先加強 Part 5 文法題,聽力表現不錯。"
    assert captured["args"][0] == "TOEIC"
    assert captured["args"][3]  # non-empty per-part breakdown

    # advice is persisted and returned again on resume
    res3 = client.get(f"/api/mock-exam/{session_id}")
    assert res3.json()["result"]["advice"] == "先加強 Part 5 文法題,聽力表現不錯。"


def test_advice_generation_failure_does_not_break_submission(client, monkeypatch):
    def failing_advice(*args, **kwargs):
        raise RuntimeError("no api key")

    monkeypatch.setattr(mock_exam_router, "generate_mock_exam_advice", failing_advice)

    data = _start(client)
    session_id = data["id"]
    res = client.post(
        f"/api/mock-exam/{session_id}/submit-listening",
        json={"answers": _answers_for(data["listening"]["questions"])},
    )
    reading_questions = res.json()["reading"]["questions"]
    res2 = client.post(
        f"/api/mock-exam/{session_id}/submit-reading",
        json={"answers": _answers_for(reading_questions)},
    )
    assert res2.status_code == 200
    assert res2.json()["advice"] is None


def test_cannot_resubmit_listening_twice(client):
    data = _start(client)
    session_id = data["id"]
    answers = _answers_for(data["listening"]["questions"])
    res1 = client.post(f"/api/mock-exam/{session_id}/submit-listening", json={"answers": answers})
    assert res1.status_code == 200
    res2 = client.post(f"/api/mock-exam/{session_id}/submit-listening", json={"answers": answers})
    assert res2.status_code == 409


def test_submit_reading_before_listening_rejected(client):
    data = _start(client)
    session_id = data["id"]
    res = client.post(f"/api/mock-exam/{session_id}/submit-reading", json={"answers": []})
    assert res.status_code == 409


def test_unknown_session_returns_404(client):
    res = client.get("/api/mock-exam/999999")
    assert res.status_code == 404


def test_unsupported_exam_rejected(client):
    res = client.post("/api/mock-exam/start", json={"exam": "IELTS", "mode": "bank"})
    assert res.status_code == 400


def test_history_lists_sessions(client):
    _start(client)
    res = client.get("/api/mock-exam/history")
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_ai_generated_mode_uses_generate_questions(client, monkeypatch):
    calls = []

    def fake_generate_questions(user_id, exam, section, part, example_item, count):
        calls.append((part, count))
        items = []
        for i in range(count):
            item = {"id": f"{part}-fake-{i}", "answer": "B"}
            if "sentence" in example_item or "prompt" in example_item or "photoDescription" in example_item:
                item["options"] = ["A. x", "B. y", "C. z", "D. w"]
            elif "transcript" in example_item:
                item["transcript"] = "fake transcript"
                item["questions"] = [{"id": f"{part}-fake-{i}-q1", "answer": "A", "options": ["A. x", "B. y"]}]
            elif "text" in example_item and "blanks" in example_item:
                item["text"] = "fake ___(1)___"
                item["blanks"] = [{"id": f"{part}-fake-{i}-b1", "answer": "A", "options": ["A. x", "B. y"]}]
            elif "passages" in example_item:
                item["passages"] = [{"label": "A", "text": "fake"}]
                item["questions"] = [{"id": f"{part}-fake-{i}-q1", "answer": "A", "options": ["A. x", "B. y"]}]
            elif "passage" in example_item:
                item["passage"] = "fake passage"
                item["questions"] = [{"id": f"{part}-fake-{i}-q1", "answer": "A", "options": ["A. x", "B. y"]}]
            items.append(item)
        return items

    monkeypatch.setattr(spec_module, "generate_questions", fake_generate_questions)

    data = _start(client, mode="ai_generated")
    assert data["mode"] == "ai_generated"
    listening = data["listening"]["questions"]
    assert len(listening) == 6 + 25 + 13 + 10
    assert calls  # generate_questions was actually invoked

    # ids must be unique across the whole assembled exam
    ids = [q["source_id"] for q in listening]
    assert len(ids) == len(set(ids))
