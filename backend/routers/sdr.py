from fastapi import APIRouter
from ..services import sdr_service

router = APIRouter(prefix="/sdr", tags=["SDR"])


@router.post("/start")
async def start_stream(stream_id: str = "default"):
    return sdr_service.start_stream(stream_id)


@router.post("/stop")
async def stop_stream(stream_id: str = "default"):
    return sdr_service.stop_stream(stream_id)


@router.get("/status")
async def sdr_status(stream_id: str = None):
    return sdr_service.get_status(stream_id)
