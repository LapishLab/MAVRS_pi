"""Publish and query recorder health for the server and command line."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
from time import monotonic


STARTUP_TIMEOUT = 60  # An unready worker must not leave startup pending forever.
STATUS_STALE_AFTER = 8


def status_path() -> Path:
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    return Path(runtime_dir) / "mavrs-recording-status.json"


def write_status(session: str, components: dict[str, dict]) -> None:
    """Replace the status record atomically so readers never see partial JSON."""
    path = status_path()
    record = {
        "session": session,
        "pid": os.getpid(),
        "invocation_id": os.environ.get("INVOCATION_ID", ""),
        "observed_at": monotonic(),
        "components": components,
    }
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".mavrs-status-", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(record, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def refresh_worker_states(workers: dict, states: dict[str, dict]) -> bool:
    """Observe exits and ready signals; never clear a previous failure."""
    changed = False
    for name, (process, ready, started_at) in workers.items():
        state = states[name]['state']
        if state == 'failed':
            continue
        if process.exitcode is not None:
            states[name] = {'state': 'failed', 'exit_code': process.exitcode,
                            'reason': 'exited before ready' if state == 'starting' else 'exited'}
            print(f'{name} recorder failed: exit code {process.exitcode}', flush=True)
            changed = True
        elif state == 'starting' and ready.is_set():
            states[name] = {'state': 'recording', 'exit_code': None}
            changed = True
        elif state == 'starting' and monotonic() - started_at >= STARTUP_TIMEOUT:
            states[name] = {'state': 'failed', 'exit_code': None, 'reason': 'startup timed out'}
            print(f'{name} recorder failed: startup timed out', flush=True)
            process.terminate()
            process.join(timeout=2)
            if process.is_alive():
                process.kill()
                process.join()
            changed = True
    return changed


def unit_properties(unit: str) -> dict[str, str]:
    result = subprocess.run(
        ["systemctl", "--user", "show", f"{unit}.service", "--property=ActiveState,Result,MainPID,InvocationID"],
        text=True, capture_output=True, check=True, timeout=3,
    )
    return dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)


def get_status(unit: str = "mavrs") -> dict:
    """Combine systemd state with the current recorder's component record."""
    properties = unit_properties(unit)
    active = properties.get("ActiveState") == "active"
    if properties.get("ActiveState") == "activating":
        return {"state": "starting", "session": None, "components": {}}
    failed = properties.get("ActiveState") == "failed" or (
        not active and properties.get("Result") not in (None, "success")
    )
    summary = {"state": "failed" if failed else "stopped", "session": None, "components": {}}
    if not active and not failed:
        return summary

    try:
        record = json.loads(status_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {**summary, "state": "starting"} if active else summary

    # A status from a previous service invocation must never look healthy.
    invocation_id = properties.get("InvocationID", "")
    current_run = (isinstance(record, dict)
                   and record.get("pid") == int(properties.get("MainPID", "0"))
                   and (not invocation_id or record.get("invocation_id") == invocation_id))
    previous_failed_run = (failed and isinstance(record, dict) and invocation_id
                           and record.get("invocation_id") == invocation_id)
    if not current_run and not previous_failed_run:
        return {**summary, "state": "starting"} if active else summary

    if active and (not isinstance(record.get("observed_at"), (int, float))
                   or monotonic() - record["observed_at"] > STATUS_STALE_AFTER):
        return {**summary, "state": "unknown"}

    components = record.get("components")
    if not isinstance(components, dict) or not components:
        return {**summary, "state": "unknown"} if active else summary
    states = [value.get("state") for value in components.values() if isinstance(value, dict)]
    if len(states) != len(components) or any(state not in ("starting", "recording", "failed") for state in states):
        return {**summary, "state": "unknown"} if active else summary
    if not active:
        stopped_components = {
            name: detail if detail["state"] == "failed" else
                  {**detail, "state": "stopped", "reason": "parent service failed"}
            for name, detail in components.items()
        }
        return {"state": "failed", "session": record.get("session"), "components": stopped_components}
    if all(state == "failed" for state in states):
        state = "failed"
    elif any(state == "failed" for state in states):
        state = "partial_failure"
    elif any(state == "starting" for state in states):
        state = "starting"
    else:
        state = "recording"
    return {"state": state, "session": record.get("session"), "components": components}


def main() -> None:
    parser = argparse.ArgumentParser(description="Report systemd and recorder component health as JSON")
    parser.add_argument("--unit", default="mavrs")
    args = parser.parse_args()
    print(json.dumps(get_status(args.unit)))


if __name__ == "__main__":
    main()
