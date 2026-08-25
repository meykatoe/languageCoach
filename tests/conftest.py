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
    with TestClient(app) as c:
        yield c
