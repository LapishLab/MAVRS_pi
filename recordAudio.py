#! /bin/python
import os
# These must be set BEFORE importing sounddevice to bypass PipeWire
os.environ["PA_ALSA_PLUGHW"] = "1"
os.environ["PA_ALSA_HOSTAPI"] = "ALSA"

from multiprocessing.synchronize import Event
from utilities import get_stop_event
import time
from sounddevice import InputStream
import numpy as np
from typing import Protocol, Optional
import config

# --- Hardware Configuration ---
SAMPLE_RATE: int = 250000
CHANNELS: int = 1
BLOCK_SIZE: int = 4096     # 16.38ms chunks at 250kHz
DEVICE_INDEX: str = 'hw:3,0'

from audioWriter import AudioWriter


class PortAudioTimeInfo(Protocol):
    inputBufferAdcTime: float
    outputBufferDacTime: float
    currentTime: float


def main(save_dir: Optional[str] = None, ready_event: Optional[Event] = None) -> None:
    if save_dir is None:
        save_dir = str(config.default_data_path())
    writer = AudioWriter(str(save_dir))

    stop_event = get_stop_event()
    print(f"Initializing PortAudio device #{DEVICE_INDEX} at {SAMPLE_RATE} Hz...")

    writer_add = writer.add
    def audio_callback(data: np.ndarray, frames: int, t: PortAudioTimeInfo, status) -> None:
        now_ns: int = time.time_ns()
        mic_latency_ns: int = int((t.currentTime - t.inputBufferAdcTime) * 1e9)
        sample_ns: int = now_ns - mic_latency_ns
        writer_add(sample_ns, frames, data)
        if status:
            print(f"PortAudio Status Flag: {status}", flush=True)

    stream = InputStream(
        device=DEVICE_INDEX,
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
