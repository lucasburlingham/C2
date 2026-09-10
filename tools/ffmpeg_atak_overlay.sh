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
INPUT_FORMAT=""
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
    --input-format) INPUT_FORMAT="$2"; shift 2;;
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

# ensure label file exists so drawtext has something to read
if [ ! -f "$LABEL_FILE" ]; then
  mkdir -p "$(dirname "$LABEL_FILE")"
  echo "no-freq" > "$LABEL_FILE"
fi

echo "Streaming video $WIDTH x $HEIGHT with label overlay from $LABEL_FILE to $OUT_URL"

# prepare audio input args depending on scheme
# special handling for rtl_fm: if AUDIO_DEVICE starts with 'rtl_fm' then
# spawn rtl_fm demodulator piped into ffmpeg stdin.
if echo "$AUDIO_DEVICE" | grep -qE '^rtl_fm'; then
  # parse optional params after colon, e.g. rtl_fm:mode=fm,rate=22050,gain=0
  PARAMS=""
  if echo "$AUDIO_DEVICE" | grep -q ':'; then
    PARAMS="$(echo "$AUDIO_DEVICE" | cut -d: -f2-)"
  fi
  MODE="fm"
  RATE=22050
  GAIN=0
  if [ -n "$PARAMS" ]; then
    IFS=','; for p in $PARAMS; do
      k=$(echo "$p" | cut -d= -f1)
      v=$(echo "$p" | cut -d= -f2-)
      case "$k" in
        mode) MODE="$v";;
        rate) RATE="$v";;
        gain) GAIN="$v";;
      esac
    done
    unset IFS
  fi
  # read numeric frequency from freq file (in Hz), fallback to 14285000
  FREQ_VAL="$(grep -oE '[0-9]+(\.[0-9]+)?' "$FREQ_FILE" | head -n1 || true)"
  if [ -z "$FREQ_VAL" ]; then
    FREQ_VAL=14285000
  fi
  echo "Using rtl_fm: freq=$FREQ_VAL mode=$MODE rate=$RATE gain=$GAIN"
  # set AUDIO_INPUT_ARGS to read from stdin
  AUDIO_INPUT_ARGS=( -f s16le -ar "$RATE" -ac 1 -i - )
  # build RTL_FM command prefix to pipe into ffmpeg
  RTL_CMD=( rtl_fm -f "$FREQ_VAL" -M "$MODE" -s "$RATE" -g "$GAIN" - )

else
  if echo "$AUDIO_DEVICE" | grep -qE '^(tcp|udp|http|https)://'; then
    # network input: allow forcing an input format (e.g., mpegts, s16le, webm)
    if [ -n "$INPUT_FORMAT" ]; then
      AUDIO_INPUT_ARGS=( -f "$INPUT_FORMAT" -i "$AUDIO_DEVICE" )
    else
      AUDIO_INPUT_ARGS=( -i "$AUDIO_DEVICE" )
    fi
  else
    # default to ALSA capture
    AUDIO_INPUT_ARGS=( -f alsa -i "$AUDIO_DEVICE" )
  fi
fi

# ffmpeg drawtext reads 'textfile' and can reload with 'reload=1'
if echo "$OUT_URL" | grep -qE '^rtsp://'; then
  echo "Detected RTSP output; streaming to RTSP server: $OUT_URL"
  if [ "${RTL_CMD+x}" = "" ]; then
    ffmpeg -hide_banner -loglevel info \
      -f lavfi -i color=size=${WIDTH}x${HEIGHT}:rate=${FPS}:color=black \
      ${AUDIO_INPUT_ARGS[@]} \
      -vf "drawtext=fontfile=${FONT}:fontsize=24:fontcolor=white:x=10:y=10:textfile=${LABEL_FILE}:reload=1" \
      -c:v libx264 -preset veryfast -tune zerolatency -pix_fmt yuv420p \
      -c:a aac -b:a 64k -f rtsp -rtsp_transport tcp "$OUT_URL"
  else
    # pipe rtl_fm into ffmpeg stdin
    "${RTL_CMD[@]}" | ffmpeg -hide_banner -loglevel info \
      -f lavfi -i color=size=${WIDTH}x${HEIGHT}:rate=${FPS}:color=black \
      ${AUDIO_INPUT_ARGS[@]} \
      -vf "drawtext=fontfile=${FONT}:fontsize=24:fontcolor=white:x=10:y=10:textfile=${LABEL_FILE}:reload=1" \
      -c:v libx264 -preset veryfast -tune zerolatency -pix_fmt yuv420p \
      -c:a aac -b:a 64k -f rtsp -rtsp_transport tcp "$OUT_URL"
  fi
else
  if [ "${RTL_CMD+x}" = "" ]; then
    ffmpeg -hide_banner -loglevel info \
      -f lavfi -i color=size=${WIDTH}x${HEIGHT}:rate=${FPS}:color=black \
      ${AUDIO_INPUT_ARGS[@]} \
      -vf "drawtext=fontfile=${FONT}:fontsize=24:fontcolor=white:x=10:y=10:textfile=${LABEL_FILE}:reload=1" \
      -c:v libx264 -preset veryfast -tune zerolatency -pix_fmt yuv420p \
      -c:a aac -b:a 64k -f mpegts "$OUT_URL"
  else
    # pipe rtl_fm into ffmpeg stdin
    "${RTL_CMD[@]}" | ffmpeg -hide_banner -loglevel info \
      -f lavfi -i color=size=${WIDTH}x${HEIGHT}:rate=${FPS}:color=black \
      ${AUDIO_INPUT_ARGS[@]} \
      -vf "drawtext=fontfile=${FONT}:fontsize=24:fontcolor=white:x=10:y=10:textfile=${LABEL_FILE}:reload=1" \
      -c:v libx264 -preset veryfast -tune zerolatency -pix_fmt yuv420p \
      -c:a aac -b:a 64k -f mpegts "$OUT_URL"
  fi
fi
