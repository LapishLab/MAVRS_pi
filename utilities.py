
import signal, threading
from pathlib import Path
from typing import Optional
from datetime import datetime
from config import default_data_path


def get_stop_event():
	# Define a signal handler to cleanly exit on interrupt
	stop_event = threading.Event()
	stop_func = lambda sig, frame: stop_event.set()
	stop_signals = [signal.SIGINT, signal.SIGTERM]
	[signal.signal(sig, stop_func) for sig in stop_signals]
	return stop_event


def get_filename(save_dir: Optional[str] = None, subfolder: str = '', extension: str = '') -> Path:
    if save_dir is None:
        save_dir = default_data_path()
    else:
        save_dir = Path(save_dir)
    save_dir = save_dir / subfolder
    save_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    saveFile = save_dir / (now + extension)
    print(f'SavingFile as {saveFile}')
    return saveFile