#!/usr/bin/python3
from argparse import ArgumentParser
from datetime import datetime
from typing import List, Optional
from config import DATA_DIR, HOSTNAME
from multiprocessing import Process, Event
import threading
import recordAudio
import recordVideo
import recordInput
import signal
from time import time

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

	# Make a list of processes for each recording modality along with an Event for each to signal when they are ready
	funcs = [recordInput.main, recordAudio.main, recordVideo.main]
	procs = []
	ready_events = []
	for f in funcs:
		ready = Event()
		p = Process(target=f, kwargs={'save_dir': saveDir, 'ready_event': ready})
		p.start()
		procs.append(p)
		ready_events.append(ready)

	# Wait for all child processes to signal they are ready
	for r in ready_events:
		r.wait()
	print('All subprocesses successfully started')

	# Define a signal handler to cleanly exit on interrupt
	stop_event = threading.Event()
	stop_func = lambda sig, frame: stop_event.set()
	stop_signals = [signal.SIGINT, signal.SIGTERM]
	[signal.signal(sig, stop_func) for sig in stop_signals]
	
	# Wait until interrupt, then terminate the subprocesses
	print('Experiment started. Waiting for interrupt.')
	stop_event.wait()

	# Clean up processes after signal
	print("closing - startExperiment.py")
	shutdown_all_workers(procs)
	print("finished - startExperiment.py")


def shutdown_all_workers(procs: List[Process], timeout: float = 10) -> None:	
	# Tell everyone to die cleanly.
	for p in procs:
		p.terminate()
			
	# Give them a collective window to clean up and exit.
	start_time: float = time()
	for p in procs:
		remaining_time = start_time+timeout-time()
		if remaining_time > 0:
			p.join(timeout=remaining_time)
		
	# Forcefully kill any remaining processes
	for p in procs:
		if p.is_alive():
			p.kill()
			p.join()

if __name__ == '__main__':
	args = script_args()
	main(**args)
