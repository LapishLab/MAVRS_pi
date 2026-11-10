# MAVRS_pi
 Modular audio and video recording system for rat behavior. Code for Raspberry Pi.

## Install on a Raspberry Pi

On 64-bit Raspberry Pi OS Bookworm or Trixie, clone this repository and run:

```sh
cd MAVRS_pi
bash install.sh
```

Run `bash install.sh` again after each `git pull`. The script installs missing OS
packages and uv, creates `.venv` from `/usr/bin/python3` with access to system
packages, then runs `uv sync` against the checked-in lockfile. Picamera2,
libcamera, python-prctl, and NumPy come from Raspberry Pi OS; the other Python
dependencies come from uv. An existing `.venv` made with a different interpreter
or without system packages is recreated.

Run the recorder with `.venv/bin/python3 startExperiment.py`. The central server
already uses this path when starting a recording on a Pi.

## Live video

Add the following to `~/mavrs_pi_config.yaml` to serve video while an experiment is recording:

```yaml
streaming:
  enable: true
  port: 9000
  queue_size: 16
```

Open `tcp://<pi-address>:9000` in VLC. Only one viewer is supported at a time; the stream contains video only. A slow or disconnected viewer can lose stream frames without stopping the MP4 recording. Allow the chosen TCP port through the Pi's firewall if one is enabled.
