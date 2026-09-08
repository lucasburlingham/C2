import threading
import time

_streams = {}


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
    return {"ok": True, "stream_id": stream_id}


def stop_stream(stream_id: str) -> dict:
    meta = _streams.get(stream_id)
    if not meta:
        return {"ok": False, "message": "not found"}
    meta["stop"].set()
    del _streams[stream_id]
    return {"ok": True, "stream_id": stream_id}


def get_status(stream_id: str = None) -> dict:
    if stream_id:
        meta = _streams.get(stream_id)
        if not meta:
            return {"ok": False, "message": "not found"}
        return {"ok": True, "stream_id": stream_id, "uptime": time.time() - meta["started_at"]}
    return {"ok": True, "streams": list(_streams.keys())}
