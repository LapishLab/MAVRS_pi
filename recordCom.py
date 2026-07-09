#! /bin/python
import threading
from typing import Optional
from argparse import ArgumentParser
from gpiozero import Button 
from datetime import datetime
from csv import DictWriter
from multiprocessing.synchronize import Event
from utilities import get_stop_event, get_filename
from subprocess import Popen, TimeoutExpired
import time
import serial
from serial.tools import list_ports
# from cap_plotter import run_plot

import subprocess


def write_data(data_file, ser, stop_event):    
	# ser = open_serial_port(rate)

	start_time = time.time() # more performant than datetime.now()
	with open(data_file, 'w', encoding='utf-8', buffering=1) as f:
		f.write(f"time,c1,c2\n")
		while not stop_event.is_set():
			line = ser.readline().decode('utf-8').strip()
			elapsed_time = time.time() - start_time
			f.write(f"{elapsed_time:.4f},{line}\n")
	print('closed cap file')

def script_args() -> dict:
	parser = ArgumentParser(description='Record GPIO pin 16')
	parser.add_argument('--save_dir', type=str, 
		help='Path within the Data folder to which data will be saved')
	args = parser.parse_args()
	# Filter out None values and return dict
	return {k: v for k, v in vars(args).items() if v is not None}

def main(save_dir: Optional[str] = None, ready_event: Optional[Event] = None) -> None:
	ser = open_serial_port('/dev/ttyACM0', 250000)
	stop_event = get_stop_event()
	thread_stopper = threading.Event()

	saveFile = get_filename(save_dir=save_dir, subfolder='capacitance', extension='.csv')
	print(f'Saving capacitance data in {saveFile}')
	
	t = threading.Thread(target=write_data, args=(saveFile, ser, thread_stopper))
	t.start()

	plot_proc = subprocess.Popen(["/home/pi/plotter/.venv/bin/python", "/home/pi/plotter/cap_plotter.py", str(saveFile)])


	# t2 = threading.Thread(target=run_plot, args=(saveFile)
	# t2.start()

	if ready_event is not None:
		ready_event.set()

	# Wait until interrupt
	print('Capacitance recording started. Waiting for interrupt.')
	stop_event.wait()

	# Clean up resources before exit
	print('closing - recordComp.py')
	thread_stopper.set()
	plot_proc.terminate()
	t.join()
	# t2.join()
	plot_proc.wait()
	print('finished - recordComp.py')

def terminate_process(p: Popen, timeout: float = 5) -> None:
	try:
		p.terminate()
		p.wait(timeout=timeout)
	except TimeoutExpired:
		print('AudioMoth-Live did not exit; killing.')
		p.kill()
		p.wait()

def open_serial_port(port, rate):
	while True:
		try:
			ser = serial.Serial(port, rate, timeout=None)
			print(f"Opened serial port {port} @ {rate}")
			return ser
		except Exception as e:
			print(f"Failed to open serial port {port}: {e}")
			print(f"retrying in 5 seconds...")
			time.sleep(5)

if __name__ == '__main__':
	args = script_args()
	main(**args)
