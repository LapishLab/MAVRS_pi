#! /bin/python
import os
# These must be set BEFORE importing sounddevice to bypass PipeWire
os.environ["PA_ALSA_PLUGHW"] = "1"
os.environ["PA_ALSA_HOSTAPI"] = "ALSA"

from multiprocessing.synchronize import Event
from utilities import get_stop_event
import time
from sounddevice import InputStream, query_devices
import numpy as np
from typing import Protocol, Optional
import config
from pathlib import Path

# --- Hardware Configuration ---
SAMPLE_RATE: int = 250000
CHANNELS: int = 1
BLOCK_SIZE: int = 16384    # 65.54ms chunks at 250kHz
DEVICE_NAME: str = '384kHz AudioMoth USB Microphone'

from audioWriter import AudioWriter


def find_device_index() -> int:
    """Return the PortAudio index for the AudioMoth USB microphone."""
    for index, device in enumerate(query_devices()):
        if device['name'].startswith(DEVICE_NAME) and device['max_input_channels'] > 0:
            return index

    raise RuntimeError(f'Audio input device not found: {DEVICE_NAME}')


class PortAudioTimeInfo(Protocol):
    inputBufferAdcTime: float
    outputBufferDacTime: float
    currentTime: float


def main(save_dir: Optional[Path | str] = None, ready_event: Optional[Event] = None) -> None:
    device_index = find_device_index()

    if save_dir is None:
        save_dir = config.default_data_path()
        save_dir.mkdir(parents=True, exist_ok=True)

    writer = AudioWriter(str(save_dir))

    stop_event = get_stop_event()
    print(f"Initializing PortAudio device #{device_index} at {SAMPLE_RATE} Hz...")

    writer_add = writer.add
    writer_log_warning = writer.log_warning

    def audio_callback(data: np.ndarray, frames: int, t: PortAudioTimeInfo, status) -> None:
        now_ns: int = time.time_ns()
        mic_latency_ns: int = int((t.currentTime - t.inputBufferAdcTime) * 1e9)
        sample_ns: int = now_ns - mic_latency_ns
        writer_add(sample_ns, frames, data)
        if status:
            writer_log_warning(f"PortAudio: {status}")

    stream = InputStream(
        device=device_index,
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        blocksize=BLOCK_SIZE,
        latency='high',
        dtype='int16',
        callback=audio_callback
    )

    try:
        with stream:
            if ready_event is not None:
                ready_event.set()
            stop_event.wait()
    finally:
        writer.stop()


if __name__ == '__main__':
    main()
