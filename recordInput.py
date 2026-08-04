#! /bin/python
from pathlib import Path
from typing import Optional, TextIO
from argparse import ArgumentParser
from gpiozero import Button 
from datetime import datetime
from csv import DictWriter
from multiprocessing.synchronize import Event
from utilities import get_stop_event, get_filename
from functools import partial

def script_args() -> dict[str, str]:
    parser = ArgumentParser(description='Record GPIO pin 16')
    parser.add_argument('--saveDir', type=str, 
        help='Path within the Data folder to which data will be saved')
    args = parser.parse_args()
    # Filter out None values and return dict
    return {k: v for k, v in vars(args).items() if v is not None}


def start_recording(saveFile: str | Path, pins: list[int] = [16]) -> tuple[list[Button], 'TextIO']:

    # Open the CSV file and write the header
    csvFields = ['Time', 'Pin', 'Event']
    csvfile = open(saveFile, "w", newline='')
    writer = DictWriter(csvfile, fieldnames=csvFields)
    writer.writeheader()

    def log_event(pin, event): 
        now = datetime.now()
        timeString = f"{now.year:04d}{now.month:02d}{now.day:02d}_{now.hour:02d}{now.minute:02d}{now.second:02d}_{now.microsecond:06d}"
        writer.writerow({'Time': timeString, 'Pin': pin, 'Event': event})
        csvfile.flush() 

    # Set up the GPIO pins and add event detection 
    buttons = []
    for pin in pins:
        b = Button(pin, bounce_time=None)
        b.when_pressed = partial(log_event, pin, '0')
        b.when_released = partial(log_event, pin, '1')
        buttons.append(b)
    return buttons, csvfile

def main(save_dir: Optional[str] = None, ready_event: Optional[Event] = None) -> None:
    saveFile = get_filename(save_dir=save_dir, subfolder='gpio', extension='.csv')
    print(f'Saving GPIO data in {saveFile}')
    buttons, csvfile = start_recording(saveFile)
    stop_event = get_stop_event()

    
    if ready_event is not None:
        ready_event.set()

    # Wait until interrupt
    print('GPIO recording started. Waiting for interrupt.')
    stop_event.wait()

    # Clean up GPIO resources before exit
    print('closing - recordInput.py')
    [b.close() for b in buttons]
    csvfile.close()
    print('finished - recordInput.py')


if __name__ == '__main__':
    args = script_args()
    main(**args)
