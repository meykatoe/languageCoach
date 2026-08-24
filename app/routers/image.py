import hashlib
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from openai import APIError

from app.database import DATA_DIR
from app.schemas import ImageRequest
from app.services.openai_service import DEFAULT_IMAGE_MODEL, DEFAULT_IMAGE_SIZE, generate_image

router = APIRouter(prefix="/api/image", tags=["image"])

CACHE_DIR = DATA_DIR / "image_cache"


def _cache_path(description: str) -> Path:
    # Keyed on the description + model/size so a future model/size change
    # doesn't serve a stale image; identical descriptions naturally share
    # one cached file.
    key = hashlib.sha256(
        f"{DEFAULT_IMAGE_MODEL}|{DEFAULT_IMAGE_SIZE}|{description}".encode("utf-8")
    ).hexdigest()
    return CACHE_DIR / f"{key}.png"


@router.post("")
def get_image(payload: ImageRequest):
    path = _cache_path(payload.description)
    if not path.exists():
        try:
            image = generate_image(payload.description)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except APIError as exc:
            raise HTTPException(
                status_code=502, detail=f"OpenAI API 呼叫失敗,請確認 ⚙️ 設定頁的 API Key 是否正確: {exc}"
            ) from exc
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_bytes(image)

    return FileResponse(path, media_type="image/png")
