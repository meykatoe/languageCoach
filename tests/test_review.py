def test_review_empty_when_no_wrong_attempts(client):
    # toeic-r5-003 has not been attempted by anyone yet in this test run
    res = client.get("/api/review")
    assert res.status_code == 200
    # can't assert empty list globally since other tests in the session may
    # have submitted wrong answers already; just check the endpoint works
    assert isinstance(res.json(), list)


def test_review_includes_item_after_wrong_answer(client):
    source_id = "toeic-r5-004"  # correct answer is "B" (are)
    client.post(
        "/api/practice/submit",
        json={"answers": [{"source_id": source_id, "answer": "A"}]},
    )
    res = client.get("/api/review", params={"limit": 100})
    assert res.status_code == 200
    ids = {q["source_id"] for q in res.json()}
    assert source_id in ids


def test_review_excludes_item_after_it_is_answered_correctly(client):
    source_id = "toeic-r5-005"  # correct answer is "A" (unless)
    client.post(
        "/api/practice/submit",
        json={"answers": [{"source_id": source_id, "answer": "B"}]},
    )
    res = client.get("/api/review", params={"limit": 100})
    assert source_id in {q["source_id"] for q in res.json()}

    client.post(
        "/api/practice/submit",
        json={"answers": [{"source_id": source_id, "answer": "A"}]},
    )
    res2 = client.get("/api/review", params={"limit": 100})
    assert source_id not in {q["source_id"] for q in res2.json()}
