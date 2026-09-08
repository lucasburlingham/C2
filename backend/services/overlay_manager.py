import os
import subprocess
import shlex
import threading
from typing import Dict, Optional

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
TOOLS_DIR = os.path.join(ROOT, 'tools')

_overlays: Dict[str, Dict] = {}
_lock = threading.Lock()

# logs directory
LOG_DIR = os.path.join(ROOT, 'backend', 'tmp', 'overlays')
os.makedirs(LOG_DIR, exist_ok=True)


def _script_for_engine(engine: str) -> Optional[str]:
    if engine == 'ffmpeg':
        return os.path.join(TOOLS_DIR, 'ffmpeg_atak_overlay.sh')
    if engine == 'gst':
        return os.path.join(TOOLS_DIR, 'gst_atak_overlay.sh')
    return None


def start_overlay(stream_id: str, engine: str = 'ffmpeg', audio_device: str = 'default', out_url: str = 'udp://127.0.0.1:5004') -> dict:
    script = _script_for_engine(engine)
    if script is None or not os.path.exists(script):
        return {'ok': False, 'error': f'unsupported engine or missing script: {engine}'}

    # If audio_device indicates 'ws' or 'websocket', start a TCP relay and rewrite audio_device
    relay_started = False
    relay_port = None
    if audio_device in ('ws', 'websocket'):
        try:
            from . import ws_audio_relay
            r = ws_audio_relay.start_relay(stream_id)
            if r.get('ok'):
                relay_port = r.get('port')
                audio_device = f"tcp://127.0.0.1:{relay_port}"
                relay_started = True
            else:
                return {'ok': False, 'error': 'failed to start websocket relay'}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    with _lock:
        if stream_id in _overlays:
            return {'ok': False, 'error': 'overlay already running'}

        cmd = [script, '--stream-id', stream_id, '--audio-device', audio_device, '--out', out_url]
        # Ensure script is executable
        try:
            os.chmod(script, os.stat(script).st_mode | 0o111)
        except Exception:
            pass
        # start subprocess detached
        try:
            # prepare log file
            log_path = os.path.join(LOG_DIR, f"{stream_id}.log")
            log_fd = open(log_path, 'ab', buffering=0)
            proc = subprocess.Popen(cmd, stdout=log_fd, stderr=subprocess.STDOUT, cwd=TOOLS_DIR)
        except Exception as e:
            # if relay was started, stop it
            if relay_started:
                try:
                    from . import ws_audio_relay
                    ws_audio_relay.stop_relay(stream_id)
                except Exception:
                    pass
            return {'ok': False, 'error': str(e)}

        _overlays[stream_id] = {'proc': proc, 'engine': engine, 'cmd': cmd, 'relay': relay_started, 'log_path': log_path, 'log_fd': log_fd}
        return {'ok': True, 'stream_id': stream_id, 'pid': proc.pid, 'log_path': log_path}


def stop_overlay(stream_id: str) -> dict:
    with _lock:
        meta = _overlays.get(stream_id)
        if not meta:
            return {'ok': False, 'error': 'not running'}
        proc = meta['proc']
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        # stop relay if one was started
        if meta.get('relay'):
            try:
                from . import ws_audio_relay
                ws_audio_relay.stop_relay(stream_id)
            except Exception:
                pass
        # close log file descriptor
        try:
            lf = meta.get('log_fd')
            if lf:
                try:
                    lf.close()
                except Exception:
                    pass
        except Exception:
            pass
        del _overlays[stream_id]
        return {'ok': True}


def get_logs(stream_id: str, lines: int = 200) -> Dict:
    """Return the last `lines` lines from the overlay log file."""
    meta = _overlays.get(stream_id)
    path = None
    if meta:
        path = meta.get('log_path')
    else:
        # try to locate on disk
        candidate = os.path.join(LOG_DIR, f"{stream_id}.log")
        if os.path.exists(candidate):
            path = candidate
    if not path or not os.path.exists(path):
        return {'ok': False, 'error': 'no log available', 'logs': ''}
    try:
        # read last N lines efficiently
        with open(path, 'rb') as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            block = 1024
            data = b''
            while size > 0 and data.count(b'\n') <= lines:
                read_size = min(block, size)
                f.seek(size - read_size, os.SEEK_SET)
                data = f.read(read_size) + data
                size -= read_size
            text = data.decode(errors='ignore')
            lines_list = text.splitlines()[-lines:]
            return {'ok': True, 'logs': '\n'.join(lines_list)}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'logs': ''}


def status_overlay(stream_id: str) -> dict:
    with _lock:
        meta = _overlays.get(stream_id)
        if not meta:
            return {'ok': False, 'running': False}
        proc = meta['proc']
        running = proc.poll() is None
        return {'ok': True, 'running': running, 'pid': proc.pid, 'engine': meta.get('engine')}


def list_overlays() -> Dict[str, Dict]:
    with _lock:
        out = {}
        for sid, meta in _overlays.items():
            proc = meta['proc']
            out[sid] = {'running': proc.poll() is None, 'pid': proc.pid, 'engine': meta.get('engine')}
        return out
