#!/usr/bin/env bash
set -euo pipefail

# Interactive helper to map serial devices to logical roles and write /etc/c2/devices.conf
CONFIG=/etc/c2/devices.conf

if [ $(id -u) -ne 0 ]; then
  echo "This script needs to be run as root (or via sudo)." >&2
  exit 1
fi

mkdir -p /etc/c2

function list_devices() {
  echo
  echo "Available serial devices (by-id):"
  if ls -1 /dev/serial/by-id >/dev/null 2>&1; then
    ls -1 /dev/serial/by-id | nl -w2 -s': '
  else
    echo "  (no /dev/serial/by-id entries found)"
  fi
  echo
}

echo "This helper lets you map physical serial devices to logical roles."
echo "Examples of roles: rig, sdr, gps, radio"

while true; do
  list_devices
  read -rp "Enter role name to configure (empty to finish): " role
  if [ -z "$role" ]; then
    break
  fi
  read -rp "Enter the device number from the list (or full path like /dev/ttyUSB0): " sel
  if [[ "$sel" =~ ^[0-9]+$ ]]; then
    devname=$(ls -1 /dev/serial/by-id | sed -n "${sel}p")
    if [ -z "$devname" ]; then
      echo "Invalid selection." >&2
      continue
    fi
    path="/dev/serial/by-id/$devname"
  else
    path="$sel"
  fi
  echo "Mapping $role -> $path"
  mkdir -p /etc/c2
  # preserve existing entries except this role
  awk -v role="$role" -F= '$1!=role {print $0}' "$CONFIG" 2>/dev/null > /tmp/devices.conf.tmp || true
  echo "$role=$path" >> /tmp/devices.conf.tmp
  mv /tmp/devices.conf.tmp "$CONFIG"
  chmod 644 "$CONFIG"
  echo "Wrote $CONFIG"
done

echo "Done. Current mappings:"
cat "$CONFIG" || true

echo "You can reference these paths in Docker mappings, e.g. --device=$(sed -n 's/^rig=//p' $CONFIG):/dev/ttyUSB0"
