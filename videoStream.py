"""Serve the recorded H.264 video to one VLC client over TCP."""

from __future__ import annotations

from multiprocessing.queues import Queue
from multiprocessing.synchronize import Event
from queue import Empty
import signal
import socket
import subprocess

import prctl


def serve_video(frames: Queue[tuple[bytes, bool]], client_connected: Event,
                stop_event: Event, port: int) -> None:
    """Accept one client at a time; all blocking network work stays in this process."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("0.0.0.0", port))
        server.listen(1)
        server.settimeout(0.5)
        print(f"Video stream listening on TCP port {port}")

        while not stop_event.is_set():
            try:
                connection, _ = server.accept()
            except socket.timeout:
                continue

            with connection:
                # FFmpeg remuxes H.264 to MPEG-TS and writes directly to the socket.
                ffmpeg = subprocess.Popen(
                    ["ffmpeg", "-loglevel", "warning", "-use_wallclock_as_timestamps", "1",
                     "-f", "h264", "-i", "pipe:0", "-c:v", "copy", "-f", "mpegts", "pipe:1"],
                    stdin=subprocess.PIPE,
                    stdout=connection,
                    preexec_fn=lambda: prctl.set_pdeathsig(signal.SIGKILL),
                )
                client_connected.set()
                waiting_for_keyframe = True
                try:
                    while not stop_event.is_set() and ffmpeg.poll() is None:
                        try:
                            frame, keyframe = frames.get(timeout=0.5)
                        except Empty:
                            continue
                        if waiting_for_keyframe:
                            if not keyframe:
                                continue
                            waiting_for_keyframe = False
                        ffmpeg.stdin.write(frame)
                        ffmpeg.stdin.flush()
                except (BrokenPipeError, OSError):
                    pass  # A disconnected or stalled viewer must not affect recording.
                finally:
                    client_connected.clear()
                    try:
                        ffmpeg.stdin.close()
                    except BrokenPipeError:
                        pass
                    if ffmpeg.poll() is None:
                        ffmpeg.terminate()
                    try:
                        ffmpeg.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        ffmpeg.kill()
                        ffmpeg.wait()
                    while True:
                        try:
                            frames.get_nowait()
                        except Empty:
                            break
