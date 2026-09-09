# Installation & RTL‑SDR → ffmpeg Integration

This document describes common ways to take demodulated audio from an RTL‑SDR (or other demodulator) and feed it into the project's `ffmpeg` overlay pipeline (see `tools/ffmpeg_atak_overlay.sh`). Pick the approach that best fits your platform and latency requirements.

Prerequisites
- `rtl-sdr` tools (e.g. `rtl_fm`) or your preferred demodulator (GNU Radio, GStreamer)
- `ffmpeg` (with codecs for aac/libx264)
- `alsa-utils` (`arecord`, `aplay`) for ALSA loopback approach on Linux
- Optionally `rtsp-simple-server` (or Docker) for RTSP ingestion

Recommendations
- For local low-latency routing: use ALSA loopback (`snd-aloop`).
- For simple piping or remote consumption: stream demodulated audio over `udp://` or `tcp://` and give that URL to the overlay manager.

1) Direct pipe into ffmpeg (stdin)
This is quick for one-off tests but not used by `ffmpeg_atak_overlay.sh` directly (the script expects an ALSA device or a URL). Adjust sample format and rate to match your demodulator.

Example (FM demod via `rtl_fm` -> ffmpeg -> UDP):

```bash
rtl_fm -f 146.520M -M fm -s 22050 - | \
  ffmpeg -f s16le -ar 22050 -ac 1 -i - \
    -c:v libx264 -preset veryfast -tune zerolatency -pix_fmt yuv420p \
    -c:a aac -b:a 64k -f mpegts udp://127.0.0.1:5005
```

Notes:
- `-f s16le -ar 22050 -ac 1` must match the raw PCM output from your demodulator.
- This writes the audio into ffmpeg's stdin. To use this with the overlay script, you would run a separate ffmpeg instance that writes to a network URL and then point the overlay `--audio-device` at that URL.

2) ALSA loopback (recommended for local setups)
This method creates a virtual ALSA device so you can write demodulated audio to the loopback playback device and have ffmpeg capture it as a normal capture device.

Enable loopback (requires root):

```bash
sudo modprobe snd-aloop
# verify with: arecord -l  or aplay -l
```

Send demodulated audio into the loopback playback device:

```bash
# Example: rtl_fm -> raw PCM -> aplay to loopback (playback device hw:Loopback,0,0)
rtl_fm -f 146.520M -M fm -s 22050 - | \
  aplay -f S16_LE -r 22050 -c 1 -D hw:Loopback,0,0
```

Find the corresponding capture device (often `hw:Loopback,1,0`) and start the overlay pointing ffmpeg at it:

```bash
# Start overlay via API (example)
curl -X POST "http://localhost:8000/sdr/sdr1/overlay/start?engine=ffmpeg&audio_device=hw:Loopback,1,0&out_url=rtsp://127.0.0.1:8554/sdr1"
```

`ffmpeg_atak_overlay.sh` will use `-f alsa -i hw:Loopback,1,0` for capture.

3) Network stream (UDP/TCP)
Demodulate locally and publish audio to a network URL; point the overlay to that URL.

Example: publish demodulated audio as an MPEG‑TS/UDP stream

```bash
rtl_fm -f 146.520M -M fm -s 22050 - | \
  ffmpeg -f s16le -ar 22050 -ac 1 -i - -c:a aac -b:a 64k -f mpegts udp://127.0.0.1:5005

# Then start the overlay with audio_device=udp://127.0.0.1:5005
curl -X POST "http://localhost:8000/sdr/sdr1/overlay/start?engine=ffmpeg&audio_device=udp://127.0.0.1:5005&out_url=rtsp://127.0.0.1:8554/sdr1"
```

Alternatively, you can stream raw PCM via TCP and have ffmpeg read it with explicit input format flags — this requires careful format matching.

4) WebSocket path (browser mic → relay → ffmpeg)
This project includes a `ws_audio_relay` service for browser audio; the overlay manager can start a relay and expose a `tcp://127.0.0.1:<port>` input that `ffmpeg` can read. This is already integrated into `overlay_manager.start_overlay` when `audio_device=ws`.

5) RTSP server for overlay publishing
If you plan to publish overlays to RTSP for remote viewing, run `rtsp-simple-server`:

Docker example:

```bash
docker run --rm -p 8554:8554 -v "$(pwd)/tools/rtsp-simple-server.yml:/rtsp-simple-server.yml":ro bluenviron/rtsp-simple-server:latest
```

Then start an overlay with `out_url=rtsp://127.0.0.1:8554/sdr1` (the UI also supports this).

6) Troubleshooting & tips
- Check `backend/tmp/overlays/<stream>.log` for ffmpeg/gst output and errors.
- Use `arecord -l` / `aplay -l` to find ALSA device names.
- Ensure sample rates and formats match between demodulator and ffmpeg (`s16le`, sample rate, channels).
- If `setSinkId` or device labels are missing in the browser UI, grant microphone permission or use a Chromium-based browser.
- If RTSP publish fails, check `rtsp-simple-server` logs and verify network reachability.

Adding helper scripts
If you want, I can add helper scripts under `tools/` to:
- spawn `rtl_fm` → `aplay` into the loopback for a given frequency and device
- spawn `rtl_fm` → `ffmpeg` → `udp://` for quick test streaming

If you tell me which demodulator you prefer (`rtl_fm`, GNU Radio, or GStreamer) and whether you want ALSA loopback or network streaming, I'll add a ready-to-run helper script to `tools/` and example commands.

7) Systemd service
To run the full stack via systemd, a helper runner script and a unit file are provided in the repository:

- `tools/c2_service_runner.sh` — starts optional RTSP helper and the FastAPI backend (`uvicorn`).
- `packaging/systemd/c2.service` — systemd unit which expects the repository to be installed at `/opt/c2` by default. You can override the path by editing the `Environment=C2_ROOT=` line in the unit file.

Install and enable the service (example assuming you install the repository to `/opt/c2`):

```bash
# copy service file
sudo cp packaging/systemd/c2.service /etc/systemd/system/c2.service
# ensure runner is executable and placed in the same repository path (/opt/c2/tools/c2_service_runner.sh)
sudo chmod +x /opt/c2/tools/c2_service_runner.sh
# reload systemd and enable the service
sudo systemctl daemon-reload
sudo systemctl enable --now c2.service
sudo journalctl -u c2.service -f
```

The runner will start the RTSP helper (if present) and `uvicorn`. Logs are written to `/var/log/c2/`.
# Installation & Hardware Guide

This document guides a systems administrator through the hardware, interfaces, and deployment options for the Vehicle C2 Node project.

## Overview

This repository provides a small command-and-control node intended to run on on-premise hardware near radios, SDRs, and GPS receivers. The software can be run via `docker-compose` or directly as a Python service (systemd). Key integrations:
- `rigctld` (Hamlib) for radio PTT / CAT
- `gpsd` for GPS input
- Optional SDR hardware for radio audio

Read the example systemd unit at [systemd/c2-backend.service](systemd/c2-backend.service) for the non-containerized startup option.

## Required Hardware (Minimum)

- Compute: x86_64 or ARM64 single-board/commercial computer
  - Recommended minimum: 4 CPU cores, 4 GiB RAM, 16 GiB storage (eMMC or SSD/SD)
  - Example: Raspberry Pi 4 (4GB) for edge, Intel NUC or small server for central
- Network: Gigabit Ethernet port; static IP recommended
- Power: Reliable PSU and inline surge protection
- Radio interface: one supported radio with a USB/serial CAT/PTT interface (USB-to-serial adapter if needed)
- GPS receiver: USB GPS (USB serial or PPS-capable) compatible with `gpsd`
- Cabling: USB, serial adapters, and audio patch cables as required by your radios

## Recommended Hardware (Production)

- Compute: 4+ CPU cores, 8+ GiB RAM, NVMe/SSD storage (50 GiB+)
- UPS for clean shutdown and power conditioning
- SDR hardware (optional): LimeSDR, HackRF, or RTL-SDR depending on needs
- Professional USB audio interface if bridging analog audio (USB soundcard with mic/line in/out)
- Enclosure with cooling and vibration isolation for vehicle installations

## Peripheral & Interface Notes

- Radio Control (PTT/CAT): The project uses `rigctld` (Hamlib). Radios should expose a CAT or accessory port (FTDI-style USB serial or RS-232). Configure the device node (e.g. `/dev/ttyUSB0`) and run `rigctld` bound to localhost (port 4532 by default).
- GPS: Use a GPS receiver supported by `gpsd`. Configure `/etc/default/gpsd` (or systemd unit) to point to the device node. For precise timing, choose a GPS with PPS output and proper kernel support.
- SDR: Containers/services expect SDR endpoints to be available. When running in Docker, expose the SDR device(s) into the container (see Docker notes below).
- Audio & PTT: If using analog audio/keying, provide an audio interface and a hardware keying circuit (or use radio-provided PTT over CAT).

## Network & Security

- Place the C2 node on a trusted management VLAN or behind a firewall. Only expose required ports (default backend port 8000) where necessary.
- Use SSH keys for administration. Configure `ufw`/`iptables` to restrict access to management ports and radio control sockets.

## Deployment Options

Option A — Docker (recommended for portability)

1. Install Docker and Docker Compose (Debian/Ubuntu example):

```bash
sudo apt update
sudo apt install -y docker.io docker-compose git
sudo systemctl enable --now docker
```

2. Clone repository and start services:

```bash
git clone <repo-url> /opt/vehicle-c2-node
cd /opt/vehicle-c2-node
sudo docker-compose up -d --build
```

Note: Do not add a top-level `version:` key to your `docker-compose.yml`.
Modern Docker Compose (v2) uses the compose specification without a `version` field; using the newer format ensures compatibility with current Docker and Compose implementations.

3. Device access notes for Docker:
   - To give containers access to serial devices (rig/GPS), edit `docker-compose.yml` to add `devices:` entries under the `backend` service, e.g.:

```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    devices:
      - "/dev/ttyUSB0:/dev/ttyUSB0"
      - "/dev/ttyUSB1:/dev/ttyUSB1"
    volumes:
      - ./backend:/app
    restart: unless-stopped
```

   - For GPSD you may run `gpsd` on the host and leave the backend container to talk to `127.0.0.1:2947` (bind containers to host network or map ports carefully).

Option B — Systemd / Native Python

1. Install system dependencies and Python runtime:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
git clone <repo-url> /opt/vehicle-c2-node
cd /opt/vehicle-c2-node/backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

2. Install and configure `gpsd` and `hamlib`:

```bash
sudo apt install -y gpsd gpsd-clients hamlib-utils
# Set DEVICES in /etc/default/gpsd to point at your GPS (e.g. /dev/ttyUSB0)
```

3. Install and enable the provided systemd unit:

```bash
sudo cp systemd/c2-backend.service /etc/systemd/system/c2-backend.service
sudo systemctl daemon-reload
sudo systemctl enable --now c2-backend.service
```

4. Start `rigctld` for your radio (example):

```bash
sudo rigctld -m <rig-model> -r /dev/ttyUSB0 -s 4532 -R
```

Replace `<rig-model>` with the Hamlib model number for your radio.

## Build & Install (detailed)

This section contains explicit build and install steps for both Docker and native installations, plus configuration snippets for `gpsd`, `rigctld`, udev, and systemd.

1) Prepare host

```bash
# Update and install common packages
sudo apt update
sudo apt install -y git curl ca-certificates \
    build-essential python3 python3-venv python3-pip \
    docker.io docker-compose gpsd gpsd-clients hamlib-utils \
    udev
```

Create a dedicated service user (recommended):

```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin c2
sudo usermod -aG dialout c2   # allow serial device access
```

2) Docker build & run (recommended for most installs)

```bash
cd /opt/vehicle-c2-node
# build and start containers
sudo docker-compose build --no-cache
sudo docker-compose up -d

# to rebuild after code changes
sudo docker-compose up -d --build
```

If your radio or GPS appears as `/dev/ttyUSB0`, ensure `docker-compose.yml` exposes the device. Example `backend` service fragment:

```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    devices:
      - "/dev/ttyUSB0:/dev/ttyUSB0"
    volumes:
      - ./backend:/app
    restart: unless-stopped
```

3) Native Python install (systemd)

```bash
git clone <repo-url> /opt/vehicle-c2-node
cd /opt/vehicle-c2-node/backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# run for testing
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Create an environment file for runtime configuration, e.g. `/etc/vehicle-c2-node.env`:

```
# /etc/vehicle-c2-node.env
RIGCTLD_HOST=127.0.0.1
RIGCTLD_PORT=4532
GPSD_HOST=127.0.0.1
GPSD_PORT=2947
# add any other env vars here
```

Update the systemd unit to load the env file (example):

```ini
[Unit]
Description=Vehicle C2 Backend Service
After=network.target

[Service]
User=c2
WorkingDirectory=/opt/vehicle-c2-node
EnvironmentFile=/etc/vehicle-c2-node.env
ExecStart=/usr/bin/env uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Install the unit and enable the service:

```bash
sudo cp systemd/c2-backend.service /etc/systemd/system/c2-backend.service
sudo systemctl daemon-reload
sudo systemctl enable --now c2-backend.service
```

4) `gpsd` configuration

Edit `/etc/default/gpsd` (Debian/Ubuntu) to point to your device and enable the daemon. Minimal example:

```
START_DAEMON="true"
GPSD_OPTIONS=""
DEVICES="/dev/ttyUSB1"
USBAUTO="false"
GPSD_SOCKET="/var/run/gpsd.sock"
```

Then:

```bash
sudo systemctl enable --now gpsd.socket
sudo systemctl restart gpsd
# verify
gpspipe -w | head -n 5
```

5) `rigctld` (Hamlib) for radio CAT/PTT

Start `rigctld` for your radio model number and device node. Example using a common FTDI USB cable:

```bash
sudo rigctld -m <rig-model> -r /dev/ttyUSB0 -s 4532 -R
```

Consider running `rigctld` under systemd as well; example unit snippet:

```ini
[Unit]
Description=Hamlib rigctld
After=network.target

[Service]
ExecStart=/usr/bin/rigctld -m <rig-model> -r /dev/ttyUSB0 -s 4532 -R
User=c2
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

6) udev rule for stable device naming (optional but recommended)

Create a udev rule under `/etc/udev/rules.d/99-vehicle-c2.rules` to symlink devices by serial/VID/PID. Example for an FTDI adapter:

```
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", SYMLINK+="vehicle-radio", GROUP="dialout", MODE="0660"
```

Then reload rules:

```bash
sudo udevadm control --reload-rules && sudo udevadm trigger
ls -l /dev/vehicle-radio
```

7) Firewall & service exposure

Allow management access only as needed. Example `ufw` rules:

```bash
sudo ufw allow from 10.0.0.0/24 to any port 8000 proto tcp   # management network
sudo ufw enable
```

8) Verification (quick commands)

```bash
# Check backend
curl -fsS http://localhost:8000/

# Check rigctld via telnet
telnet localhost 4532

# Check gpsd
gpspipe -w | head -n 5
```

## Verification

- Backend: open the UI at `http://<host>:8000/` and exercise the example endpoints:
  - `GET /sdr/status` — returns SDR status placeholder
  - `GET /radio/status` — checks `rigctld` connection
  - `POST /radio/ptt?keying=true` — press PTT; `false` to release
- GPS: use `cgps` or `gpspipe -w` on the host to confirm GPSD provides TPV reports
- Rig: use `telnet localhost 4532` or `rigctl -m <model> -r /dev/ttyUSB0` to confirm connectivity

## Troubleshooting

- If `rigctld` returns connection errors, verify device nodes and permissions (`ls -l /dev/ttyUSB*`). Add the service user to the `dialout` group if necessary.
- If GPS fix is not present, check antenna placement, serial device baud, and PPS wiring.
- Docker device access problems: ensure the Docker service has permission to access the device nodes and consider running the container with `privileged: true` only as a last resort.

## Accessories & Safety

- Antennas, coax, grounding, lightning protection, and proper RF filtering are the responsibility of the installer. Use surge protectors and an inline lightning/arrestor where appropriate.
- Secure radios physically in vehicles; provide vibration mounts and temperature management.

## Notes & Next Steps

- This system is intentionally modular; expand `backend/routers` and `services` to add radio models, SDR backends, or mesh protocols.
- Consider placing the C2 node behind an authenticated reverse proxy if exposed outside a trusted network.

For further customization, see the `backend` source and the example systemd unit at [systemd/c2-backend.service](systemd/c2-backend.service).
