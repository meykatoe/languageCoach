"""Encrypts secrets (currently just the user's OpenAI API key) before they
are stored in SQLite, so a copied/leaked `app.db` file doesn't hand over a
usable key in plain text.

The Fernet key itself is either supplied via the `APP_SECRET_KEY` env var
(recommended for a shared/deployed instance) or auto-generated on first run
and persisted to `data/secret.key` (fine for the single-user local case this
app is normally run in). Either way the key file must never be committed.
"""

import os

from cryptography.fernet import Fernet, InvalidToken

from app.database import DATA_DIR

_KEY_PATH = DATA_DIR / "secret.key"


def _load_key() -> bytes:
    env_key = os.environ.get("APP_SECRET_KEY")
    if env_key:
        return env_key.encode()

    if _KEY_PATH.exists():
        return _KEY_PATH.read_bytes().strip()

    key = Fernet.generate_key()
    _KEY_PATH.write_bytes(key)
    _KEY_PATH.chmod(0o600)
    return key


_fernet = Fernet(_load_key())


def get_session_secret() -> str:
    """Signing secret for the OAuth login flow's transient server-side
    session (holds the CSRF `state`/`nonce` between the Google redirect and
    callback). Reuses the same key material as the API-key encryption above
    -- both already fall back to an auto-generated, persisted secret, and
    keeping a second secret in sync isn't worth it for this app's scale.
    """
    return _load_key().decode()


def encrypt(value: str) -> str:
    return _fernet.encrypt(value.encode()).decode()


def decrypt(value: str) -> str | None:
    """Returns the decrypted plaintext, or None if `value` isn't a token
    this key can decrypt (wrong/rotated key, corrupted data, ...) so callers
    can fail closed instead of treating garbage as a usable API key.
    """
    try:
        return _fernet.decrypt(value.encode()).decode()
    except (InvalidToken, ValueError):
        return None


def migrate_legacy_plaintext_key(db) -> None:
    """One-time upgrade for rows written before encryption was added: if a
    stored `openai_api_key` isn't a valid Fernet token, it's a legacy
    plaintext key, so encrypt it in place. Checks every AppSetting row
    (one per user since multi-user support was added).
    """
    from app.models import AppSetting

    changed = False
    for setting in db.query(AppSetting).all():
        if setting.openai_api_key and decrypt(setting.openai_api_key) is None:
            setting.openai_api_key = encrypt(setting.openai_api_key)
            changed = True
    if changed:
        db.commit()
