from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import SESSION_COOKIE_NAME, get_current_user
from app.models import AppSetting, Attempt, ExamSession, Question, User, VocabEntry
from app.schemas import LoginRequest, RegisterRequest, UserOut
from app.services.auth import create_session, delete_session, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

_COOKIE_MAX_AGE = 30 * 24 * 60 * 60  # 30 days, matches the session's own expiry


def _set_session_cookie(response: Response, token: str, request: Request) -> None:
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        max_age=_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
    )


def _claim_orphaned_data(db: Session, user: User) -> None:
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


@router.post("/register", response_model=UserOut)
def register(payload: RegisterRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    username = payload.username.strip()
    is_first_user = db.query(User).count() == 0

    user = User(username=username, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="此帳號名稱已被使用。") from exc
    db.refresh(user)

    if is_first_user:
        _claim_orphaned_data(db, user)

    token = create_session(db, user)
    _set_session_cookie(response, token, request)
    return UserOut(id=user.id, username=user.username)


@router.post("/login", response_model=UserOut)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username.strip()).one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤。")

    token = create_session(db, user)
    _set_session_cookie(response, token, request)
    return UserOut(id=user.id, username=user.username)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        delete_session(db, token)
    response.delete_cookie(SESSION_COOKIE_NAME)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return UserOut(id=current_user.id, username=current_user.username)
