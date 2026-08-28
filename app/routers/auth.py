from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import SESSION_COOKIE_NAME, get_current_user
from app.models import User
from app.schemas import LoginRequest, RegisterRequest, UserOut
from app.services.auth import (
    claim_orphaned_data,
    create_session,
    delete_session,
    get_or_create_google_user,
    hash_password,
    verify_password,
)
from app.services.oauth import google_login_enabled, oauth

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
        claim_orphaned_data(db, user)

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


@router.get("/google/login")
async def google_login(request: Request):
    if not google_login_enabled():
        raise HTTPException(status_code=503, detail="尚未設定 Google 登入。")
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback", name="google_callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    if not google_login_enabled():
        raise HTTPException(status_code=503, detail="尚未設定 Google 登入。")
    token = await oauth.google.authorize_access_token(request)
    userinfo = token.get("userinfo") or await oauth.google.userinfo(token=token)
    email = userinfo.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Google 帳號未提供 email。")

    user = get_or_create_google_user(db, email=email, google_sub=userinfo["sub"])
    session_token = create_session(db, user)
    response = RedirectResponse(url="/")
    _set_session_cookie(response, session_token, request)
    return response
