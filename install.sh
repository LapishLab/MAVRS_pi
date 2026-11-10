#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "$(realpath -- "$0")")"

if [[ "$(uname -s)" != Linux || "$(dpkg --print-architecture)" != arm64 ]]; then
    echo "This installer requires 64-bit Raspberry Pi OS (arm64)." >&2
    exit 1
fi

if [[ ! -x /usr/bin/python3 ]]; then
    echo "Raspberry Pi OS system Python (/usr/bin/python3) is missing." >&2
    exit 1
fi

uv_bin=$(command -v uv || true)
if [[ -z "$uv_bin" && -x "$HOME/.local/bin/uv" ]]; then
    uv_bin="$HOME/.local/bin/uv"
fi

# Keep packages that provide native Pi bindings and the NumPy used by Picamera2
# under apt's control. uv installs the remaining project dependencies in .venv.
apt_packages=(python3-picamera2 python3-libcamera python3-prctl python3-numpy libportaudio2 ffmpeg v4l-utils)
if [[ -z "$uv_bin" ]]; then
    apt_packages+=(ca-certificates)
fi
if [[ -z "$uv_bin" ]] && ! command -v curl >/dev/null 2>&1; then
    apt_packages+=(curl)
fi

missing_packages=()
for package in "${apt_packages[@]}"; do
    if [[ "$(dpkg-query -W -f='${Status}' "$package" 2>/dev/null || true)" != "install ok installed" ]]; then
        missing_packages+=("$package")
    fi
done

if (( ${#missing_packages[@]} )); then
    echo "Installing OS packages: ${missing_packages[*]}"
    sudo apt-get update
    sudo apt-get install -y "${missing_packages[@]}"
fi

if [[ -z "$uv_bin" ]]; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | env UV_NO_MODIFY_PATH=1 sh
    uv_bin="$HOME/.local/bin/uv"
    if [[ ! -x "$uv_bin" ]]; then
        echo "uv installer did not create $uv_bin" >&2
        exit 1
    fi
fi

if [[ -L .venv ]]; then
    echo ".venv is a symlink; remove it manually before running this installer." >&2
    exit 1
fi

venv_is_usable=false
if [[ -x .venv/bin/python3 && -f .venv/pyvenv.cfg ]] && \
   grep -Eiq '^include-system-site-packages[[:space:]]*=[[:space:]]*true[[:space:]]*$' .venv/pyvenv.cfg && \
   .venv/bin/python3 -c 'import os, sys; assert sys.prefix != sys.base_prefix and os.path.samefile(sys._base_executable, "/usr/bin/python3")' 2>/dev/null; then
    venv_is_usable=true
fi

if [[ "$venv_is_usable" != true ]]; then
    echo "Creating .venv with Raspberry Pi OS Python and system packages..."
    "$uv_bin" venv --clear --python /usr/bin/python3 --no-python-downloads --system-site-packages .venv
fi

"$uv_bin" sync --locked --python /usr/bin/python3 --no-python-downloads --no-install-package numpy

.venv/bin/python3 -c 'import gpiozero, libcamera, numpy, picamera2, prctl, sounddevice, soundfile, yaml'
echo "Ready. Run: .venv/bin/python3 startExperiment.py"
