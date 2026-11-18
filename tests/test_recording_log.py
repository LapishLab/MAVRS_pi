import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import recording_log


class RecordingLogTests(unittest.TestCase):
    def test_saves_settings_and_git_revision(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            user_settings = root / "mavrs_pi_config.yaml"
            user_settings.write_text("recordings:\n  audio: false\n")
            save_dir = root / "data" / "session" / "pi"

            with patch.object(recording_log, "USER_SETTINGS_FILE", user_settings), patch.object(
                recording_log, "run"
            ) as git_run:
                git_run.side_effect = [
                    unittest.mock.Mock(stdout="main\n"),
                    unittest.mock.Mock(stdout="abc123\n"),
                ]
                recording_log.write_recording_log(save_dir)

            log_dir = save_dir / "log"
            self.assertEqual((log_dir / user_settings.name).read_bytes(), user_settings.read_bytes())
            self.assertEqual((log_dir / "recording.log").read_text(), "Branch: main\nCommit: abc123\n")
            self.assertEqual(git_run.call_count, 2)
            for call in git_run.call_args_list:
                self.assertEqual(call.kwargs, {"check": True, "capture_output": True, "text": True})


if __name__ == "__main__":
    unittest.main()
