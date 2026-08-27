import uuid

from fastapi.testclient import TestClient

import app.routers.translate as translate_module
from app.database import SessionLocal
from app.main import app
from app.models import Attempt, User
from app.routers.auth import _claim_orphaned_data


def _fresh_client() -> TestClient:
    return TestClient(app)


def test_register_sets_cookie_and_me_works():
    c = _fresh_client()
    username = f"reg-{uuid.uuid4().hex[:8]}"
    res = c.post("/api/auth/register", json={"username": username, "password": "correcthorse123"})
    assert res.status_code == 200
    assert "session_token" in res.cookies

    me = c.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["username"] == username


def test_duplicate_username_rejected():
    c = _fresh_client()
    username = f"dupe-{uuid.uuid4().hex[:8]}"
    assert c.post("/api/auth/register", json={"username": username, "password": "correcthorse123"}).status_code == 200
    res = c.post("/api/auth/register", json={"username": username, "password": "anotherpassword"})
    assert res.status_code == 409


def test_wrong_password_rejected():
    c = _fresh_client()
    username = f"wrongpw-{uuid.uuid4().hex[:8]}"
    c.post("/api/auth/register", json={"username": username, "password": "correcthorse123"})
    c.cookies.clear()

    res = c.post("/api/auth/login", json={"username": username, "password": "not-the-right-password"})
    assert res.status_code == 401


def test_logout_clears_session():
    c = _fresh_client()
    username = f"logout-{uuid.uuid4().hex[:8]}"
    c.post("/api/auth/register", json={"username": username, "password": "correcthorse123"})

    assert c.post("/api/auth/logout").status_code == 204
    assert c.get("/api/auth/me").status_code == 401


def test_unauthenticated_api_request_gets_401():
    c = _fresh_client()
    res = c.get("/api/history")
    assert res.status_code == 401


def test_unauthenticated_page_request_redirects_to_login():
    c = _fresh_client()
    res = c.get("/history", follow_redirects=False)
    assert res.status_code in (302, 303, 307)
    assert res.headers["location"].startswith("/login")


def test_vocab_book_is_isolated_between_users(client, other_client, monkeypatch):
    monkeypatch.setattr(translate_module, "translate_text", lambda user_id, text: f"[譯] {text}")
    suffix = "".join(c for c in uuid.uuid4().hex if c.isalpha())[:6] or "abcdef"
    word = f"isolationword{suffix}"
    client.post("/api/translate/text", json={"text": word})
    other_client.post("/api/translate/text", json={"text": word})

    mine = [e["word"] for e in client.get("/api/vocab").json()]
    theirs = [e["word"] for e in other_client.get("/api/vocab").json()]
    assert word.lower() in mine
    assert word.lower() in theirs

    # deleting my entry should not touch the other user's
    mine_id = next(e["id"] for e in client.get("/api/vocab").json() if e["word"] == word.lower())
    theirs_id = next(e["id"] for e in other_client.get("/api/vocab").json() if e["word"] == word.lower())
    assert mine_id != theirs_id


def test_attempt_history_is_isolated_between_users(client, other_client):
    source_id = "toeic-r5-009"  # correct answer is "D" (necessary)

    client.post("/api/practice/submit", json={"answers": [{"source_id": source_id, "answer": "A"}]})
    my_total = client.get("/api/history").json()["total_attempts"]
    their_total_before = other_client.get("/api/history").json()["total_attempts"]

    assert my_total >= 1
    assert their_total_before == 0

    other_client.post("/api/practice/submit", json={"answers": [{"source_id": source_id, "answer": "D"}]})
    their_total_after = other_client.get("/api/history").json()["total_attempts"]
    assert their_total_after == 1


def test_mock_exam_session_not_visible_to_other_user(client, other_client):
    res = client.post("/api/mock-exam/start", json={"exam": "TOEIC", "mode": "bank"})
    assert res.status_code == 200
    session_id = res.json()["id"]

    mine = client.get(f"/api/mock-exam/{session_id}")
    assert mine.status_code == 200

    theirs = other_client.get(f"/api/mock-exam/{session_id}")
    assert theirs.status_code == 404


def test_bootstrap_claim_assigns_orphaned_rows_to_the_claiming_user():
    db = SessionLocal()
    try:
        orphan = Attempt(
            user_id=None,
            exam="TOEIC",
            section="Reading",
            source_id="bootstrap-claim-test",
            item_type="objective",
            is_correct=True,
        )
        db.add(orphan)
        db.commit()
        db.refresh(orphan)

        claimant = User(username=f"claimant-{uuid.uuid4().hex[:8]}", password_hash="irrelevant")
        db.add(claimant)
        db.commit()
        db.refresh(claimant)

        _claim_orphaned_data(db, claimant)

        db.refresh(orphan)
        assert orphan.user_id == claimant.id
    finally:
        db.close()
