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

The installer disables NTP before installing packages, since the central server
sets the Pi clock before recordings. If disabling NTP fails, installation stops.
This does not depend on htpdate.

The optional Pi setup steps live in `setup/optional/`. If Conky, the panel
clock, htpdate, or PipeWire setup fails, the installer reports a warning and
continues with the recorder installation. You can rerun `bash install.sh` after
fixing the cause, or run one of those scripts on its own.

When successful, the optional PipeWire step sets its default rate to 48 kHz and
permits 8, 16, 32, 48, 96, 192, 250, and 384 kHz when PipeWire is installed.
It writes a drop-in under `/etc/pipewire/pipewire.conf.d/`, which takes effect
when PipeWire next starts. The optional htpdate step disables its continuous
service and enables a one-shot time update after the network comes online at
each boot. Reboot after setup succeeds to apply the startup settings.

Run the installer as the same Pi account used by the central server, without
prefixing the script with `sudo`. It grants that account passwordless access to
`sudo timedatectl` in `/etc/sudoers.d/timedatectl`, so the server can set the
Pi clock without an interactive password prompt.

The optional Conky step installs it and configures a desktop overlay with the Pi
name, network addresses, CPU, RAM, and swap usage. It starts at the next
graphical login. Edit `~/.config/conky/conky.conf` to change the display; run
`conky --daemonize` from a desktop terminal to start it now, or `killall conky`
to stop it.

The optional panel step sets the desktop clock to `yy-mm-dd HH:MM:SS`. It edits
the existing `wf-panel-pi.ini` for the current Pi OS layout, preserving other
panel settings. Restart the panel or log out and back in to see the new format.

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
