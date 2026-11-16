# Agent guidance for MAVRS_pi

## Purpose and architecture

This repository runs on Raspberry Pi 4 recorders controlled by the sibling `MAVRS_server` repository. The server starts `startExperiment.py` over SSH through a user systemd unit and passes a shared session name. The Pi records enabled video, audio, and GPIO modalities in separate processes under `data/<session>/<hostname>/`; the server later collects the files with rsync. Check the server side when changing this interface or the recording layout.

## Working preferences

- Write clean, readable code with clear names and straightforward control flow. Keep changes small and focused on the requested behavior.
- The user reviews all changes and personally performs all git commits. Leave changes uncommitted and describe their scope clearly.
- Keep core recording and configuration functionality runnable from the command line. Any GUI should call the same underlying functions rather than duplicate recording logic.
- If the user asks why code was written a certain way, discuss the reasoning and tradeoffs. Do not treat that question alone as a request to change code.
- Mention unrelated concerns found during review separately so they can be considered for a separate commit. Do not fold them into the current change without a reason tied to the request.

## Recording and timing requirements

- GPIO event timestamps are used to synchronize Pi recordings with behavioral control computers, electrophysiology, fiber photometry, and ultrasonic audio playback. They need to align closely with audio and video timestamps, including timestamps embedded in filenames.
- Treat timestamp origin, clock source, timezone, precision, and the point in the capture pipeline being timestamped as part of the data format. When changing any of them, trace the effect across `recordInput.py`, `recordAudio.py`, `audioWriter.py`, `recordVideo.py`, and `utilities.py`. Preserve a consistent time reference and document any offset or uncertainty rather than assuming file creation time equals capture time.
- Keep recording workers responsive to stop signals so files are finalized before the server transfers them. Preserve the session/hostname directory structure expected by `MAVRS_server`.
- Be careful with real-time capture paths: avoid blocking audio callbacks or video encoding on optional output such as logging or live streaming.
