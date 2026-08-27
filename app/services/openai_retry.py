"""Retry + friendly-error wrapper around individual OpenAI SDK calls.

The openai SDK already retries a couple of times internally, but on final
failure it surfaces a raw, English, low-level `APIError` straight through to
the user. `call_with_retry` adds a few extra attempts (with backoff) for
transient failures — rate limits, connection drops, timeouts, 5xx — and
translates whatever is left at the end into a short, actionable Traditional
Chinese `RuntimeError`, which every router already knows how to display
(they all catch `RuntimeError` and return its message as-is).

Non-transient failures (bad API key, malformed request, ...) are translated
immediately without retrying, since retrying won't change the outcome.
"""

import logging
import random
import time

from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
BASE_DELAY_SECONDS = 1.0

_TRANSIENT_ERRORS = (RateLimitError, APIConnectionError, APITimeoutError, InternalServerError)

_FRIENDLY_MESSAGES = {
    RateLimitError: "已超過 OpenAI API 的速率限制或帳戶額度上限,請稍後再試,或至 OpenAI 後台確認用量。",
    AuthenticationError: "OpenAI API Key 無效或已過期,請至 ⚙️ 設定頁重新確認並儲存。",
    PermissionDeniedError: "這組 OpenAI API Key 沒有權限呼叫此功能,請確認帳戶權限或改用其他 Key。",
    NotFoundError: "OpenAI 找不到指定的模型,請至 ⚙️ 設定頁確認模型名稱是否正確。",
    APIConnectionError: "無法連線到 OpenAI 服務,請檢查網路連線後再試一次。",
    APITimeoutError: "呼叫 OpenAI 服務逾時,請稍後再試一次。",
    InternalServerError: "OpenAI 服務目前異常,請稍後再試。",
}


def _friendly_message(exc: Exception) -> str:
    for exc_type, message in _FRIENDLY_MESSAGES.items():
        if isinstance(exc, exc_type):
            return message
    return f"呼叫 OpenAI API 時發生錯誤: {exc}"


def call_with_retry(fn, *args, **kwargs):
    """Call an OpenAI SDK method (e.g. `client.chat.completions.create`),
    retrying transient failures a few times with backoff before giving up.
    Always raises `RuntimeError` (never a raw `openai.APIError`) so callers
    only need one except clause.
    """
    last_exc = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return fn(*args, **kwargs)
        except _TRANSIENT_ERRORS as exc:
            last_exc = exc
            if attempt == MAX_ATTEMPTS:
                break
            delay = BASE_DELAY_SECONDS * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
            logger.warning(
                "OpenAI call %s failed on attempt %d/%d (%s), retrying in %.1fs",
                fn.__qualname__, attempt, MAX_ATTEMPTS, exc.__class__.__name__, delay,
            )
            time.sleep(delay)
        except APIError as exc:
            logger.error("OpenAI call %s failed: %s", fn.__qualname__, exc, exc_info=True)
            raise RuntimeError(_friendly_message(exc)) from exc

    logger.error(
        "OpenAI call %s failed after %d attempts: %s", fn.__qualname__, MAX_ATTEMPTS, last_exc, exc_info=last_exc,
    )
    raise RuntimeError(_friendly_message(last_exc)) from last_exc
