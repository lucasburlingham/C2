import asyncio
from typing import Dict, Set

_streams: Dict[str, Set[asyncio.AbstractEventLoop]] = {}
_locks: Dict[str, asyncio.Lock] = {}


def _get_lock(stream_id: str) -> asyncio.Lock:
    if stream_id not in _locks:
        _locks[stream_id] = asyncio.Lock()
    return _locks[stream_id]


async def register(stream_id: str, websocket) -> None:
    async with _get_lock(stream_id):
        conns = _streams.get(stream_id)
        if conns is None:
            conns = set()
            _streams[stream_id] = conns
        conns.add(websocket)


async def unregister(stream_id: str, websocket) -> None:
    async with _get_lock(stream_id):
        conns = _streams.get(stream_id)
        if not conns:
            return
        conns.discard(websocket)
        if not conns:
            # cleanup
            _streams.pop(stream_id, None)
            _locks.pop(stream_id, None)


async def broadcast(stream_id: str, data: bytes, sender=None) -> int:
    """Broadcast binary `data` to all websocket clients on `stream_id` except `sender`.
    Returns number of recipients attempted.
    """
    conns = _streams.get(stream_id)
    if not conns:
        return 0
    coros = []
    for ws in list(conns):
        if ws is sender:
            continue
        try:
            coros.append(ws.send_bytes(data))
        except Exception:
            # ignore send scheduling errors; cleanup in disconnect
            pass
    if not coros:
        return 0
    await asyncio.gather(*coros, return_exceptions=True)
    return len(coros)
