
import os
# These must be set BEFORE importing sounddevice to bypass PipeWire
os.environ["PA_ALSA_PLUGHW"] = "1"
os.environ["PA_ALSA_HOSTAPI"] = "ALSA"
import queue
import time
import sounddevice as sd
import soundfile as sf
import numpy as np
from typing import Protocol, TextIO
from datetime import datetime

# --- Hardware Configuration ---
SAMPLE_RATE: int = 250000
CHANNELS: int = 1
BLOCK_SIZE: int = 4096     # 16.38ms chunks at 250kHz
DEVICE_INDEX: str = 'hw:3,0' 

FILE_INTERVAL_SEC: int = 5 * 60
BLOCKS_PER_FILE: int =  round(FILE_INTERVAL_SEC * SAMPLE_RATE / BLOCK_SIZE)

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
        
# Thread-safe queue to pass timestamped chunks from audio thread to disk thread
audio_queue: queue.Queue[AudioPacket] = queue.Queue()

def audio_callback(data: np.ndarray, frames: int, t: PortAudioTimeInfo, status) -> None:
    now_ns: int = time.time_ns()
    mic_latency_ns: int = int((t.currentTime - t.inputBufferAdcTime)*1_000_000_000)
    sample_ns: int = now_ns - mic_latency_ns
    packet = AudioPacket(sample_ns, frames, data.copy())
    audio_queue.put(packet)
    if status:
        print(f"PortAudio Status Flag: {status}", flush=True)

def get_new_files(time_ns: int) -> tuple[sf.SoundFile, TextIO] :
    time_str = datetime.fromtimestamp(time_ns / 1_000_000_000).strftime("%Y%m%d_%H%M%S_%f")

    filename = f"{time_str}.wav"
    print(f"Creating: {filename}")
    wav_file = sf.SoundFile(
        filename,
        mode='x',  # Prevents accidental file overwrites
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        subtype='PCM_16'
    )

    filename = f"{time_str}.csv"
    csv_file = open(filename, 'w')
    csv_file.write('sample, file_us \n')
    return (wav_file, csv_file)

def process_audio_stream() -> None:
    """Orchestrates the background hardware stream and manages file generation 
    on the main execution thread.
    """
    # Initialize the InputStream utilizing correct PortAudio bindings
    stream = sd.InputStream(
        device=DEVICE_INDEX,
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        blocksize=BLOCK_SIZE,
        latency='high',
        dtype='int16',  # Native 16-bit signed integer format
        callback=audio_callback
    )

    print(f"Initializing PortAudio device #{DEVICE_INDEX} at {SAMPLE_RATE} Hz...")
    with stream:
        print("Hardware capture running. Processing real-time data stream...")
        while True:
            packet: AudioPacket = audio_queue.get()
            file_start_ns = packet.system_time_ns
            current_sample = 0

            wav_file, csv_file = get_new_files(file_start_ns)
            wav_file.write(packet.data)
            
            csv_file.write(f'{current_sample}, {int((packet.system_time_ns-file_start_ns) / 1000)} \n')
            current_sample += packet.n_samples

            for i in range(BLOCKS_PER_FILE):
                packet: AudioPacket = audio_queue.get()
                wav_file.write(packet.data)
                csv_file.write(f'{current_sample}, {int((packet.system_time_ns-file_start_ns) / 1000)} \n')
                current_sample += packet.n_samples
            
            wav_file.close()
            csv_file.close()


if __name__ == "__main__":
    process_audio_stream()
