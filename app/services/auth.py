"""Password hashing and session management for username/password login.

Uses stdlib `hashlib.pbkdf2_hmac` (no new dependency) rather than a
third-party password library, matching how `app/services/crypto.py`
already keeps this project's dependency footprint minimal.
"""

import datetime
import hashlib
import hmac
import secrets

from sqlalchemy.orm import Session

from app.models import User, UserSession

_PBKDF2_ITERATIONS = 600_000
_SESSION_LIFETIME = datetime.timedelta(days=30)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), _PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations_str, salt, digest_hex = stored.split("$")
    except ValueError:
        return False
    if algo != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations_str))
    return hmac.compare_digest(digest.hex(), digest_hex)


def create_session(db: Session, user: User) -> str:
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    token = secrets.token_urlsafe(32)
    db.add(UserSession(token=token, user_id=user.id, created_at=now, expires_at=now + _SESSION_LIFETIME))
    db.commit()
    return token


def get_user_from_token(db: Session, token: str) -> User | None:
    session = db.get(UserSession, token)
    if session is None:
        return None
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    if session.expires_at < now:
        return None
    return db.get(User, session.user_id)


def delete_session(db: Session, token: str) -> None:
    session = db.get(UserSession, token)
    if session is not None:
        db.delete(session)
        db.commit()
