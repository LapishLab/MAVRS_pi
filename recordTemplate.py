#! /bin/python
from typing import Optional
from argparse import ArgumentParser
from multiprocessing.synchronize import Event
from utilities import get_stop_event, get_filename
import threading
import sys

def script_args() -> dict[str, str]:
    parser = ArgumentParser(description='Record ??')
    parser.add_argument('--saveDir', type=str, 
        help='Path within the Data folder to which data will be saved')
    args = parser.parse_args()
    # Filter out None values and return dict
    return {k: v for k, v in vars(args).items() if v is not None}

class WorkerThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.__stop__event = threading.Event()
        self.exception = None
    def stop(self):
        self.__stop__event.set()
    def run(self):
        try:
            while not self.__stop__event.is_set():
                self.__stop__event.wait(timeout=1.0)
                print('working')
        except Exception as e:
            self.exception = e
            print(f'[ERROR] Thread encountered an error: {e}', file=sys.stderr)
        finally:
            print('cleaning up resources')

def main(save_dir: Optional[str] = None, ready_event: Optional[Event] = None) -> None:
    saveFile = get_filename(save_dir=save_dir, subfolder='subname??', extension='.ext??')
    print(f'Saving  data in {saveFile}')

    my_thread = WorkerThread()
    my_thread.start()
    stop_event = get_stop_event()

    if ready_event is not None:
        ready_event.set()

    # Wait until interrupt
    print('?? recording started. Waiting for interrupt.')
    stop_event.wait()

    # Clean up GPIO resources before exit
    print('closing - ??.py')
    my_thread.stop()
    my_thread.join() # wait for the thread to finish
    print('finished - ??.py')


if __name__ == '__main__':
    args = script_args()
    main(**args)
