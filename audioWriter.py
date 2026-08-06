#! /bin/python
import os
# These must be set BEFORE importing sounddevice to bypass PipeWire
os.environ["PA_ALSA_PLUGHW"] = "1"
os.environ["PA_ALSA_HOSTAPI"] = "ALSA"

from utilities import get_filename
from soundfile import SoundFile
import numpy as np
from typing import Optional
import threading
import h5py
from datetime import datetime

# --- Hardware Configuration ---
SAMPLE_RATE: int = 250000
CHANNELS: int = 1
BLOCK_SIZE: int = 16384     # 16.38ms chunks at 250kHz

class AudioPacket:
    """Preallocated container for one audio block."""
    __slots__ = ("system_time_ns", "n_samples", "data")

    def __init__(self, block_size: int):
        self.system_time_ns = -1
        self.n_samples = -1
        self.data = np.zeros(block_size, dtype=np.int16)

    def set(self, system_time_ns: int, n_samples: int, data: np.ndarray) -> None:
        self.system_time_ns = system_time_ns
        self.n_samples = n_samples

        samples = np.asarray(data, dtype=np.int16).reshape(-1)
        copy_length = min(n_samples, samples.size)
        self.data[:copy_length] = samples[:copy_length]


class AudioWriter(threading.Thread):
    """Writer to handle audio data and timestamps, writing to WAV and CSV metadata files."""
    def __init__(self, save_dir: str):
        super().__init__(daemon=True)

        # Initialize WAV and .csv files with temporary names; will rename later based on first packet timestamp
        self.save_dir = save_dir
        self.wav_filename = save_dir + "/temp.wav"
        self.wav_file: SoundFile = SoundFile(
            self.wav_filename,
            mode='x',
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            subtype='PCM_16'
        )

        self._metadata_file_path = save_dir + "/temp.csv"
        self._metadata_file = open(self._metadata_file_path, "w", newline='')
        self._metadata_file.write('sample,file_us\n')
        self._current_sample = 0

        # Preallocate a ring buffer of audio packets to avoid memory allocation during real-time audio capture
        self.n_slots = 50
        self.write_idx = 0
        self.read_idx = 0
        self.buffer = [AudioPacket(BLOCK_SIZE) for _ in range(self.n_slots)]

        # Threading events to manage stopping and signaling when new data is available
        self._stop_event = threading.Event()
        self._data_available = threading.Condition()

        # File start time in nanoseconds, set when the first audio packet is added
        self._file_start_ns: Optional[int] = None

        self._warning_log_path = os.path.join(save_dir, 'audio_writer.log')
        self._warning_file = open(self._warning_log_path, 'a', encoding='utf-8')
        self._warning_lock = threading.Lock()

        self.start()

    def run(self) -> None:
        while self._file_start_ns is None:
            with self._data_available:
                self._data_available.wait(timeout=0.02)

        self._rename_output_files(self._file_start_ns)

        while not self._stop_event.is_set():
            with self._data_available:
                while self.read_idx >= self.write_idx and not self._stop_event.is_set():
                    self._data_available.wait(timeout=0.5)
                if self.read_idx >= self.write_idx and self._stop_event.is_set():
                    break
                packet = self.buffer[self.read_idx % self.n_slots]
                self.read_idx += 1
            self.wav_file.write(packet.data[:packet.n_samples])
            elapsed_us = int((packet.system_time_ns - self._file_start_ns) / 1000)
            self._metadata_file.write(str(self._current_sample) + "," + str(elapsed_us) + "\n")
            self._current_sample += packet.n_samples

    def add(self, system_time_ns: int, n_samples: int, data: np.ndarray) -> None:
        """Add a new audio packet to the writer buffer."""
        if self._file_start_ns is None:
            self._file_start_ns = system_time_ns

        with self._data_available:
            if self.write_idx - self.read_idx >= self.n_slots:
                self.log_warning("AudioWriter: buffer overflow")
                return
            slot = self.buffer[self.write_idx % self.n_slots]
            slot.set(system_time_ns, n_samples, data)
            self.write_idx += 1
            self._data_available.notify()

    def stop(self) -> None:
        self._stop_event.set()
        with self._data_available:
            self._data_available.notify_all()
        self.join(timeout=5.0)

        self.wav_file.flush()
        self.wav_file.close()

        self._metadata_file.close()
        self._warning_file.close()

    def log_warning(self, message: str) -> None:
        timestamp = datetime.now().isoformat()
        with self._warning_lock:
            self._warning_file.write(timestamp + ": " + message + "\n")

    def _rename_output_files(self, system_time_ns: int) -> None:
        wav_path = get_filename(save_dir=self.save_dir, subfolder='mic', extension='.wav', time_ns=system_time_ns)
        if os.path.exists(self.wav_filename):
            os.rename(self.wav_filename, wav_path)
            self.wav_filename = wav_path

        meta_path = get_filename(save_dir=self.save_dir, subfolder='mic', extension='.csv', time_ns=system_time_ns)
        if os.path.exists(self._metadata_file_path):
            os.rename(self._metadata_file_path, meta_path)
            self._metadata_file_path = meta_path



