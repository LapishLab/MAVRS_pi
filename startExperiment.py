from argparse import ArgumentParser
from datetime import datetime
from subprocess import Popen
from config import DATA_DIR, ROOT_DIR, HOSTNAME
import signal
import time
import sys

parser = ArgumentParser(description='start an experiment')
parser.add_argument('--session', help='SessionName')
args = parser.parse_args()

if args.session is None:
	args.session = datetime.now().strftime("%Y%m%d_%H%M%S")

saveDir = DATA_DIR / args.session / HOSTNAME

print('starting experiment')

processes = []

# Start count recording
processes.append(Popen(['python', '-u', ROOT_DIR/'count.py', '--saveDir', saveDir, '--fname', 'count_A']))
processes.append(Popen(['python', '-u', ROOT_DIR/'count.py', '--saveDir', saveDir, '--fname', 'count_B']))


def handle_sigterm(signum, frame):
	print("\nCleaning up subprocesses...")
	for p in processes: 
		if p.poll() is None: 
			p.terminate()
	for p in processes:
		p.wait() 
	sys.exit(0)

# Register the SIGTERM handler
signal.signal(signal.SIGTERM, handle_sigterm)
signal.signal(signal.SIGINT, handle_sigterm) #SIGINT is for handling Ctrl+C gracefully

while True:
	time.sleep(1)