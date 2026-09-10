from fastapi import APIRouter
from ..services import gps_service, mesh_service
from ..services import audio_service
from ..services import presets_service

router = APIRouter(prefix="/system", tags=["System"])


@router.get("/status")
async def system_status():
    gps = gps_service.get_gps_status()
    mesh = mesh_service.mesh_status()
    return {"gps": gps, "mesh": mesh}


@router.get("/audio-devices")
async def audio_devices():
    return audio_service.list_alsa_devices()


@router.post("/select-usb-mic")
async def select_usb_mic(bus: int, dev: int):
    hw = audio_service.find_alsa_for_usb(bus, dev)
    if not hw:
        return {"ok": False, "error": "not found"}
    audio_service.write_server_audio_device(hw)
    return {"ok": True, "device": hw}


@router.get("/server-audio-device")
async def server_audio_device():
    hw = audio_service.read_server_audio_device()
    return {"device": hw}


@router.get('/presets')
async def get_presets():
    return presets_service.read_presets()


@router.post('/presets')
async def post_presets(data: dict):
    ok = presets_service.write_presets(data)
    return {'ok': ok}
