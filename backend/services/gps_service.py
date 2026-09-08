import socket
import json
import time

GPSD_HOST = "127.0.0.1"
GPSD_PORT = 2947


def _read_json_line(sock, deadline):
    buf = b""
    sock.settimeout(max(0.1, deadline - time.time()))
    while time.time() < deadline:
        try:
            chunk = sock.recv(4096)
            if not chunk:
                break
            buf += chunk
            if b"\n" in buf:
                line, _, rest = buf.partition(b"\n")
                return line.decode(errors="ignore")
        except socket.timeout:
            break
    return None


def get_gps_status(timeout: float = 2.0):
    """Try to query gpsd and return a simple status dict.

    Returns: {fix: bool, lat: float|None, lon: float|None, alt: float|None, time: str|None}
    """
    deadline = time.time() + timeout
    try:
        with socket.create_connection((GPSD_HOST, GPSD_PORT), timeout=1) as s:
            # request JSON watches
            s.sendall(b'?WATCH={"enable":true,"json":true}\n')
            # read a few lines until we get a TPV report or timeout
            while time.time() < deadline:
                line = _read_json_line(s, deadline)
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if obj.get("class") == "TPV":
                    lat = obj.get("lat")
                    lon = obj.get("lon")
                    alt = obj.get("alt")
                    time_str = obj.get("time")
                    # mode >=2 means 2D or 3D fix
                    mode = obj.get("mode", 0)
                    return {"fix": mode >= 2, "lat": lat, "lon": lon, "alt": alt, "time": time_str}
    except Exception:
        pass
    return {"fix": False, "lat": None, "lon": None, "alt": None, "time": None}

