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

# --- Hardware Configuration ---
SAMPLE_RATE: int = 250000
CHANNELS: int = 1
BLOCK_SIZE: int = 4096     # 16.38ms chunks at 250kHz

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
    """Writer to handle audio data and timestamps, writing to WAV and HDF5 metadata files."""
    def __init__(self, save_dir: str):
        super().__init__(daemon=True)

        # Initialize WAV and .h5 files with temporary names; will rename later based on first packet timestamp
        self.save_dir = save_dir
        self.wav_filename = save_dir + "/temp.wav"
        self.wav_file: SoundFile = SoundFile(
            self.wav_filename,
            mode='x',
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            subtype='PCM_16'
        )
        self._metadata_file_path = save_dir + "/temp.h5"
        self._metadata_file: h5py.File = h5py.File(self._metadata_file_path, mode='w')

        # Preallocate a dataset for metadata entries (sample index, elapsed time in microseconds)
        self._metadata_dataset = self._metadata_file.create_dataset('metadata', shape=(0, 2), maxshape=(None, 2), dtype=np.int64)
        self._metadata_buffer = np.empty((4096, 2), dtype=np.int64) # Should fill every ~67s
        self._metadata_count = 0
        self._current_sample = 0

        # Preallocate a ring buffer of audio packets to avoid memory allocation during real-time audio capture
        self.n_slots = 10
        self.write_idx = 0
        self.read_idx = 0
        self.buffer = [AudioPacket(BLOCK_SIZE) for _ in range(self.n_slots)]

        # Threading events to manage stopping and signaling when new data is available
        self._stop_event = threading.Event()
        self._data_available = threading.Event()

        # File start time in nanoseconds, set when the first audio packet is added
        self._file_start_ns: Optional[int] = None
        
        self.start()

    def run(self) -> None:
        while self._file_start_ns is None:
            self._data_available.wait(timeout=0.02)
        self._rename_output_files(self._file_start_ns)

        while not self._stop_event.is_set():
            self._data_available.wait(timeout=0.5)
            while self.read_idx < self.write_idx:
                packet = self.buffer[self.read_idx % self.n_slots]
                self.wav_file.write(packet.data[:packet.n_samples])
                self._write_metadata_entry(packet)
                self.read_idx += 1
            self._data_available.clear()

    def add(self, system_time_ns: int, n_samples: int, data: np.ndarray) -> None:
        """Add a new audio packet to the writer buffer."""
        self._push(system_time_ns, n_samples, data)

    def stop(self) -> None:
        self._stop_event.set()
        self._data_available.set()
        self.join(timeout=5.0)

        self.wav_file.flush()
        self.wav_file.close()

        self._flush_metadata_buffer()
        self._metadata_file.close()

    def _push(self, system_time_ns: int, n_samples: int, data: np.ndarray) -> None:
        if self._file_start_ns is None:
            self._file_start_ns = system_time_ns

        slot = self.buffer[self.write_idx % self.n_slots]
        slot.set(system_time_ns, n_samples, data)
        self.write_idx += 1
        self._data_available.set()

    def _rename_output_files(self, system_time_ns: int) -> None:
        wav_path = get_filename(save_dir=self.save_dir, subfolder='mic', extension='.wav', time_ns=system_time_ns)
        if os.path.exists(self.wav_filename):
            os.rename(self.wav_filename, wav_path)
            self.wav_filename = wav_path

        h5_path = get_filename(save_dir=self.save_dir, subfolder='mic', extension='.h5', time_ns=system_time_ns)
        if os.path.exists(self._metadata_file_path):
            os.rename(self._metadata_file_path, h5_path)
            self._metadata_file_path = h5_path

    def _write_metadata_entry(self, packet: AudioPacket) -> None:
        if self._file_start_ns is None:
            raise Exception("File start time is not set. Cannot write metadata entry.")
        elapsed_us = int((packet.system_time_ns - self._file_start_ns) / 1000)
        self._metadata_buffer[self._metadata_count, 0] = self._current_sample
        self._metadata_buffer[self._metadata_count, 1] = elapsed_us
        self._metadata_count += 1
        self._current_sample += packet.n_samples

        if self._metadata_count >= self._metadata_buffer.shape[0]:
            self._flush_metadata_buffer()

    def _flush_metadata_buffer(self) -> None:
        if self._metadata_count == 0:
            return

        rows = self._metadata_buffer[:self._metadata_count]
        current_size = self._metadata_dataset.shape[0]
        self._metadata_dataset.resize((current_size + rows.shape[0], 2))
        self._metadata_dataset[current_size:current_size + rows.shape[0]] = rows
        self._metadata_file.flush()
        self._metadata_count = 0


