# config.py
from datetime import datetime
import os
from pathlib import Path

ROOT_DIR: Path = Path(__file__).resolve().parent
DATA_DIR: Path = ROOT_DIR / "data"
DEFAULT_SETTINGS_FILE: Path = ROOT_DIR / "default_settings.yaml"
USER_SETTINGS_FILE: Path = Path.home() / "mavrs_pi_config.yaml"

HOSTNAME: str = os.uname().nodename
# Automatically create folders if they don't exist
DATA_DIR.mkdir(exist_ok=True)

def default_data_path() -> Path:
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    return DATA_DIR / now / HOSTNAME