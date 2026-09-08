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


@router.post("/{stream_id}/overlay/start")
async def start_overlay(stream_id: str, engine: str = 'ffmpeg', audio_device: str = 'default', out_url: str = 'udp://127.0.0.1:5004'):
    from ..services import overlay_manager
    # ensure the stream is started
    sdr_service.start_stream(stream_id)
    return overlay_manager.start_overlay(stream_id, engine=engine, audio_device=audio_device, out_url=out_url)


@router.post("/{stream_id}/overlay/stop")
async def stop_overlay(stream_id: str):
    from ..services import overlay_manager
    return overlay_manager.stop_overlay(stream_id)


@router.get("/{stream_id}/overlay/status")
async def overlay_status(stream_id: str):
    from ..services import overlay_manager
    return overlay_manager.status_overlay(stream_id)


@router.get("/overlay/list")
async def overlay_list():
    from ..services import overlay_manager
    return overlay_manager.list_overlays()


@router.get("/{stream_id}/overlay/logs")
async def overlay_logs(stream_id: str, lines: int = 200):
    from ..services import overlay_manager
    return overlay_manager.get_logs(stream_id, lines=lines)


@router.post("/{stream_id}/user")
async def set_user(stream_id: str, name: str = None):
    return sdr_service.set_user(stream_id, name)


@router.get("/{stream_id}/user")
async def get_user(stream_id: str):
    return {"username": sdr_service.get_user(stream_id)}
