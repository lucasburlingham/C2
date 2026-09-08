# C2 & Mobile Communications System - Agent & Architecture Specification

> **Project Target:** Mobile Command and Control (C2) / Communications Node for Vehicle Integration
> **Target Audience:** GitHub Copilot Context & Workspace Guide (`AGENTS.md`)
> **Stack Architecture:** Python (FastAPI), C/C++ backend daemons, HTMX + Tailwind CSS (via CDN), WebSockets, WebRTC / Web Audio API, Docker / Systemd.

---

## 1. System Overview & Hardware Topology

```
+--------------------------------------------------------------------------+
|                              VEHICLE C2 NODE                             |
|                                                                          |
|  +-----------------------+              +-----------------------------+  |
|  |   Raspberry Pi 5 4GB  |              |     Raspberry Pi Zero 2W    |  |
|  |  (Primary C2 & SDR)   |              |     (DMR & Meshcore Node)   |  |
|  +-----------------------+              +-----------------------------+  |
|  | - TAK Server (FreeTAKServer)         | - WPSD (Pi-Star fork)       |  |
|  | - GPS-fed NTP (gpsd + chrony)        | - MMDVM DMR Radio HAT       |  |
|  | - SDR Receiver (OpenWebRX+ / Soapy)  | - Meshcore Serial Companion |  |
|  | - Rigctld (Xiegu G90 Control)        |                             |  |
|  | - FastAPI Web UI (HTMX + WebSockets) |                             |  |
|  +-----------------------+              +-----------------------------+  |
|              |                                         |                 |
|      (USB / GPIO / Ethernet)                    (USB / Serial)           |
+--------------|-----------------------------------------|-----------------+
               |                                         |
        [UBLOX USB GPS]                [Heltec V4 ESP32 LoRa Companion Node]
        [2x RTL-SDR v4]
		[Xiegu G90 (Audio/CAT)]
```

---

## 2. Core Software Stack & Component Matrix

### 2.1. Operating System & Time Synchronization (Raspberry Pi 5)
*   **Base OS:** Raspberry Pi OS Lite (64-bit, Debian Bookworm).
*   **GPS Daemon (`gpsd`):** Interfaces directly with the UBLOX USB-Serial NEMA GPS device (`/dev/ttyACM0` or `/dev/serial/by-id/...`). Provides raw NMEA positioning and 1PPS timing signals if wired.
*   **Time Synchronization (`chrony`):** Configured with `gpsd` SHM (Shared Memory) / PPS reference as primary stratum-0/1 time source, falling back to public NTP pools (NTP.org) when GPS lock is unavailable.

### 2.2. TAK Infrastructure (Raspberry Pi 5)
*   **TAK Server:** **FreeTAKServer (FTS)** (Python-based) or **TakServer-Docker**. Runs natively via Docker Compose. Handles CoT (Cursor on Target) TCP/UDP ingestion, SSL/TLS client cert authentication, and data sync.
*   **CoT Gateway:** A lightweight custom Python script (`cot_gateway.py`) running as a systemd service that listens to local sensor states (GPS from `gpsd`, radio status) and multicasts CoT XML packets over the local network or TAK server uplink.

### 2.3. Software Defined Radio & Transceiver Control (Raspberry Pi 5)
*   **SDR Receiver Daemons:**
    *   **SoapySDR / rtl-sdr:** Drivers and backend libraries for the dual RTL-SDR v4 dongles.
    *   **OpenWebRX+ / OpenWebRX:** Provides multi-channel waterfall generation, demodulation (AM, FM, SSB, DMR metadata), and audio streaming over WebSockets/WebRTC.
*   **Rig Control (`Hamlib` - `rigctld`):**
    *   `rigctld -m 3090 -r /dev/ttyUSB0 -s 19200`: Controls frequency, mode, and PTT states for the **Xiegu G90** transceiver connected via USB/CAT serial cable.
*   **Audio Gateway & PTT Interface (`PulseAudio / PipeWire` or direct ALSA + WebRTC):**
    *   Bridges USB audio interface (connected to Xiegu G90 audio line-out/in) to browser WebSockets. Enables browser-based push-to-talk (PTT) keyed via spacebar or UI button.

### 2.4. DMR Radio & Secondary Node (Raspberry Pi Zero 2W)
*   **WPSD (Wireless Parrot/Repeater Software Dashboard):** Pi-Star derivative running on the Pi Zero 2W with MMDVM HAT for local DMR repeater/hotspot communications.
*   **Meshcore IP-Serial Companion:**
    *   Connects to the RPi Zero 2W via USB/Serial.
    *   Runs `meshcore-router` or bridge daemon translating IP packets (TCP/UDP/HTTP API) into Meshtastic/Meshcore radio protocol frames over serial/LoRa hardware.

---

## 3. Unified Web UI Specification (HTMX + FastAPI)

### 3.1. Architectural Guidelines for Copilot
*   **No Server-Side JavaScript (Node.js):** The backend must be 100% Python (FastAPI).
*   **Frontend Philosophy:** Server-driven UI using HTML fragments, **HTMX** for dynamic AJAX updates, and **Tailwind CSS** loaded via CDN for a tactical dark-mode styling (slate/zinc grays with amber/green tactical accents).
*   **Real-Time Transport:** WebSockets (`/ws/telemetry`, `/ws/audio`, `/ws/sdr`) for low-latency PTT audio streaming, waterfall display updates, and live GPS/CoT telemetry feeds.

### 3.2. Single-Pane-of-Glass Layout
```
+--------------------------------------------------------------------------+
| [C2 VEHICLE NODE] - TAK: ONLINE | GPS: 3D FIX | NTP: SYNCD | MESH: 4 NODES |
+-----------------------------------+--------------------------------------+
|                                   |                                      |
|  PANEL 1: SDR 1 & SDR 2 WATERFALL |  PANEL 2: XIEGU G90 RADIO CONTROL    |
|  - Interactive frequency tuning   |  - VFO Frequency: [ 14.285.00 MHz ]  |
|  - Waterfall spectrogram (Canvas) |  - Mode: [ USB ] S-Meter: [ S9 ]     |
|  - Demodulator (AM/FM/SSB)        |  - PTT BUTTON / SPACEBAR: [ KEYED ]  |
|  - Audio output stream            |  - Audio Gain / Mic Level Sliders    |
|                                   |                                      |
+-----------------------------------+--------------------------------------+
|                                   |                                      |
|  PANEL 3: TAK CoT MULTICAST MGR   |  PANEL 4: MESHCORE & NTP STATUS      |
|  - Send manual PLI / Spot report  |  - Mesh nodes list & packet stats    |
|  - Active CoT message stream log  |  - NTP offset, jitter, GPS sat count |
|  - Quick marker presets           |  - WPSD DMR status monitor           |
|                                   |                                      |
+--------------------------------------------------------------------------+
```

---

## 4. Implementation Blueprint & File Structure

When prompting GitHub Copilot to scaffold or build this project, instruct it to follow this exact repository structure:

```text
vehicle-c2-node/
├── docker-compose.yml
├── README.md
├── AGENTS.md
├── backend/
|   ├── Dockerfile
|   ├── requirements.txt
|   ├── main.py                # FastAPI app entrypoint
|   ├── routers/
|   |   ├── sdr.py             # RTL-SDR / SoapySDR integration & audio bridge
|   |   ├── radio.py           # Rigctld interface for Xiegu G90 & PTT
|   |   ├── tak.py             # CoT generation and UDP/TCP multicast
|   |   ├── system.py          # GPS, NTP, and Meshcore status endpoints
|   |   └── websocket.py       # WS manager for live audio, waterfall, & telemetry
|   └── services/
|       ├── gps_service.py     # gpsd polling & position parsing
|       ├── rig_service.py     # Hamlib socket communication
|       ├── cot_service.py     # Cursor on Target XML builder
|       └── mesh_service.py    # Meshcore serial bridge client
├── frontend/
|   ├── templates/
|   |   ├── index.html         # Main dashboard layout
|   |   └── partials/
|   |       ├── sdr_panel.html
|   |       ├── radio_panel.html
|   |       ├── tak_panel.html
|   |       └── status_panel.html
|   └── static/
|       ├── css/               # Custom tactical styling overrides
|       └── js/
|           ├── audio-node.js  # Web Audio API receiver for SDR / Radio audio
|           └── ptt-listener.js# Spacebar & UI button global PTT keyboard listener
└── systemd/
    ├── gpsd.service.override
    └── c2-backend.service
```

---

## 5. Copilot Prompting Guide & Code Snippets

### Example 1: FastAPI WebSocket PTT & Radio Handler (`backend/routers/radio.py`)
```python
# Instruct Copilot to generate Hamlib rigctld TCP socket wrapper and PTT state machine
import socket
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(prefix="/radio", tags=["Radio G90"])
logger = logging.getLogger("c2.radio")

RIGCTLD_HOST = "127.0.0.1"
RIGCTLD_PORT = 4532

@router.post("/ptt")
async def set_ptt(keying: bool):
    cmd = "T 1\n" if keying else "T 0\n"
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((RIGCTLD_HOST, RIGCTLD_PORT))
            s.sendall(cmd.encode())
            response = s.recv(1024).decode()
        return {"status": "success", "ptt": keying, "response": response.strip()}
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

### Example 2: Frontend PTT Global Spacebar Listener (`frontend/static/js/ptt-listener.js`)
```javascript
// Instruct Copilot to handle Spacebar down/up for PTT with safety lockout to prevent typing lock
let isPttActive = false;

document.addEventListener('keydown', async (e) => {
    if (e.code === 'Space' && !isPttActive && document.activeElement.tagName !== 'INPUT') {
        e.preventDefault();
        isPttActive = true;
        document.getElementById('ptt-status-badge').classList.remove('bg-zinc-700', 'text-zinc-300');
        document.getElementById('ptt-status-badge').classList.add('bg-red-600', 'text-white', 'animate-pulse');
        document.getElementById('ptt-status-badge').innerText = 'TX ACTIVE';
        await fetch('/radio/ptt?keying=true', { method: 'POST' });
    }
});

document.addEventListener('keyup', async (e) => {
    if (e.code === 'Space' && isPttActive) {
        e.preventDefault();
        isPttActive = false;
        document.getElementById('ptt-status-badge').classList.remove('bg-red-600', 'text-white', 'animate-pulse');
        document.getElementById('ptt-status-badge').classList.add('bg-zinc-700', 'text-zinc-300');
        document.getElementById('ptt-status-badge').innerText = 'RX STANDBY';
        await fetch('/radio/ptt?keying=false', { method: 'POST' });
    }
});
```

### Example 3: Cursor on Target (CoT) XML Generator (`backend/services/cot_service.py`)
```python
# Instruct Copilot to build standard MIL-STD-2525 / CoT XML messages for PLI broadcasting
import time
import xml.etree.ElementTree as ET

def generate_pli_cot(callsign: str, lat: float, lon: float, hae: float, speed: float, course: float) -> str:
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    stale = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + 60))
    
    event = ET.Element("event", {
        "version": "2.0",
        "uid": f"VEHICLE-C2-{callsign}",
        "type": "a-f-G-U-C",  # Friend, Ground, Combat Vehicle
        "time": now,
        "start": now,
        "stale": stale,
        "how": "m-g"
    })
    
    point = ET.SubElement(event, "point", {
        "lat": str(lat),
        "lon": str(lon),
        "hae": str(hae),
        "ce": "5.0",
        "le": "5.0"
    })
    
    detail = ET.SubElement(event, "detail")
    ET.SubElement(detail, "contact", {"callsign": callsign})
    ET.SubElement(detail, "track", {"course": str(course), "speed": str(speed)})
    
    return ET.tostring(event, encoding="utf-8", method="xml").decode("utf-8")
```

---

## 6. Verification & Systemd Deployment Checklist

1.  **GPS & Chrony Validation:**
    *   Run `gpsmon` or `cgps` to verify UBLOX NMEA fix.
    *   Run `chronyc sources` to ensure `SHM0` / GPS PPS is marked with `^*` (active reference).
2.  **Rigctld Validation:**
    *   Test serial connection: `rigctl -m 3090 -r /dev/ttyUSB0 -s 19200 f` to query current frequency.
3.  **Docker & FastAPI Startup:**
    *   `docker compose up -d` to spin up FreeTAKServer, Redis, and the C2 FastAPI container.
4.  **Browser Interface:**
    *   Navigate to `http://<pi5-ip>:8000` to access the unified HTMX dashboard.