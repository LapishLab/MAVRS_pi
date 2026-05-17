from argparse import ArgumentParser
from datetime import datetime
from multiprocessing import Process
import count
from config import DATA_DIR, ROOT_DIR, HOSTNAME
import signal
import time
import sys


def main():
	parser = ArgumentParser(description='start an experiment')
	parser.add_argument('--session', help='SessionName')
	args = parser.parse_args()

	if args.session is None:
		args.session = datetime.now().strftime("%Y%m%d_%H%M%S")

	saveDir = DATA_DIR / args.session / HOSTNAME

	print('starting experiment')

	processes = []

	# Start count recording using multiprocessing
	processes.append(Process(target=count.main, args=(saveDir, 'count_A')))
	processes.append(Process(target=count.main, args=(saveDir, 'count_B')))

	for p in processes:
		p.start()


	def handle_sigterm(signum, frame):
		print("\nCleaning up processes...")
		for p in processes:
			if p.is_alive():
				p.terminate()
		for p in processes:
			p.join()
		sys.exit(0)

	# Register the SIGTERM handler
	signal.signal(signal.SIGTERM, handle_sigterm)
	signal.signal(signal.SIGINT, handle_sigterm)  # SIGINT is for handling Ctrl+C gracefully

	try:
		while True:
			time.sleep(1)
	except KeyboardInterrupt:
		handle_sigterm(None, None)


if __name__ == '__main__':
	main()