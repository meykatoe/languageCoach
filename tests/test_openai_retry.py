import httpx
import pytest
from openai import APIConnectionError, AuthenticationError, RateLimitError

from app.services.openai_retry import MAX_ATTEMPTS, call_with_retry


def _rate_limit_error():
    req = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    resp = httpx.Response(429, request=req)
    return RateLimitError("rate limited", response=resp, body=None)


def _auth_error():
    req = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    resp = httpx.Response(401, request=req)
    return AuthenticationError("bad key", response=resp, body=None)


def _connection_error():
    req = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    return APIConnectionError(request=req)


def test_succeeds_without_retry_when_call_works():
    calls = []

    def fn():
        calls.append(1)
        return "ok"

    assert call_with_retry(fn) == "ok"
    assert len(calls) == 1


def test_retries_transient_error_then_succeeds(monkeypatch):
    monkeypatch.setattr("app.services.openai_retry.time.sleep", lambda _: None)
    attempts = []

    def fn():
        attempts.append(1)
        if len(attempts) < 2:
            raise _rate_limit_error()
        return "recovered"

    assert call_with_retry(fn) == "recovered"
    assert len(attempts) == 2


def test_exhausts_retries_and_raises_friendly_runtime_error(monkeypatch):
    monkeypatch.setattr("app.services.openai_retry.time.sleep", lambda _: None)
    attempts = []

    def fn():
        attempts.append(1)
        raise _connection_error()

    with pytest.raises(RuntimeError, match="無法連線"):
        call_with_retry(fn)
    assert len(attempts) == MAX_ATTEMPTS


def test_permanent_error_fails_fast_without_retrying():
    attempts = []

    def fn():
        attempts.append(1)
        raise _auth_error()

    with pytest.raises(RuntimeError, match="API Key 無效"):
        call_with_retry(fn)
    assert len(attempts) == 1
