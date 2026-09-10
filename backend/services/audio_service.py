import asyncio
import os
from typing import Dict, Set

# import shared state dir from sdr_service
from .sdr_service import STATE_DIR

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
            # schedule a clear of the active username after a short grace period
            try:
                # cancel existing timer if present
                handle = _active_timers.get(stream_id)
                if handle:
                    try:
                        handle.cancel()
                    except Exception:
                        pass
                loop = asyncio.get_event_loop()

                def _clear_release():
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

                # short grace before clearing (2s)
                _active_timers[stream_id] = loop.call_later(2, _clear_release)
            except Exception:
                pass
            return {'ok': True}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def list_alsa_devices() -> dict:
    """Return a structured list of ALSA capture/playback devices by parsing `arecord -l` output.
    Returns {'cards': [ { 'card': int, 'name': str, 'devices': [ { 'device': int, 'name': str } ] } ] }
    """
    import subprocess
    import re

    try:
        out = subprocess.check_output(['arecord', '-l'], stderr=subprocess.STDOUT, text=True)
    except Exception:
        # fallback: try to read /proc/asound/cards
        try:
            with open('/proc/asound/cards', 'r', encoding='utf-8') as f:
                data = f.read()
        except Exception:
            return {'cards': []}
        out = data

    cards = []
    # parse lines like: card 3: Loopback [Loopback], device 0: Loopback PCM [Loopback PCM]
    card_re = re.compile(r"card\s+(\d+):\s*([^\[]+?)\s*\[([^\]]+)\]")
    dev_re = re.compile(r"device\s+(\d+):\s*([^\[]+?)\s*\[([^\]]+)\]")

    current = None
    for line in out.splitlines():
        m = card_re.search(line)
        if m:
            card_no = int(m.group(1))
            card_name = m.group(2).strip()
            current = {'card': card_no, 'name': card_name, 'devices': []}
            cards.append(current)
            continue
        m2 = dev_re.search(line)
        if m2 and current is not None:
            dev_no = int(m2.group(1))
            dev_name = m2.group(2).strip()
            current['devices'].append({'device': dev_no, 'name': dev_name})

    return {'cards': cards}


def find_alsa_for_usb(bus: int, dev: int) -> str:
    """Return ALSA hw string for given USB bus and device (e.g. 'hw:Card3,0'), or empty string if not found."""
    import os

    # normalize
    bus = int(bus)
    dev = int(dev)
    # look through sound cards
    cards_dir = '/sys/class/sound'
    if not os.path.exists(cards_dir):
        return ''
    for name in os.listdir(cards_dir):
        if not name.startswith('card'):
            continue
        card_no = int(name.replace('card', ''))
        devpath = os.path.realpath(os.path.join(cards_dir, name, 'device'))
        # walk ancestors looking for usb node like '3-5'
        parts = devpath.split(os.sep)
        for i in range(len(parts)):
            part = parts[i]
            if '-' in part:
                try:
                    pbus, pdev = part.split('-', 1)
                    if int(pbus) == bus and int(pdev) == dev:
                        # found matching usb device
                        return f'hw:Card{card_no},0'
                except Exception:
                    pass
    return ''


def write_server_audio_device(hw: str) -> None:
    path = os.path.join(STATE_DIR, 'server_audio_device.txt')
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(hw)
    except Exception:
        pass


def read_server_audio_device() -> str:
    path = os.path.join(STATE_DIR, 'server_audio_device.txt')
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return f.read().strip()
    except Exception:
        pass
    return ''
