from pathlib import Path
from argparse import ArgumentParser
from config import default_data_path
import signal
from typing import Optional
from subprocess import Popen
import sys

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

def main(save_dir: Optional[str] = None, sample_rate: int = 250000, auto_save_interval: int = 5, heterodyne: Optional[int] = None) -> None:
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

    def handle_sigterm(signum, frame):
        print("\nEnding Audio recording")
        if p.poll() is None:  # Check if the process is still running
            p.terminate()
        sys.exit(0)

	# Register the SIGTERM handler
    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigterm)  # SIGINT is for handling Ctrl+C gracefully
    
    #Wait until interrupt
    print('Audio recording started. Waiting for interrupt.')
    signal.pause()
        
if __name__ == '__main__':
    args = script_args()
    main(**args)
