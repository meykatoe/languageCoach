import os
import tempfile
from pathlib import Path

import pytest

_tmp_dir = tempfile.TemporaryDirectory()
os.environ["LANGCOACH_DB_PATH"] = str(Path(_tmp_dir.name) / "test.db")

from app.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="session")
def client():
    """A TestClient logged in as a throwaway user (this project is now
    multi-user, so every route except /login and /register requires a
    session cookie). Session-scoped and registered once so the same user's
    data accumulates across a test file the way the old single-user client
    did.
    """
    with TestClient(app) as c:
        res = c.post("/api/auth/register", json={"username": "testuser", "password": "testpassword123"})
        assert res.status_code == 200, res.text
        yield c


@pytest.fixture
def other_client():
    """A second, independently logged-in user, for tests that verify data
    isolation between accounts. Function-scoped (fresh user per test) since
    isolation tests care about a clean slate, not shared history.
    """
    with TestClient(app) as c:
        import uuid

        username = f"other-{uuid.uuid4().hex[:8]}"
        res = c.post("/api/auth/register", json={"username": username, "password": "testpassword123"})
        assert res.status_code == 200, res.text
        yield c
