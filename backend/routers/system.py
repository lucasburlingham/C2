from fastapi import APIRouter
from ..services import gps_service, mesh_service

router = APIRouter(prefix="/system", tags=["System"])


@router.get("/status")
async def system_status():
    gps = gps_service.get_gps_status()
    mesh = mesh_service.mesh_status()
    return {"gps": gps, "mesh": mesh}
