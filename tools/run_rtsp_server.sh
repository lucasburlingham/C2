#!/usr/bin/env bash
set -euo pipefail
# Helper to run rtsp-simple-server locally or show Docker command.

if command -v rtsp-simple-server >/dev/null 2>&1; then
  echo "Found rtsp-simple-server in PATH, launching..."
  exec rtsp-simple-server
else
  echo "rtsp-simple-server not found in PATH. You can run it via Docker:" >&2
  echo "docker run --rm -p 8554:8554 -v \"$(pwd)/tools/rtsp-simple-server.yml:/rtsp-simple-server.yml\":ro bluenviron/rtsp-simple-server:latest" >&2
  echo
  echo "Or install from https://github.com/aler9/rtsp-simple-server" >&2
  exit 1
fi
