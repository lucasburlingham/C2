from fastapi import APIRouter
from ..services import rig_service

router = APIRouter(prefix="/radio", tags=["Radio G90"])


@router.post("/ptt")
async def set_ptt(keying: bool = True):
    result = rig_service.set_ptt_state(keying)
    if result.get("ok"):
        return {"status": "success", "ptt": keying, "response": result.get("response")}
    return {"status": "error", "message": result.get("response")}


@router.get("/status")
async def status():
    raw = rig_service.get_raw_status()
    return {"status": "ok", "raw": raw}
