from fastapi import APIRouter
from ..services import sdr_service

router = APIRouter(prefix="/sdr", tags=["SDR"])


@router.post("/start")
async def start_stream(stream_id: str = "sdr1"):
    return sdr_service.start_stream(stream_id)


@router.post("/stop")
async def stop_stream(stream_id: str = "sdr1"):
    return sdr_service.stop_stream(stream_id)


@router.get("/status")
async def sdr_status(stream_id: str = None):
    return sdr_service.get_status(stream_id)


@router.post("/{stream_id}/frequency")
async def set_frequency(stream_id: str, hz: float):
    """Set the tuned frequency (Hz) for the given SDR stream. Writes a small text file used by ffmpeg/gst drawtext."""
    return sdr_service.set_frequency(stream_id, hz)


@router.get("/{stream_id}/frequency")
async def get_frequency(stream_id: str):
    return {"frequency": sdr_service.get_frequency(stream_id)}
