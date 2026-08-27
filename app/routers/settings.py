import os

from fastapi import APIRouter, Depends
from openai import APIError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import AppSetting, User
from app.schemas import (
    SettingsOut,
    SettingsUpdateRequest,
    TestConnectionRequest,
    TestConnectionResponse,
)
from app.services.crypto import decrypt, encrypt
from app.services.openai_service import DEFAULT_MODEL, test_connection

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _build_settings_out(db: Session, user_id: int) -> SettingsOut:
    setting = db.query(AppSetting).filter(AppSetting.user_id == user_id).first()
    db_key = decrypt(setting.openai_api_key) if setting and setting.openai_api_key else None
    env_key = os.environ.get("OPENAI_API_KEY")

    if db_key:
        source, active_key = "database", db_key
    elif env_key:
        source, active_key = "environment", env_key
    else:
        source, active_key = "none", None

    hint = f"...{active_key[-4:]}" if active_key and len(active_key) > 4 else None
    model = (
        (setting.openai_model if setting and setting.openai_model else None)
        or os.environ.get("OPENAI_MODEL")
        or DEFAULT_MODEL
    )

    return SettingsOut(
        has_api_key=bool(active_key),
        api_key_hint=hint,
        api_key_source=source,
        openai_model=model,
        review_mode=bool(setting and setting.review_mode),
    )


@router.get("", response_model=SettingsOut)
def get_settings(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return _build_settings_out(db, current_user.id)


@router.post("", response_model=SettingsOut)
def update_settings(
    payload: SettingsUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    setting = db.query(AppSetting).filter(AppSetting.user_id == current_user.id).first()
    if setting is None:
        setting = AppSetting(user_id=current_user.id)
        db.add(setting)

    if payload.clear_api_key:
        setting.openai_api_key = None
    elif payload.openai_api_key:
        setting.openai_api_key = encrypt(payload.openai_api_key.strip())

    if payload.openai_model is not None:
        setting.openai_model = payload.openai_model.strip() or None

    if payload.review_mode is not None:
        setting.review_mode = payload.review_mode

    db.commit()
    return _build_settings_out(db, current_user.id)


@router.post("/test", response_model=TestConnectionResponse)
def test_settings_connection(
    payload: TestConnectionRequest, current_user: User = Depends(get_current_user)
):
    key = payload.openai_api_key.strip() if payload.openai_api_key else None
    try:
        model_id = test_connection(current_user.id, api_key=key)
        return TestConnectionResponse(ok=True, message=f"連線成功,可正常呼叫模型(範例: {model_id})。")
    except RuntimeError as exc:
        return TestConnectionResponse(ok=False, message=str(exc))
    except APIError as exc:
        return TestConnectionResponse(ok=False, message=f"連線失敗: {exc}")
