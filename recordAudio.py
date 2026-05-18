import os
from pathlib import Path
from argparse import ArgumentParser
from typing import Optional
from config import default_data_path

def script_args() -> dict:
    parser = ArgumentParser(description='Record audio.')
    parser.add_argument('--saveDir', type=str
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

def main(save_dir: str = None, sample_rate: int = 250000, auto_save_interval: int = 5, heterodyne: int = None) -> None:
    if save_dir is None:
        save_dir = default_data_path() / 'mic'
    else:
        save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)
    print('SavingFile in ' + str(save_dir))

    c = 'AudioMoth-Live ' + sample_rate
    c = c + ' autosave ' + auto_save_interval + ' ' + str(save_dir)

    if heterodyne is not None:
        c = c + ' heterodyne ' + heterodyne
        print('Heterodyne might cause sporadic camera disconnect problems')

    print('starting audio recording')
    os.system(c)
    print('recordAudio.sh finished')


if __name__ == '__main__':
    args = script_args()
    main(**args)
