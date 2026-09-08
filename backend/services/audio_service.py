import asyncio
from typing import Dict, Set

# _streams maps stream_id -> set of websockets
_streams: Dict[str, Set[asyncio.AbstractEventLoop]] = {}
# _locks maps stream_id -> asyncio.Lock
_locks: Dict[str, asyncio.Lock] = {}
# _meta maps websocket -> {'stream_id': ..., 'username': ...}
_meta: Dict[object, Dict] = {}
_active_timers: Dict[str, asyncio.Handle] = {}
_active_username: Dict[str, str] = {}


def _get_lock(stream_id: str) -> asyncio.Lock:
    if stream_id not in _locks:
        _locks[stream_id] = asyncio.Lock()
    return _locks[stream_id]


async def register(stream_id: str, websocket, username: str = None) -> None:
    async with _get_lock(stream_id):
        conns = _streams.get(stream_id)
        if conns is None:
            conns = set()
            _streams[stream_id] = conns
        conns.add(websocket)
        _meta[websocket] = {'stream_id': stream_id, 'username': username}


async def unregister(stream_id: str, websocket) -> None:
    async with _get_lock(stream_id):
        conns = _streams.get(stream_id)
        if not conns:
            return
        conns.discard(websocket)
        _meta.pop(websocket, None)
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
        # still forward to any TCP relay listeners
        try:
            from . import ws_audio_relay
            try:
                ws_audio_relay.send_bytes(stream_id, data)
            except Exception:
                pass
        except Exception:
            pass
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

    # determine sender username and update label for overlay (activity timer)
    try:
        meta = _meta.get(sender)
        if meta and meta.get('username'):
            # schedule/set active username with timeout
            await _set_active_username(stream_id, meta.get('username'))
    except Exception:
        pass

    # also forward to any TCP relay listeners
    try:
        from . import ws_audio_relay
        try:
            ws_audio_relay.send_bytes(stream_id, data)
        except Exception:
            pass
    except Exception:
        pass
    return len(coros)


async def _set_active_username(stream_id: str, username: str, timeout: int = 10):
    """Set active username label for stream and schedule a timeout to clear it after `timeout` seconds of inactivity."""
    try:
        from . import sdr_service
        sdr_service.set_user(stream_id, username)
        _active_username[stream_id] = username
        # cancel existing timer
        handle = _active_timers.get(stream_id)
        if handle:
            try:
                handle.cancel()
            except Exception:
                pass
        loop = asyncio.get_event_loop()

        def _clear():
            try:
                cur = _active_username.get(stream_id)
                if cur == username:
                    try:
                        from . import sdr_service as _sdr
                        _sdr.set_user(stream_id, None)
                    except Exception:
                        pass
                    _active_username.pop(stream_id, None)
            except Exception:
                pass

        _active_timers[stream_id] = loop.call_later(timeout, _clear)
    except Exception:
        pass


async def ptt_event(stream_id: str, websocket, state: bool):
    """Handle PTT events from a websocket client. If state is True, set active username immediately; if False, schedule timeout."""
    try:
        meta = _meta.get(websocket)
        if not meta:
            return {'ok': False, 'error': 'unknown client'}
        username = meta.get('username')
        if not username:
            return {'ok': False, 'error': 'no username set'}
        if state:
            await _set_active_username(stream_id, username)
            return {'ok': True}
        else:
            # schedule clear after timeout (reset timer)
            await _set_active_username(stream_id, username)
            return {'ok': True}
    except Exception as e:
        return {'ok': False, 'error': str(e)}
