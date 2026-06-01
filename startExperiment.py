#!/usr/bin/python3
from argparse import ArgumentParser
from datetime import datetime
from typing import Optional
from config import DATA_DIR, HOSTNAME
from multiprocessing import Process
import recordAudio
import recordVideo
import recordInput
import signal
import sys

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

	# Make a list of processes for each recording
	procs = []
	procs.append(Process(target=recordInput.main, kwargs={'save_dir': saveDir}))
	procs.append(Process(target=recordAudio.main, kwargs={'save_dir': saveDir}))
	procs.append(Process(target=recordVideo.main, kwargs={'save_dir': saveDir}))
	for p in procs:
		p.start()

	def handle_sigterm(signum, frame):
		print("\nCleaning up processes...")
		for p in procs:
			if p.is_alive():
				p.terminate()
		for p in procs:
			p.join()
		sys.exit(0)

	# Register the SIGTERM handler
	signal.signal(signal.SIGTERM, handle_sigterm)
	signal.signal(signal.SIGINT, handle_sigterm)  # SIGINT is for handling Ctrl+C gracefully

	print('Experiment started. Waiting for interput.')
	signal.pause()  # Wait indefinitely until a signal is received

if __name__ == '__main__':
	args = script_args()
	main(**args)
