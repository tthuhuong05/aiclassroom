from fastapi import APIRouter
from pydantic import BaseModel
from services.exam_proctor_service import ProctorEngine
import base64, requests

router = APIRouter()
engines = {}  # attempt_id -> ProctorEngine

class FrameIn(BaseModel):
    attempt_id: str
    frame_b64: str

class InitIn(BaseModel):
    attempt_id: str
    avatar_url: str | None = None
    avatar_b64: str | None = None

@router.post("/proctor/init")
def proctor_init(body: InitIn):
    try:
        avatar_bytes = None
        if body.avatar_b64:
            data = body.avatar_b64
            if data.startswith('data:image'):
                data = data.split(',',1)[1]
            missing = (-len(data)) % 4
            if missing: data += '=' * missing
            try:
                avatar_bytes = base64.b64decode(data, validate=False)
            except Exception:
                avatar_bytes = base64.urlsafe_b64decode(data)
        elif body.avatar_url:
            r = requests.get(body.avatar_url, timeout=10)
            r.raise_for_status()
            avatar_bytes = r.content
        else:
            return {"ok": False, "error": "avatar_required"}

        engines[body.attempt_id] = ProctorEngine(attempt_id=body.attempt_id, avatar_bytes=avatar_bytes)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": f"init_failed: {e}"}

@router.post("/proctor/frame")
def proctor_frame(body: FrameIn):
    eng = engines.get(body.attempt_id)
    if not eng:
        return {"ok": False, "error": "not_initialized"}
    return eng.process_base64_frame(body.frame_b64, save=False)

@router.get("/proctor/status/{attempt_id}")
def proctor_status(attempt_id: str):
    eng = engines.get(attempt_id)
    if not eng:
        return {"ok": False, "error": "not_initialized"}
    return {"ok": True, "state": eng.state}

@router.delete("/proctor/reset/{attempt_id}")
def proctor_reset(attempt_id: str):
    if attempt_id in engines:
        del engines[attempt_id]
    return {"ok": True}
