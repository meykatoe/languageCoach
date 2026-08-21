import os

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AppSetting
from app.schemas import SettingsOut, SettingsUpdateRequest
from app.services.openai_service import DEFAULT_MODEL

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _build_settings_out(db: Session) -> SettingsOut:
    setting = db.query(AppSetting).first()
    db_key = setting.openai_api_key if setting else None
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
    )


@router.get("", response_model=SettingsOut)
def get_settings(db: Session = Depends(get_db)):
    return _build_settings_out(db)


@router.post("", response_model=SettingsOut)
def update_settings(payload: SettingsUpdateRequest, db: Session = Depends(get_db)):
    setting = db.query(AppSetting).first()
    if setting is None:
        setting = AppSetting()
        db.add(setting)

    if payload.clear_api_key:
        setting.openai_api_key = None
    elif payload.openai_api_key:
        setting.openai_api_key = payload.openai_api_key.strip()

    if payload.openai_model is not None:
        setting.openai_model = payload.openai_model.strip() or None

    db.commit()
    return _build_settings_out(db)
