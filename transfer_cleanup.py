"""Inventory visible recordings and remove files approved by the server.

Usage: python3 transfer_cleanup.py inventory|delete
The delete command reads JSON rows of [relative path, size, mtime_ns] on stdin.
"""

import json
import os
import stat
import sys
from pathlib import Path

DATA_ROOT = Path(__file__).resolve().parent / "data"
DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def inventory(root: Path = DATA_ROOT) -> list[list[str | int]]:
    if not root.is_dir():
        raise FileNotFoundError(root)
    files = []

    def walk_error(error: OSError) -> None:
        raise error

    for directory, dirs, names in os.walk(root, followlinks=False, onerror=walk_error):
        dirs[:] = [name for name in dirs if not name.startswith(".") and
                   not os.path.islink(os.path.join(directory, name))]
        for name in names:
            if name.startswith("."):
                continue
            path = Path(directory) / name
            info = path.lstat()
            if stat.S_ISREG(info.st_mode):
                files.append([path.relative_to(root).as_posix(), info.st_size, info.st_mtime_ns])
    return files


def delete_selected(candidates: list[list[str | int]], root: Path = DATA_ROOT) -> int:
    root_fd = os.open(root, DIRECTORY_FLAGS)
    deleted = 0
    try:
        for relative, size, mtime_ns in candidates:
            parts = relative.split("/")
            if not parts or any(part in ("", ".", "..") or part.startswith(".") for part in parts):
                continue
            fd = os.dup(root_fd)
            try:
                for part in parts[:-1]:
                    next_fd = os.open(part, DIRECTORY_FLAGS, dir_fd=fd)
                    os.close(fd)
                    fd = next_fd
                info = os.stat(parts[-1], dir_fd=fd, follow_symlinks=False)
                if (stat.S_ISREG(info.st_mode) and info.st_size == size and
                        info.st_mtime_ns == mtime_ns):
                    os.unlink(parts[-1], dir_fd=fd)
                    deleted += 1
            except FileNotFoundError:
                pass
            finally:
                os.close(fd)
    finally:
        os.close(root_fd)

    for directory, _, _ in os.walk(root, topdown=False, followlinks=False):
        if Path(directory) == root:
            continue
        relative_parts = Path(directory).relative_to(root).parts
        if any(part.startswith(".") for part in relative_parts) or os.path.islink(directory):
            continue
        try:
            os.rmdir(directory)
        except OSError:
            pass
    return deleted


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in ("inventory", "delete"):
        raise SystemExit("Usage: transfer_cleanup.py inventory|delete")
    if sys.argv[1] == "inventory":
        print(json.dumps(inventory()))
    else:
        candidates = json.load(sys.stdin)
        print(json.dumps({"deleted": delete_selected(candidates), "selected": len(candidates)}))


if __name__ == "__main__":
    main()
