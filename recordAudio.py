#! /bin/python
import os
# These must be set BEFORE importing sounddevice to bypass PipeWire
os.environ["PA_ALSA_PLUGHW"] = "1"
os.environ["PA_ALSA_HOSTAPI"] = "ALSA"

from multiprocessing.synchronize import Event
from utilities import get_stop_event, get_filename
from queue import Queue
import time
from sounddevice import InputStream
from soundfile import SoundFile
import numpy as np
from typing import Protocol, TextIO, Optional

# --- Hardware Configuration ---
SAMPLE_RATE: int = 250000
CHANNELS: int = 1
BLOCK_SIZE: int = 4096     # 16.38ms chunks at 250kHz
DEVICE_INDEX: str = 'hw:3,0' 

class PortAudioTimeInfo(Protocol):
    inputBufferAdcTime: float
    outputBufferDacTime: float
    currentTime: float

class AudioPacket:
    """Statically typed container to pair hardware buffers with system timelines."""
    def __init__(self, t: int, n: int, data: np.ndarray):
        self.system_time_ns = t
        self.n_samples = n
        self.data = data


class AudioWriter:
    """Writer to handle audio data and timestamps, writing to WAV and CSV files."""
    def __init__(self, save_dir: Optional[str] = None, ready_event: Optional[Event] = None):
        self.save_dir = save_dir
        self.wav_file: Optional[SoundFile] = None
        self.csv_file: Optional[TextIO] = None
        self.file_start_ns: int = 0
        self.current_sample: int = 0
        self.audio_queue: Queue[AudioPacket] = Queue()
        self.stop_event = get_stop_event()
        self.ready_event = ready_event

    def start_recording(self):
        # Initialize the InputStream utilizing correct PortAudio bindings
        stream = InputStream(
            device=DEVICE_INDEX,
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            blocksize=BLOCK_SIZE,
            latency='high',
            dtype='int16',  # Native 16-bit signed integer format
            callback=self.audio_callback
            )

        print(f"Initializing PortAudio device #{DEVICE_INDEX} at {SAMPLE_RATE} Hz...")
        with stream:
            packet = self.audio_queue.get()
            self.open_new_files(packet.system_time_ns)
            self.write_packet(packet)

            if self.ready_event is not None:
                self.ready_event.set()

            while not self.stop_event.is_set():
                packet = self.audio_queue.get()
                self.write_packet(packet)
            self.close_files()

    def open_new_files(self, time_ns: int) -> None:
        wav_filename = get_filename(save_dir=self.save_dir, subfolder='mic', extension='.wav', time_ns=time_ns)
        wav_filename = str(wav_filename)
        csv_filename =  wav_filename.replace('.wav', '.csv')

        print(f"Creating: {wav_filename} and {csv_filename}")
        self.wav_file = SoundFile(
            wav_filename,
            mode='x',  # Prevents accidental file overwrites
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            subtype='PCM_16'
        )
        self.csv_file = open(csv_filename, 'w')
        self.csv_file.write('sample, file_us \n')
        self.file_start_ns = time_ns
        self.current_sample = 0

    def write_packet(self, packet: AudioPacket) -> None:
        if self.wav_file is None or self.csv_file is None:
            raise RuntimeError("Files are not open. Call open_new_files() first.")
        
        self.wav_file.write(packet.data)
        elapsed_us = int((packet.system_time_ns - self.file_start_ns) / 1000)
        self.csv_file.write(f'{self.current_sample}, {elapsed_us} \n')
        self.current_sample += packet.n_samples

    def close_files(self) -> None:
        if self.wav_file:
            self.wav_file.close()
            self.wav_file = None
        if self.csv_file:
            self.csv_file.close()
            self.csv_file = None
        
    def audio_callback(self, data: np.ndarray, frames: int, t: PortAudioTimeInfo, status) -> None:
        now_ns: int = time.time_ns()
        mic_latency_ns: int = int((t.currentTime - t.inputBufferAdcTime)*1_000_000_000)
        sample_ns: int = now_ns - mic_latency_ns
        packet = AudioPacket(sample_ns, frames, data.copy())
        self.audio_queue.put(packet)
        if status:
            print(f"PortAudio Status Flag: {status}", flush=True)


def main(save_dir: Optional[str] = None, ready_event: Optional[Event] = None) -> None:
    writer = AudioWriter(save_dir,ready_event)
    writer.start_recording()


if __name__ == '__main__':
    main()
