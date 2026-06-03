#!/usr/bin/python3
from argparse import ArgumentParser
from typing import Optional
from subprocess import Popen, TimeoutExpired
from multiprocessing.synchronize import Event
from utilities import get_stop_event, get_filename

def script_args() -> dict:
    parser = ArgumentParser(description='Record audio.')
    parser.add_argument('--saveDir', type=str,
        help='Path within the Data folder to which data will be saved')
    parser.add_argument('--file_time', type=int, 
        help='Length of each audiofile in minutes (default 5)')
    parser.add_argument('--sampleRate', type=int,
        help='Sample rate in Hz (default 250kHz)')
    args = parser.parse_args()
    # Filter out None values and return dict
    return {k: v for k, v in vars(args).items() if v is not None}

def main(save_dir: Optional[str] = None, sample_rate: int = 250000, auto_save_interval: int = 5, ready_event: Optional[Event] = None) -> None:
    save_dir = get_filename(save_dir=save_dir, subfolder='mic').parent
    print(f'Saving audio in {save_dir}')
    print('starting audio recording')
    p = Popen(['AudioMoth-Live', str(sample_rate), 'autosave', str(auto_save_interval), str(save_dir)])
    stop_event = get_stop_event()

    # Signal that recording has started sucessfully
    if ready_event is not None:
        ready_event.set()

    # Wait until interrupt
    print('Audio recording started. Waiting for interrupt.')
    stop_event.wait()

    # Clean up subprocess before exit
    print("closing - recordAudio.py")
    terminate_process(p)
    print("finished - recordAudio.py")

def terminate_process(p: Popen, timeout: float = 5) -> None:
    try:
        p.terminate()
        p.wait(timeout=timeout)
    except TimeoutExpired:
        print('AudioMoth-Live did not exit; killing.')
        p.kill()
        p.wait()
        
if __name__ == '__main__':
    args = script_args()
    main(**args)
