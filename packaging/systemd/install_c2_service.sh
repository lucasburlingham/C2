#!/usr/bin/env bash
set -euo pipefail

# install_c2_service.sh
# Installs the c2 service to systemd: copies files, creates user, sets permissions, enables service.
# Usage: sudo ./packaging/systemd/install_c2_service.sh [--prefix /opt/c2] [--user c2] [--no-enable]

PREFIX="/opt/c2"
USER_NAME="c2"
ENABLE=1
PYTHON_BIN="python3"

VENV_SUBPATH="venv"

print_help() {
  cat <<EOF
Usage: $0 [--prefix /opt/c2] [--user c2] [--no-enable]

Installs C2 service files to the system. Must be run as root.
Options:
  --prefix DIR    Installation root (default: /opt/c2)
  --user NAME     System user to run the service (default: c2)
  --no-enable     Do not enable/start the systemd service
  -h, --help      Show this help
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --prefix) PREFIX="$2"; shift 2;;
    --user) USER_NAME="$2"; shift 2;;
    --python) PYTHON_BIN="$2"; shift 2;;
    --venv) VENV_SUBPATH="$2"; shift 2;;
    --no-enable) ENABLE=0; shift 1;;
    -h|--help) print_help; exit 0;;
    *) echo "Unknown arg: $1"; print_help; exit 2;;
  esac
done

if [ "$EUID" -ne 0 ]; then
  echo "This installer must be run as root. Use sudo." >&2
  exit 1
fi

echo "Installing C2 to prefix: $PREFIX"

# create installation directory
mkdir -p "$PREFIX"

# copy repository files (exclude .git)
if command -v rsync >/dev/null 2>&1; then
  rsync -a --exclude='.git' --exclude='venv' ./ "$PREFIX/"
else
  # fallback to cp
  cp -a . "$PREFIX/tmp_install_src" || true
  # move contents out of tmp to prefix without preserving top-level dot
  (cd "$PREFIX/tmp_install_src" && cp -a . "$PREFIX/" )
  rm -rf "$PREFIX/tmp_install_src"
fi

# ensure runner is executable
if [ -f "$PREFIX/tools/c2_service_runner.sh" ]; then
  chmod +x "$PREFIX/tools/c2_service_runner.sh"
fi

# create virtualenv and install backend requirements
VENV_PATH="$PREFIX/$VENV_SUBPATH"
REQ_FILE="$PREFIX/backend/requirements.txt"
if command -v "$PYTHON_BIN" >/dev/null 2>&1 && [ -f "$REQ_FILE" ]; then
  echo "Creating virtualenv at $VENV_PATH using $PYTHON_BIN"
  "$PYTHON_BIN" -m venv "$VENV_PATH"
  # install requirements
  if [ -x "$VENV_PATH/bin/pip" ]; then
    "$VENV_PATH/bin/pip" install --upgrade pip
    "$VENV_PATH/bin/pip" install -r "$REQ_FILE"
  fi
else
  echo "Warning: Python binary $PYTHON_BIN not found or requirements file missing; skipping venv creation"
fi

# create system user if needed
if id -u "$USER_NAME" >/dev/null 2>&1; then
  echo "User $USER_NAME already exists"
else
  if command -v useradd >/dev/null 2>&1; then
    echo "Creating system user $USER_NAME with home at $PREFIX"
    # create system user with the install prefix as home so service can use WorkingDirectory
    useradd --system --home-dir "$PREFIX" --create-home --shell /usr/sbin/nologin --user-group "$USER_NAME" || \
      useradd -r -d "$PREFIX" -s /sbin/nologin "$USER_NAME" || true
  else
    echo "useradd not found; skipping user creation" >&2
  fi
fi

# create logdir
mkdir -p /var/log/c2
chown "$USER_NAME":"$USER_NAME" /var/log/c2 || true
chmod 755 /var/log/c2 || true

# ensure venv ownership (if created)
if [ -d "$VENV_PATH" ]; then
  chown -R "$USER_NAME":"$USER_NAME" "$VENV_PATH" || true
fi

# install systemd unit (replace C2_ROOT env line with actual prefix)
UNIT_SRC="packaging/systemd/c2.service"
UNIT_DST="/etc/systemd/system/c2.service"
if [ -f "$UNIT_SRC" ]; then
  echo "Installing systemd unit to $UNIT_DST"
  sed "s|Environment=C2_ROOT=/opt/c2|Environment=C2_ROOT=${PREFIX}|g" "$UNIT_SRC" > /tmp/c2.service
  mv /tmp/c2.service "$UNIT_DST"
  chmod 644 "$UNIT_DST"
fi

# set ownership of installed files
chown -R "$USER_NAME":"$USER_NAME" "$PREFIX" || true

# reload systemd and enable/start service
if command -v systemctl >/dev/null 2>&1 && [ $ENABLE -eq 1 ]; then
  systemctl daemon-reload
  systemctl enable --now c2.service
  echo "Enabled and started c2.service"
  systemctl status --no-pager c2.service || true
else
  echo "Systemctl not available or --no-enable specified; unit installed but not started. To start: systemctl enable --now c2.service"
fi

echo "Installation complete. Logs: /var/log/c2/" 
