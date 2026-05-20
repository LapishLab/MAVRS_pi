#! /bin/python
import signal, os
from pathlib import Path
from sys import exit
from time import sleep
from argparse import ArgumentParser
from gpiozero import Button 
from datetime import datetime
from csv import DictWriter
from config import default_data_path

def script_args() -> dict:
    parser = ArgumentParser(description='Record GPIO pin 16')
    parser.add_argument('--saveDir', type=str, 
        help='Path within the Data folder to which data will be saved')
    args = parser.parse_args()
    # Filter out None values and return dict
    return {k: v for k, v in vars(args).items() if v is not None}


def main(save_dir: str = None) -> None:
    pins = [16]  # List of GPIO pins to monitor 
    csvFields = ['Time', 'Pin', 'Event']

    if save_dir is None:
        save_dir = default_data_path()
    else:
        save_dir = Path(save_dir)
    save_dir = save_dir / 'gpio'
    save_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    saveFile = save_dir / (now + '.csv')
    print('SavingFile as ' + str(saveFile))

    # Create or open the CSV file and write the header 
    with open(saveFile, "w", newline='') as csvfile: 
        writer = DictWriter(csvfile, fieldnames=csvFields) 
        writer.writeheader() 

    def log_event(pin, event): 
        timeString = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        with open(saveFile, "a", newline='') as csvfile: 
            writer = DictWriter(csvfile, fieldnames=csvFields) 
            writer.writerow({'Time': timeString, 'Pin': pin, 'Event': event}) 

    # Set up the GPIO pins and add event detection 
    buttons = [Button(pin, bounce_time=0.1) for pin in pins]
    for button in buttons: 
        button.when_released = lambda pin=button.pin.number: log_event(pin, '1') 
        button.when_pressed = lambda pin=button.pin.number: log_event(pin, '0') 

    def endRecording(sig, frame):
        print('recordInput.py finished')
        exit(0)

    signal.signal(signal.SIGINT, endRecording)
    signal.signal(signal.SIGTERM, endRecording)

    #Wait until interrupt
    try:
        while True: sleep(1)
    except KeyboardInterrupt:
        endRecording(0,None)


if __name__ == '__main__':
    args = script_args()
    main(**args)
