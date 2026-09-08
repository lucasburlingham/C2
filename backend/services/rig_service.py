import socket
import os

RIGCTLD_HOST = os.environ.get("RIGCTLD_HOST", "127.0.0.1")
RIGCTLD_PORT = int(os.environ.get("RIGCTLD_PORT", "4532"))


def _send_cmd(cmd: str, timeout: float = 2.0) -> str:
    try:
        with socket.create_connection((RIGCTLD_HOST, RIGCTLD_PORT), timeout=timeout) as s:
            s.sendall(cmd.encode())
            # rigctld typically responds with a line
            data = s.recv(4096)
            return data.decode(errors="ignore").strip()
    except Exception as e:
        return f"ERROR: {e}"


def set_ptt_state(state: bool) -> dict:
    """Key or unkey PTT via rigctld. Returns a result dict."""
    cmd = "T 1\n" if state else "T 0\n"
    resp = _send_cmd(cmd)
    return {"ok": not resp.startswith("ERROR"), "ptt": state, "response": resp}


def get_raw_status() -> str:
    # Request a frequency read; fallback to returning raw response
    resp = _send_cmd("f\n")
    return resp

