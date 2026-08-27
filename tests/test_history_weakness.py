def test_weakness_appears_after_wrong_answer(client):
    source_id = "toeic-r5-007"  # correct answer is "B" (analysis)
    client.post(
        "/api/practice/submit",
        json={"answers": [{"source_id": source_id, "answer": "A"}]},
    )

    res = client.get("/api/history")
    assert res.status_code == 200
    weaknesses = res.json()["weaknesses"]

    match = next(
        (
            w
            for w in weaknesses
            if w["exam"] == "TOEIC"
            and w["section"] == "Reading"
            and w["part"] == "Part 5: Incomplete Sentences"
        ),
        None,
    )
    assert match is not None
    assert match["wrong_count"] >= 1

    # weaknesses is sorted worst-first
    counts = [w["wrong_count"] for w in weaknesses]
    assert counts == sorted(counts, reverse=True)


def test_daily_accuracy_reflects_objective_attempts_only(client):
    source_id = "toeic-r5-007"  # correct answer is "B" (analysis)
    client.post(
        "/api/practice/submit",
        json={"answers": [{"source_id": source_id, "answer": "B"}]},
    )

    res = client.get("/api/history")
    assert res.status_code == 200
    daily = res.json()["daily_accuracy"]

    assert daily, "expected at least one day of objective attempts"
    today = daily[-1]
    assert today["total"] >= 1
    assert today["correct"] >= 1
    assert 0.0 <= today["accuracy"] <= 1.0


def test_daily_activity_counts_all_item_types(client):
    source_id = "toeic-r5-007"
    client.post(
        "/api/practice/submit",
        json={"answers": [{"source_id": source_id, "answer": "B"}]},
    )

    res = client.get("/api/history")
    assert res.status_code == 200
    activity = res.json()["daily_activity"]

    assert activity, "expected at least one day of activity"
    today = activity[-1]
    assert today["count"] >= 1


def test_weakness_entry_disappears_once_the_only_wrong_item_is_fixed(client):
    source_id = "toeic-r5-008"  # correct answer is "A" (proceeded)
    client.post(
        "/api/practice/submit",
        json={"answers": [{"source_id": source_id, "answer": "B"}]},
    )
    before = client.get("/api/history").json()["weaknesses"]
    before_count = next(
        w["wrong_count"] for w in before if w["part"] == "Part 5: Incomplete Sentences"
    )

    client.post(
        "/api/practice/submit",
        json={"answers": [{"source_id": source_id, "answer": "A"}]},
    )
    after = client.get("/api/history").json()["weaknesses"]
    after_match = next(
        (w for w in after if w["part"] == "Part 5: Incomplete Sentences"), None
    )
    after_count = after_match["wrong_count"] if after_match else 0
    assert after_count == before_count - 1
