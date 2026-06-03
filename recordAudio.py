from pathlib import Path
from argparse import ArgumentParser
from config import default_data_path
import signal
from typing import Optional
from subprocess import Popen, TimeoutExpired
import threading
from multiprocessing.synchronize import Event

def script_args() -> dict:
    parser = ArgumentParser(description='Record audio.')
    parser.add_argument('--saveDir', type=str,
        help='Path within the Data folder to which data will be saved')
    parser.add_argument('--file_time', type=int, 
        help='Length of each audiofile in minutes (default 5)')
    parser.add_argument('--sampleRate', type=int,
        help='Sample rate in Hz (default 250kHz)')
    parser.add_argument('--heterodyne', type=int,
        help='Heterodyne frequency for audio output or None to disable (default None)')
    args = parser.parse_args()
    # Filter out None values and return dict
    return {k: v for k, v in vars(args).items() if v is not None}

def main(save_dir: Optional[str] = None, sample_rate: int = 250000, auto_save_interval: int = 5, heterodyne: Optional[int] = None, ready_event: Optional[Event] = None) -> None:
    if save_dir is None:
        save_dir = default_data_path()
    else:
        save_dir = Path(save_dir)
    save_dir = save_dir / 'mic'
    save_dir.mkdir(parents=True, exist_ok=True)
    print('SavingFile in ' + str(save_dir))

    c = ['AudioMoth-Live', str(sample_rate), 'autosave', str(auto_save_interval), str(save_dir)]

    if heterodyne is not None:
        c.append('heterodyne')
        c.append(str(heterodyne))
        print('Heterodyne might cause sporadic camera disconnect problems')

    print('starting audio recording')
    p = Popen(c)

    # Define a signal handler to cleanly exit on interrupt
    stop_event = threading.Event()
    stop_func = lambda sig, frame: stop_event.set()
    stop_signals = [signal.SIGINT, signal.SIGTERM]
    [signal.signal(sig, stop_func) for sig in stop_signals]

    # Wait until interrupt, then terminate the subprocess
    print('Audio recording started. Waiting for interrupt.')
    if ready_event is not None:
        ready_event.set()
    stop_event.wait()

    print("closing - recordAudio.py")
    try:
        p.terminate()
        p.wait(timeout=5)
    except TimeoutExpired:
        print('AudioMoth-Live did not exit; killing.')
        p.kill()
        p.wait()
    print("finished - recordAudio.py")
        
if __name__ == '__main__':
    args = script_args()
    main(**args)
