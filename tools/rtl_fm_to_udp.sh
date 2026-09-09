#!/usr/bin/env bash
set -euo pipefail

# rtl_fm_to_udp.sh
# Demodulate an RTL‑SDR frequency with rtl_fm and publish the audio via UDP (MPEG-TS/AAC)
#
# Usage:
#   ./tools/rtl_fm_to_udp.sh --freq 146.520M --out udp://127.0.0.1:5005 [--mode fm] [--rate 22050] [--gain 0] [--bitrate 64k]

FREQ=""
OUT="udp://127.0.0.1:5005"
MODE="fm"
RATE=22050
GAIN=0
BITRATE="64k"

print_help() {
  cat <<EOF
Usage: $0 --freq <frequency> [--out <udp://host:port>] [--mode fm|am|wbfm] [--rate <hz>] [--gain <db>] [--bitrate <aac>]

Example:
  $0 --freq 146.520M --out udp://127.0.0.1:5005 --mode fm --rate 22050 --gain 0 --bitrate 64k

This demodulates audio with rtl_fm and pipes 16-bit PCM into ffmpeg which encodes AAC and sends an MPEG-TS UDP stream to the given URL.
EOF
}

if [ $# -eq 0 ]; then
  print_help
  exit 1
fi

while [ $# -gt 0 ]; do
  case "$1" in
    --freq) FREQ="$2"; shift 2;;
    --out) OUT="$2"; shift 2;;
    --mode) MODE="$2"; shift 2;;
    --rate) RATE="$2"; shift 2;;
    --gain) GAIN="$2"; shift 2;;
    --bitrate) BITRATE="$2"; shift 2;;
    -h|--help) print_help; exit 0;;
    *) echo "Unknown arg: $1"; print_help; exit 2;;
  esac
done

if [ -z "$FREQ" ]; then
  echo "Error: --freq is required"
  print_help
  exit 2
fi

echo "Demodulating $FREQ -> $OUT (mode=$MODE rate=$RATE gain=$GAIN bitrate=$BITRATE)"

# rtl_fm outputs 16-bit signed PCM to stdout by default. Pipe into ffmpeg which will encode and send via UDP.
rtl_fm -f "$FREQ" -M "$MODE" -s $RATE -g $GAIN - | \
  ffmpeg -hide_banner -loglevel info -f s16le -ar $RATE -ac 1 -i - \
    -c:a aac -b:a $BITRATE -f mpegts "$OUT"
