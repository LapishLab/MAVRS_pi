#!/usr/bin/python3
from argparse import ArgumentParser
from datetime import datetime
from subprocess import Popen
from config import DATA_DIR, ROOT_DIR, HOSTNAME

parser = ArgumentParser(description='start an experiment')
parser.add_argument('--session', 
                    help='SessionName'
                    )
args = parser.parse_args()

if args.session is None:
        args.session = datetime.now().strftime("%Y%m%d_%H%M%S")

saveRoot = DATA_DIR / args.session / HOSTNAME

# Start GPIO recording
scriptPath = ROOT_DIR /'recordInput.py'
saveDir = saveRoot / 'gpio'
Popen(['python', '-u', str(scriptPath), '--saveDir', str(saveDir)])

# Start audio recording
scriptPath = ROOT_DIR / 'recordAudio.py'
saveDir = saveRoot / 'mic'
Popen(['python', '-u', str(scriptPath), '--saveDir', str(saveDir)])

# Start video recording
scriptPath = ROOT_DIR / 'recordVideo.py'
saveDir = saveRoot / 'cam'
Popen(['python', '-u', str(scriptPath), '--saveDir', str(saveDir)])