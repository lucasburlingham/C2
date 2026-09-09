#!/usr/bin/env bash
set -euo pipefail

# c2_service_runner.sh
# Starts the C2 application stack: optional RTSP server and the FastAPI backend (uvicorn).
# Designed to be run by systemd or directly. It will attempt to discover the repository root
# when not provided via C2_ROOT environment variable.

ROOT="${C2_ROOT:-}"
if [ -z "$ROOT" ]; then
  # compute root relative to this script
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi

LOGDIR="/var/log/c2"
mkdir -p "$LOGDIR"

PIDFILE="/run/c2_service.pid"

RTSP_SCRIPT="$ROOT/tools/run_rtsp_server.sh"
UVICORN_LOG="$LOGDIR/uvicorn.log"
RTSP_LOG="$LOGDIR/rtsp.log"

PIDS=()

function start_rtsp() {
  # start RTSP server if helper exists and RTSP_ENABLE is not "0"
  if [ -x "$RTSP_SCRIPT" ] && [ "${RTSP_ENABLE:-1}" != "0" ]; then
    echo "Starting RTSP server..." >> "$RTSP_LOG" 2>&1 || true
    nohup "$RTSP_SCRIPT" >> "$RTSP_LOG" 2>&1 &
    PIDS+=("$!")
    echo "rtsp pid $!" >> "$RTSP_LOG" 2>&1 || true
  fi
}

function start_uvicorn() {
  echo "Starting uvicorn..." >> "$UVICORN_LOG" 2>&1 || true
  # run uvicorn from the same python environment; rely on PATH
  nohup python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 >> "$UVICORN_LOG" 2>&1 &
  PIDS+=("$!")
  echo "uvicorn pid $!" >> "$UVICORN_LOG" 2>&1 || true
}

function stop_all() {
  echo "Stopping C2 processes..." >> "$LOGDIR/c2-service.log" 2>&1 || true
  for pid in "${PIDS[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" || true
      wait "$pid" 2>/dev/null || true
    fi
  done
}

trap 'stop_all; exit 0' SIGINT SIGTERM

start_rtsp
start_uvicorn

echo "$BASHPID" > "$PIDFILE" 2>/dev/null || true

# wait on all child processes; if any exit, stop the rest and exit
while true; do
  for pid in "${PIDS[@]}"; do
    if ! kill -0 "$pid" 2>/dev/null; then
      echo "Process $pid exited; shutting down" >> "$LOGDIR/c2-service.log" 2>&1 || true
      stop_all
      exit 0
    fi
  done
  sleep 1
done
