from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..services import audio_service

router = APIRouter()


@router.websocket('/ws/telemetry')
async def telemetry_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            # echo for scaffold
            await websocket.send_text(f"echo: {data}")
    except WebSocketDisconnect:
        return


@router.websocket('/ws/audio/{stream_id}')
async def audio_ws(websocket: WebSocket, stream_id: str):
    """Simple audio websocket bridge: clients send binary frames which are broadcast to other clients."""
    await websocket.accept()
    await audio_service.register(stream_id, websocket)
    try:
        while True:
            msg = await websocket.receive()
            # support bytes and text base64 if needed
            if 'bytes' in msg:
                data = msg['bytes']
                await audio_service.broadcast(stream_id, data, sender=websocket)
            elif 'text' in msg:
                # ignore text messages for now
                pass
    except WebSocketDisconnect:
        await audio_service.unregister(stream_id, websocket)
        return
