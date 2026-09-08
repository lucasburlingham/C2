
#!/usr/bin/env bash
set -euo pipefail
# gst_atak_overlay.sh
# Looping GStreamer launcher that reads the frequency file each iteration and streams short clips with the current text overlay.

STREAM_ID="sdr1"
OUT_HOST="127.0.0.1"
OUT_PORT="5004"
FPS=15
WIDTH=500
HEIGHT=400
FONT="Sans 24"

if [ $# -gt 0 ]; then
	STREAM_ID="$1"
fi

LABEL_FILE="$(dirname "$(realpath "$0")")/../backend/tmp/${STREAM_ID}.label.txt"

if [ ! -f "$LABEL_FILE" ]; then
	mkdir -p "$(dirname "$LABEL_FILE")"
	echo "" > "$LABEL_FILE"
fi

echo "Starting looping gst pipeline for stream $STREAM_ID -> udp://$OUT_HOST:$OUT_PORT"

while true; do
	LABEL_TEXT=$(cat "$LABEL_FILE" 2>/dev/null || echo "")
	# create a short clip of 1 second (FPS frames) with the current overlay and send it
	gst-launch-1.0 -q videotestsrc pattern=black num-buffers=$FPS ! video/x-raw,width=$WIDTH,height=$HEIGHT,framerate=${FPS}/1 \
		! textoverlay text="$LABEL_TEXT" valignment=top halignment=left font-desc="$FONT" ! x264enc tune=zerolatency bitrate=500 speed-preset=superfast \
		! mpegtsmux ! udpsink host=$OUT_HOST port=$OUT_PORT sync=false
	sleep 0.1
done

