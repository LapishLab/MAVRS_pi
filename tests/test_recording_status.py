import json
import unittest
from unittest.mock import Mock, patch

import recording_status


class RecordingStatusTests(unittest.TestCase):
    def setUp(self):
        self.path = Mock()
        self.path_patch = patch("recording_status.status_path", return_value=self.path)
        self.path_patch.start()
        self.addCleanup(self.path_patch.stop)

    def write_record(self, pid=123, invocation="current", components=None):
        self.path.read_text.return_value = json.dumps({
            "pid": pid, "invocation_id": invocation, "session": "session-one",
            "observed_at": recording_status.monotonic(),
            "components": components or {
                "Video": {"state": "failed", "exit_code": 1},
                "Audio": {"state": "recording", "exit_code": None},
            },
        })

    def test_partial_failure_and_stale_run(self):
        self.write_record()
        properties = {"ActiveState": "active", "Result": "success", "MainPID": "123",
                      "InvocationID": "current"}
        with patch("recording_status.unit_properties", return_value=properties):
            report = recording_status.get_status()
            self.assertEqual(report["state"], "partial_failure")
            self.assertEqual(report["components"]["Video"]["exit_code"], 1)
            properties["InvocationID"] = "next"
            self.assertEqual(recording_status.get_status()["state"], "starting")

    def test_failed_unit_keeps_current_run_details(self):
        self.write_record(components={"Video": {"state": "failed", "exit_code": 1}})
        properties = {"ActiveState": "failed", "Result": "exit-code", "MainPID": "0",
                      "InvocationID": "current"}
        with patch("recording_status.unit_properties", return_value=properties):
            report = recording_status.get_status()
        self.assertEqual(report["state"], "failed")
        self.assertEqual(report["components"]["Video"]["state"], "failed")

    def test_stopped_unit_ignores_old_record(self):
        self.write_record()
        with patch("recording_status.unit_properties", return_value={
            "ActiveState": "inactive", "Result": "success", "MainPID": "0"
        }):
            self.assertEqual(recording_status.get_status()["components"], {})

    def test_stale_active_record_is_unknown(self):
        self.write_record()
        properties = {"ActiveState": "active", "Result": "success", "MainPID": "123",
                      "InvocationID": "current"}
        with patch("recording_status.unit_properties", return_value=properties), patch(
            "recording_status.monotonic", return_value=recording_status.monotonic() + 9
        ):
            self.assertEqual(recording_status.get_status()["state"], "unknown")

    def test_worker_exit_before_ready_and_timeout(self):
        exited = Mock(exitcode=2)
        waiting = Mock(exitcode=None)
        waiting.is_alive.return_value = True
        states = {"Video": {"state": "starting"}, "Audio": {"state": "starting"}}
        video_ready = Mock()
        video_ready.is_set.return_value = False
        audio_ready = Mock()
        audio_ready.is_set.return_value = False
        workers = {"Video": (exited, video_ready, 99), "Audio": (waiting, audio_ready, 0)}
        with patch("recording_status.monotonic", return_value=100):
            self.assertTrue(recording_status.refresh_worker_states(workers, states))
        self.assertEqual(states["Video"]["reason"], "exited before ready")
        self.assertEqual(states["Audio"]["reason"], "startup timed out")
        waiting.terminate.assert_called_once()
        waiting.kill.assert_called_once()


if __name__ == "__main__":
    unittest.main()
