import threading
import time
import os
from typing import Dict, Optional

_streams: Dict[str, Dict] = {}
_frequencies: Dict[str, float] = {}

# directory to write small state files used by ffmpeg/gst drawtext textfile
STATE_DIR = os.path.join(os.path.dirname(__file__), '..', 'tmp')
os.makedirs(STATE_DIR, exist_ok=True)


def _write_freq_file(stream_id: str, freq: Optional[float]):
    path = os.path.join(STATE_DIR, f"{stream_id}.freq.txt")
    try:
        if freq is None:
            # remove if no frequency
            if os.path.exists(path):
                os.remove(path)
        else:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(f"{freq:.3f} Hz")
    except Exception:
        pass


def start_stream(stream_id: str) -> dict:
    if stream_id in _streams:
        return {"ok": False, "message": "already running"}

    # Placeholder: start a background thread to simulate streaming
    stop_flag = threading.Event()

    def _runner(flag: threading.Event):
        while not flag.is_set():
            time.sleep(0.5)

    th = threading.Thread(target=_runner, args=(stop_flag,), daemon=True)
    th.start()
    _streams[stream_id] = {"thread": th, "stop": stop_flag, "started_at": time.time()}
    # initialize frequency file if we have a known value
    freq = _frequencies.get(stream_id)
    _write_freq_file(stream_id, freq)
    return {"ok": True, "stream_id": stream_id}


def stop_stream(stream_id: str) -> dict:
    meta = _streams.get(stream_id)
    if not meta:
        return {"ok": False, "message": "not found"}
    meta["stop"].set()
    del _streams[stream_id]
    # remove frequency file
    _write_freq_file(stream_id, None)
    return {"ok": True, "stream_id": stream_id}


def get_status(stream_id: str = None) -> dict:
    if stream_id:
        meta = _streams.get(stream_id)
        if not meta:
            return {"ok": False, "message": "not found"}
        uptime = time.time() - meta["started_at"]
        return {"ok": True, "stream_id": stream_id, "uptime": uptime, "frequency": _frequencies.get(stream_id)}
    return {"ok": True, "streams": list(_streams.keys())}


def set_frequency(stream_id: str, hz: float) -> dict:
    _frequencies[stream_id] = float(hz)
    _write_freq_file(stream_id, float(hz))
    return {"ok": True, "stream_id": stream_id, "frequency": float(hz)}


def get_frequency(stream_id: str) -> Optional[float]:
    return _frequencies.get(stream_id)

