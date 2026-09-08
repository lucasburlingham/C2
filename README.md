# Vehicle C2 Node

This repository is a scaffold for the Vehicle C2 Node described in AGENT.md. It contains a FastAPI backend, HTMX-driven frontend templates, and Docker support.

Quick start (local):

```bash
python -m venv .venv
source .venv/Scripts/activate  # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Or with Docker Compose:

```bash
docker compose up --build -d

VLC + ATAK / WinTAK streaming notes
----------------------------------

- To listen in VLC: you can run an ffmpeg relay locally that reads your SDR audio input and streams as UDP/MPEG-TS. Example (adapt audio input):

```bash
# Example: create a 64kbps AAC MPEG-TS UDP stream local:5004
ffmpeg -f dshow -i audio="Your Microphone Device" -c:a aac -b:a 64k -f mpegts udp://127.0.0.1:5004
```

- In VLC, open Network Stream and use `udp://@127.0.0.1:5004`.


- To produce a 500x400 video with a live frequency overlay for ATAK/WinTAK use the `tools/ffmpeg_atak_overlay.sh` script (Debian/Linux) or `tools/gst_atak_overlay.sh`. These scripts read the frequency file written by the backend at `backend/tmp/<stream_id>.freq.txt` and overlay it on a black video, then stream via UDP to `127.0.0.1:5004`.

- Update the SDR frequency using the API:

```bash
curl -X POST "http://localhost:8000/sdr/sdr1/frequency?hz=14285000"
```

The backend will write the frequency text to `backend/tmp/sdr1.freq.txt` which is read by the ffmpeg/gst overlay tools.

Server-managed overlay controls
------------------------------

You can start and stop overlay processes from the backend API. Examples:

Start an overlay (ffmpeg engine):

```bash
curl -X POST "http://localhost:8000/sdr/sdr1/overlay/start?engine=ffmpeg&audio_device=default&out_url=udp://127.0.0.1:5004"
```

Stop an overlay:

```bash
curl -X POST "http://localhost:8000/sdr/sdr1/overlay/stop"
```

Overlay status:

```bash
curl "http://localhost:8000/sdr/sdr1/overlay/status"
```

List overlays:

```bash
curl "http://localhost:8000/sdr/overlay/list"
```

The backend will spawn `tools/ffmpeg_atak_overlay.sh` or `tools/gst_atak_overlay.sh` depending on the `engine` parameter and manage the process lifecycle.

```
