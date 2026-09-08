#!/usr/bin/env bash
set -euo pipefail
# ffmpeg_atak_overlay.sh
# Create a 500x400 video with a live frequency overlay (reads backend/tmp/<stream_id>.freq.txt)
# and stream it via UDP for ATAK/WinTAK or play in VLC.
#
# Usage:
#   ./tools/ffmpeg_atak_overlay.sh [--stream-id sdr1] [--audio-device "hw:1,0"] [--out udp://127.0.0.1:5004]
#

STREAM_ID="sdr1"
AUDIO_DEVICE="default"
OUT_URL="udp://127.0.0.1:5004"
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FPS=15
WIDTH=500
HEIGHT=400

print_help() {
  cat <<EOF
Usage: $0 [--stream-id id] [--audio-device device] [--out url] [--font path]

Examples:
  $0 --stream-id sdr1 --audio-device default --out udp://127.0.0.1:5004

This script reads frequency from backend/tmp/<stream_id>.freq.txt and overlays it on a $WIDTH x $HEIGHT black video.
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --stream-id) STREAM_ID="$2"; shift 2;;
    --audio-device) AUDIO_DEVICE="$2"; shift 2;;
    --out) OUT_URL="$2"; shift 2;;
    --font) FONT="$2"; shift 2;;
    -h|--help) print_help; exit 0;;
    *) echo "Unknown arg: $1"; print_help; exit 2;;
  esac
done

FREQ_FILE="$(dirname "$(realpath "$0")")/../backend/tmp/${STREAM_ID}.freq.txt"
USER_FILE="$(dirname "$(realpath "$0")")/../backend/tmp/${STREAM_ID}.user.txt"
LABEL_FILE="$(dirname "$(realpath "$0")")/../backend/tmp/${STREAM_ID}.label.txt"

if [ ! -f "$FREQ_FILE" ]; then
  # create an empty file so drawtext can read it
  mkdir -p "$(dirname "$FREQ_FILE")"
  echo "no-freq" > "$FREQ_FILE"
fi

echo "Streaming video $WIDTH x $HEIGHT with label overlay from $LABEL_FILE to $OUT_URL"

# prepare audio input args depending on scheme
if echo "$AUDIO_DEVICE" | grep -qE '^(tcp|udp|http|https)://'; then
  AUDIO_INPUT_ARGS=( -i "$AUDIO_DEVICE" )
else
  # default to ALSA capture
  AUDIO_INPUT_ARGS=( -f alsa -i "$AUDIO_DEVICE" )
fi

# ffmpeg drawtext reads 'textfile' and can reload with 'reload=1'
if echo "$OUT_URL" | grep -qE '^rtsp://'; then
  echo "Detected RTSP output; streaming to RTSP server: $OUT_URL"
  ffmpeg -hide_banner -loglevel info \
    -f lavfi -i color=size=${WIDTH}x${HEIGHT}:rate=${FPS}:color=black \
    ${AUDIO_INPUT_ARGS[@]} \
    -vf "drawtext=fontfile=${FONT}:fontsize=24:fontcolor=white:x=10:y=10:textfile=${LABEL_FILE}:reload=1" \
    -c:v libx264 -preset veryfast -tune zerolatency -pix_fmt yuv420p \
    -c:a aac -b:a 64k -f rtsp -rtsp_transport tcp "$OUT_URL"
else
  ffmpeg -hide_banner -loglevel info \
    -f lavfi -i color=size=${WIDTH}x${HEIGHT}:rate=${FPS}:color=black \
    ${AUDIO_INPUT_ARGS[@]} \
    -vf "drawtext=fontfile=${FONT}:fontsize=24:fontcolor=white:x=10:y=10:textfile=${LABEL_FILE}:reload=1" \
    -c:v libx264 -preset veryfast -tune zerolatency -pix_fmt yuv420p \
    -c:a aac -b:a 64k -f mpegts "$OUT_URL"
fi
