import app.routers.practice as practice_module


def _set_review_mode(client, enabled: bool):
    res = client.post("/api/settings", json={"review_mode": enabled})
    assert res.status_code == 200
    assert res.json()["review_mode"] is enabled


def test_review_mode_toggle_persists(client):
    _set_review_mode(client, True)
    assert client.get("/api/settings").json()["review_mode"] is True
    _set_review_mode(client, False)
    assert client.get("/api/settings").json()["review_mode"] is False


def test_review_mode_hides_previous_notes(client, monkeypatch):
    monkeypatch.setattr(
        practice_module, "explain_mistake", lambda user_id, exam, node, expected, submitted: "第一次的錯誤說明。"
    )
    source_id = "toeic-r5-009"  # correct answer is "B" (honest)
    _set_review_mode(client, False)
    client.post("/api/practice/submit", json={"answers": [{"source_id": source_id, "answer": "A"}]})

    # not in review mode: the note is visible
    res = client.get("/api/review", params={"limit": 100})
    matches = [q for q in res.json() if source_id in (q.get("reviewNotes") or {})]
    assert matches and matches[0]["reviewNotes"][source_id] == "第一次的錯誤說明。"

    # switch to review mode: the same wrong question no longer exposes the note
    _set_review_mode(client, True)
    res2 = client.get("/api/review", params={"limit": 100})
    hidden = [q for q in res2.json() if q["source_id"] == matches[0]["source_id"]]
    assert hidden and not (hidden[0].get("reviewNotes") or {})

    _set_review_mode(client, False)


def test_review_mode_regenerates_comment_using_previous_note(client, monkeypatch):
    monkeypatch.setattr(
        practice_module, "explain_mistake", lambda user_id, exam, node, expected, submitted: "第一次錯誤: 誤用副詞。"
    )
    source_id = "toeic-r5-010"  # correct answer is "B" (was expected)
    _set_review_mode(client, False)
    client.post("/api/practice/submit", json={"answers": [{"source_id": source_id, "answer": "A"}]})

    seen_previous_notes = []

    def fake_review_progress_comment(user_id, exam, node, expected, submitted, is_correct, previous_note):
        seen_previous_notes.append(previous_note)
        return "太棒了,這次你答對了,已經修正先前的誤解。" if is_correct else "你又犯了類似的錯誤,再注意一下。"

    monkeypatch.setattr(practice_module, "review_progress_comment", fake_review_progress_comment)

    _set_review_mode(client, True)
    res = client.post("/api/practice/submit", json={"answers": [{"source_id": source_id, "answer": "B"}]})
    body = res.json()
    assert body["results"][0]["note"] == "太棒了,這次你答對了,已經修正先前的誤解。"
    assert seen_previous_notes == ["第一次錯誤: 誤用副詞。"]

    _set_review_mode(client, False)


def test_review_mode_correct_reattempt_removed_from_notebook(client, monkeypatch):
    monkeypatch.setattr(
        practice_module, "explain_mistake", lambda user_id, exam, node, expected, submitted: "第一次的錯誤說明。"
    )
    monkeypatch.setattr(
        practice_module,
        "review_progress_comment",
        lambda user_id, exam, node, expected, submitted, is_correct, previous_note: "答對了,恭喜修正先前的錯誤。",
    )
    source_id = "toeic-r5-014"  # correct answer is "B" (dissatisfied)
    _set_review_mode(client, False)
    client.post("/api/practice/submit", json={"answers": [{"source_id": source_id, "answer": "A"}]})

    res = client.get("/api/review", params={"limit": 100})
    assert source_id in {q["source_id"] for q in res.json()}

    _set_review_mode(client, True)
    client.post("/api/practice/submit", json={"answers": [{"source_id": source_id, "answer": "B"}]})

    res2 = client.get("/api/review", params={"limit": 100})
    assert source_id not in {q["source_id"] for q in res2.json()}

    _set_review_mode(client, False)


def test_non_review_mode_does_not_call_review_progress_comment(client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        practice_module,
        "review_progress_comment",
        lambda *a, **k: calls.append(1) or "should not be used",
    )
    _set_review_mode(client, False)
    client.post(
        "/api/practice/submit",
        json={"answers": [{"source_id": "toeic-r5-011", "answer": "A"}]},
    )
    assert calls == []
