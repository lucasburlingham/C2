from fastapi import APIRouter
import socket
import os
from ..services import cot_service

router = APIRouter(prefix="/tak", tags=["TAK"])

TAK_HOST = os.environ.get('TAK_HOST', '127.0.0.1')
TAK_PORT = int(os.environ.get('TAK_PORT', '8087'))


def _send_to_tak(xml: str) -> dict:
    try:
        data = xml.encode('utf-8')
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.sendto(data, (TAK_HOST, TAK_PORT))
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/pli")
async def send_pli(callsign: str = "VEHICLE", lat: float = 0.0, lon: float = 0.0, hae: float = 0.0, speed: float = 0.0, course: float = 0.0):
    xml = cot_service.generate_pli_cot(callsign, lat, lon, hae, speed, course)
    result = _send_to_tak(xml)
    if result.get("ok"):
        return {"status": "sent", "callsign": callsign}
    return {"status": "error", "message": result.get("error")}
