"""Password hashing and session management for username/password login.

Uses stdlib `hashlib.pbkdf2_hmac` (no new dependency) rather than a
third-party password library, matching how `app/services/crypto.py`
already keeps this project's dependency footprint minimal.
"""

import datetime
import hashlib
import hmac
import re
import secrets

from sqlalchemy.orm import Session

from app.models import AppSetting, Attempt, ExamSession, Question, User, UserSession, VocabEntry

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


def claim_orphaned_data(db: Session, user: User) -> None:
    """One-time bootstrap: the very first account ever registered inherits
    all pre-existing data that predates multi-user support (user_id IS
    NULL), except the shared seed question bank, which stays shared.
    """
    db.query(Attempt).filter(Attempt.user_id.is_(None)).update({"user_id": user.id})
    db.query(ExamSession).filter(ExamSession.user_id.is_(None)).update({"user_id": user.id})
    db.query(VocabEntry).filter(VocabEntry.user_id.is_(None)).update({"user_id": user.id})
    db.query(AppSetting).filter(AppSetting.user_id.is_(None)).update({"user_id": user.id})
    db.query(Question).filter(
        Question.user_id.is_(None), Question.source_file.in_(["ai-generated", "user-upload"])
    ).update({"user_id": user.id}, synchronize_session=False)
    db.commit()


def _unique_username_from_email(db: Session, email: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9_.-]", "", email.split("@")[0]) or "user"
    username = base
    suffix = 1
    while db.query(User).filter(User.username == username).one_or_none() is not None:
        suffix += 1
        username = f"{base}{suffix}"
    return username


def get_or_create_google_user(db: Session, *, email: str, google_sub: str) -> User:
    """Resolves a Google login to a User: an existing account already linked
    to this Google account, an existing username/password account with the
    same email (auto-linked here), or a freshly created Google-only account.
    """
    user = db.query(User).filter(User.google_sub == google_sub).one_or_none()
    if user is not None:
        return user

    user = db.query(User).filter(User.email == email).one_or_none()
    if user is not None:
        user.google_sub = google_sub
        db.commit()
        db.refresh(user)
        return user

    is_first_user = db.query(User).count() == 0
    user = User(
        username=_unique_username_from_email(db, email),
        password_hash=hash_password(secrets.token_urlsafe(32)),
        email=email,
        google_sub=google_sub,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    if is_first_user:
        claim_orphaned_data(db, user)
    return user
