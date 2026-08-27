import hashlib
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from openai import APIError

from app.database import DATA_DIR
from app.dependencies import get_current_user
from app.models import User
from app.schemas import TtsRequest
from app.services.openai_service import DEFAULT_TTS_MODEL, DEFAULT_TTS_VOICE, synthesize_speech

router = APIRouter(prefix="/api/tts", tags=["tts"])

CACHE_DIR = DATA_DIR / "tts_cache"


def _cache_path(text: str) -> Path:
    # Keyed on the text + model/voice so a future model/voice change doesn't
    # serve stale audio; identical transcripts across different questions
    # naturally share one cached file.
    key = hashlib.sha256(f"{DEFAULT_TTS_MODEL}|{DEFAULT_TTS_VOICE}|{text}".encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{key}.mp3"


@router.post("")
def get_speech(payload: TtsRequest, current_user: User = Depends(get_current_user)):
    path = _cache_path(payload.text)
    if not path.exists():
        try:
            audio = synthesize_speech(current_user.id, payload.text)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except APIError as exc:
            raise HTTPException(
                status_code=502, detail=f"OpenAI API 呼叫失敗,請確認 ⚙️ 設定頁的 API Key 是否正確: {exc}"
            ) from exc
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_bytes(audio)

    return FileResponse(path, media_type="audio/mpeg")
