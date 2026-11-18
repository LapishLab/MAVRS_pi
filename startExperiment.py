#!/usr/bin/python3
from argparse import ArgumentParser
from datetime import datetime
from typing import List, Optional
from config import DATA_DIR, HOSTNAME
from multiprocessing import Process, Event
from utilities import get_settings
from recording_status import write_status, refresh_worker_states
from recording_log import write_recording_log
import threading
import recordAudio
import recordVideo
import recordInput
import signal
from time import time, monotonic


MONITOR_INTERVAL = 0.5
STATUS_INTERVAL = 2


def run_worker(function, save_dir, ready_event):
	# Forked children must not inherit the parent's stop handler during initialization.
	for stop_signal in (signal.SIGINT, signal.SIGTERM):
		signal.signal(stop_signal, signal.SIG_DFL)
	function(save_dir=save_dir, ready_event=ready_event)

def script_args() -> dict[str, str]:
	parser = ArgumentParser(description='start an experiment')
	parser.add_argument('--session', type=str,
		help='SessionName (default current date and time in YYYYMMDD_HHMMSS format)')
	args = parser.parse_args()
	# Filter out None values and return dict
	return {k: v for k, v in vars(args).items() if v is not None}

def main(session: Optional[str] = None) -> int:
	if session is None:
		session = datetime.now().strftime("%Y%m%d_%H%M%S")

	saveDir = DATA_DIR / session / HOSTNAME

	# Make a list of processes for each recording modality along with an Event for each to signal when they are ready
	recordings = get_settings()['recordings']
	funcs = {}
	if recordings['gpio']: funcs['GPIO'] = recordInput.main
	if recordings['audio']: funcs['Audio'] = recordAudio.main
	if recordings['video']: funcs['Video'] = recordVideo.main
	if not funcs:
		raise RuntimeError('No recording components are enabled')

	# Install the handler before startup so a stop during initialization is honored.
	stop_event = threading.Event()
	for stop_signal in (signal.SIGINT, signal.SIGTERM):
		signal.signal(stop_signal, lambda sig, frame: stop_event.set())

	write_recording_log(saveDir)

	states = {name: {'state': 'starting', 'exit_code': None} for name in funcs}
	write_status(session, states)
	last_published = monotonic()
	workers = {}
	try:
		for name, function in funcs.items():
			if stop_event.is_set():
				break
			ready = Event()
			process = Process(target=run_worker, args=(function, saveDir, ready))
			try:
				process.start()
			except Exception as exc:
				states[name] = {'state': 'failed', 'exit_code': None, 'reason': f'could not start: {exc}'}
				print(f'{name} recorder failed to start: {exc}', flush=True)
				continue
			workers[name] = (process, ready, monotonic())

		print('Experiment started. Monitoring recording components.')
		while not stop_event.is_set():
			changed = refresh_worker_states(workers, states)
			if changed or monotonic() - last_published >= STATUS_INTERVAL:
				try:
					write_status(session, states)
				except OSError as exc:
					print(f'Could not publish recorder status: {exc}', flush=True)
				last_published = monotonic()
			if all(state['state'] == 'failed' for state in states.values()):
				print('All recording components failed', flush=True)
				return 1
			stop_event.wait(MONITOR_INTERVAL)
		return 0
	finally:
		print('closing - startExperiment.py')
		shutdown_all_workers([process for process, _, _ in workers.values()])
		print('finished - startExperiment.py')


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
	raise SystemExit(main(**args))
