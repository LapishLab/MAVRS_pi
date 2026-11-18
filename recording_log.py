"""Save the configuration and code revision used for a recording."""

import shutil
from pathlib import Path
from subprocess import run

from config import ROOT_DIR, USER_SETTINGS_FILE


def write_recording_log(save_dir: Path) -> None:
    log_dir = save_dir / "log"
    log_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(USER_SETTINGS_FILE, log_dir / USER_SETTINGS_FILE.name)

    def git_value(*args: str) -> str:
        return run(
            ["git", "-C", str(ROOT_DIR), *args],
            check=True, capture_output=True, text=True,
        ).stdout.strip()

    branch = git_value("rev-parse", "--abbrev-ref", "HEAD")
    commit = git_value("rev-parse", "HEAD")
    (log_dir / "recording.log").write_text(
        f"Branch: {branch}\nCommit: {commit}\n", encoding="utf-8"
    )
