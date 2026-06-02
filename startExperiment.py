#!/usr/bin/python3
from argparse import ArgumentParser
from datetime import datetime
from typing import Optional
from config import DATA_DIR, HOSTNAME
from multiprocessing import Process
import threading
import recordAudio
import recordVideo
import recordInput
import signal

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

   # Define a signal handler to cleanly exit on interrupt
	stop_event = threading.Event()
	stop_func = lambda sig, frame: stop_event.set()
	stop_signals = [signal.SIGINT, signal.SIGTERM]
	[signal.signal(sig, stop_func) for sig in stop_signals]
	
	# Wait until interrupt, then terminate the subprocesses
	print('Experiment started. Waiting for interrupt.')
	stop_event.wait()

	# Clean up processes after signal
	print("\nCleaning up processes...")
	for p in procs:
		if p.is_alive():
			p.terminate()
	for p in procs:
		p.join()

if __name__ == '__main__':
	args = script_args()
	main(**args)
