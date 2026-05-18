#!/usr/bin/python3
from argparse import ArgumentParser, Namespace
from datetime import datetime
from subprocess import Popen
from typing import Optional
from config import DATA_DIR, ROOT_DIR, HOSTNAME

def script_args() -> dict:
    parser = ArgumentParser(description='start an experiment')
    parser.add_argument('--session', type=str,
		help='SessionName (default current date and time in YYYYMMDD_HHMMSS format)')
    args = parser.parse_args()
    # Filter out None values and return dict
    return {k: v for k, v in vars(args).items() if v is not None}

def main(session: Optional[str] = None) -> None:
    if session is None:
        session = datetime.now().strftime("%Y%m%d_%H%M%S")

    saveDir = DATA_DIR / session / HOSTNAME

    # Start GPIO recording
    scriptPath = ROOT_DIR / 'recordInput.py'
    Popen(['python', '-u', str(scriptPath), '--saveDir', str(saveDir)])

    # Start audio recording
    scriptPath = ROOT_DIR / 'recordAudio.py'
    Popen(['python', '-u', str(scriptPath), '--saveDir', str(saveDir)])

    # Start video recording
    scriptPath = ROOT_DIR / 'recordVideo.py'
    Popen(['python', '-u', str(scriptPath), '--saveDir', str(saveDir)])

if __name__ == '__main__':
    args = script_args()
    main(**args)
