# config.py
from datetime import datetime
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
CONFIG_YAML = ROOT_DIR / "default_settings.yaml"

HOSTNAME = 'Windows' #os.uname().nodename
# Automatically create folders if they don't exist
DATA_DIR.mkdir(exist_ok=True)

def default_data_path():
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    return DATA_DIR / now / HOSTNAME