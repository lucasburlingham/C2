#!/usr/bin/env bash
set -euo pipefail

# setup_venv.sh
# Create a Python virtualenv and install backend dependencies.
# Usage: ./tools/setup_venv.sh [--path /opt/c2/venv] [--python python3]

VENV_PATH=".venv"
PYTHON_BIN="python3"

print_help() {
  cat <<EOF
Usage: $0 [--path /path/to/venv] [--python python3]

Creates a virtualenv and installs requirements from backend/requirements.txt.
Default venv path is .venv (repo root).
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --path) VENV_PATH="$2"; shift 2;;
    --python) PYTHON_BIN="$2"; shift 2;;
    -h|--help) print_help; exit 0;;
    *) echo "Unknown arg: $1"; print_help; exit 2;;
  esac
done

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python binary '$PYTHON_BIN' not found in PATH" >&2
  exit 1
fi

REQ_FILE="$(dirname "$0")/../backend/requirements.txt"
if [ ! -f "$REQ_FILE" ]; then
  echo "Requirements file not found: $REQ_FILE" >&2
  exit 1
fi

echo "Creating venv at $VENV_PATH using $PYTHON_BIN"
$PYTHON_BIN -m venv "$VENV_PATH"
source "$VENV_PATH/bin/activate"
pip install --upgrade pip
pip install -r "$REQ_FILE"
deactivate

echo "Virtualenv created at $VENV_PATH and dependencies installed. Activate with: source $VENV_PATH/bin/activate"
