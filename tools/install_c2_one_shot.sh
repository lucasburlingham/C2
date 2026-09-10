#!/usr/bin/env bash
set -euo pipefail

# One-shot installer for Vehicle C2 (Docker Compose)
# Usage:
#   sudo ./tools/install_c2_one_shot.sh [repo-dir|git-url]
# If run without args, assumes current directory is the repo root (contains backend/).

REPO_ARG=${1:-}

function err() { echo "ERROR: $*" >&2; exit 1; }

# Resolve repo dir
if [ -n "$REPO_ARG" ]; then
  if [[ "$REPO_ARG" =~ ^https?:// ]] || [[ "$REPO_ARG" =~ ^git@ ]]; then
    TARGET_DIR="/opt/c2"
    echo "Cloning repo to $TARGET_DIR..."
    rm -rf "$TARGET_DIR"
    git clone --depth=1 "$REPO_ARG" "$TARGET_DIR"
    REPO_DIR="$TARGET_DIR"
  else
    REPO_DIR="$REPO_ARG"
  fi
else
  REPO_DIR="$(pwd)"
fi

cd "$REPO_DIR"

if [ ! -d backend ]; then
  err "backend/ not found in $REPO_DIR — run from repo root or pass a git URL" 
fi

# Debian/Ubuntu install helper
if command -v apt-get >/dev/null 2>&1; then
  PKG_INSTALL="sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin git"
  echo "Installing prerequisites via apt..."
  sudo apt-get update
  sudo apt-get install -y docker.io docker-compose-plugin git
else
  echo "No apt-get detected. Ensure Docker and docker compose are installed on this host." 
fi

# Ensure docker service is running
if ! systemctl is-active --quiet docker; then
  echo "Starting docker service..."
  sudo systemctl enable --now docker
fi

# Add current user to docker group if not root
if [ "$EUID" -ne 0 ]; then
  if ! groups "$USER" | grep -qw docker; then
    echo "Adding $USER to docker group (you'll need to re-login for group to take effect)"
    sudo usermod -aG docker "$USER" || true
  fi
fi

# Prepare env file
ENV_EXAMPLE=systemd/vehicle-c2.env.example
ENV_TARGET=systemd/vehicle-c2.env
if [ -f "$ENV_EXAMPLE" ]; then
  echo "Copying $ENV_EXAMPLE -> $ENV_TARGET"
  cp "$ENV_EXAMPLE" "$ENV_TARGET"
else
  echo "Warning: $ENV_EXAMPLE not found; creating minimal env file"
  cat > "$ENV_TARGET" <<EOF
RIG_MODEL=2
RIG_DEVICE=/dev/ttyUSB0
RIGCTLD_PORT=4532
GPSD_DEVICE=/dev/ttyUSB1
GPSD_PORT=2947
RIGCTLD_HOST=127.0.0.1
GPSD_HOST=127.0.0.1
EOF
fi

# Try to auto-detect common serial devices
if [ -e /dev/ttyUSB0 ] && grep -q "RIG_DEVICE" "$ENV_TARGET" >/dev/null 2>&1; then
  sed -i "s@RIG_DEVICE=.*@RIG_DEVICE=/dev/ttyUSB0@" "$ENV_TARGET" || true
fi
if [ -e /dev/ttyUSB1 ] && grep -q "GPSD_DEVICE" "$ENV_TARGET" >/dev/null 2>&1; then
  sed -i "s@GPSD_DEVICE=.*@GPSD_DEVICE=/dev/ttyUSB1@" "$ENV_TARGET" || true
fi

# Inform user they should review env file
echo "Environment file written to $REPO_DIR/$ENV_TARGET — edit if device paths differ."

# Install packaged udev rule for RTL-SDR symlinks if present
UDEV_RULE_SRC="packaging/udev/99-vehicle-c2-rtlsdr.rules"
if [ -f "$UDEV_RULE_SRC" ]; then
  echo "Installing udev rule for RTL-SDR devices from $UDEV_RULE_SRC"
  sudo cp "$UDEV_RULE_SRC" /etc/udev/rules.d/ || true
  sudo udevadm control --reload-rules || true
  sudo udevadm trigger || true
  echo "udev rules reloaded. You should now see /dev/rtlsdr-* symlinks for attached RTL-SDR devices."
fi

# Load ALSA loopback module on the host so containers can use `hw:Loopback`.
echo "Loading snd-aloop kernel module (requires sudo)..."
if sudo modprobe snd-aloop 2>/dev/null; then
  echo "snd-aloop loaded."
else
  echo "Warning: failed to modprobe snd-aloop (you may need to run this manually as root)."
fi

# Ensure docker-compose maps host ALSA devices into the backend container
DC_FILE="docker-compose.yml"
if [ -f "$DC_FILE" ]; then
  if ! grep -q '/dev/snd:/dev/snd' "$DC_FILE" >/dev/null 2>&1; then
    echo "Adding /dev/snd mapping to $DC_FILE"
    awk '\
    BEGIN{added=0} \
    {print} \
    /^[[:space:]]*devices:[[:space:]]*$/ && added==0 { \
      print "      - \"/dev/snd:/dev/snd\" # added by installer (ALSA devices)"; added=1; next }' "$DC_FILE" > "$DC_FILE.tmp" && mv "$DC_FILE.tmp" "$DC_FILE"
  else
    echo "$DC_FILE already maps /dev/snd"
  fi
fi

# Ensure docker-compose.yml exists
if [ ! -f docker-compose.yml ]; then
  err "docker-compose.yml not found in repo root"
fi

# Start containers
echo "Building and starting containers (this may take a few minutes)..."
# Use sudo when necessary
if [ "$EUID" -eq 0 ]; then
  docker compose up -d --build
else
  sudo docker compose up -d --build
fi

echo "If SDR devices are present, consider verifying them inside the backend container with:"
echo "  sudo docker compose exec backend rtl_test -t"

echo "Done: containers started. Backend should be reachable on port 8000."

cat <<EOF
Next steps:
- Edit $ENV_TARGET if device nodes or RIG_MODEL need adjusting.
- Check logs: sudo docker compose logs -f backend
- To rebuild after code changes: sudo docker compose up -d --build
- To enable a systemd unit (optional), copy packaging/systemd/c2.service to /etc/systemd/system and ensure /opt/c2/tools/c2_service_runner.sh exists.
EOF
