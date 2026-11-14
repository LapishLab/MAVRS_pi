import json
import tempfile
import unittest
from pathlib import Path

from transfer_cleanup import delete_selected, inventory


class TransferCleanupTests(unittest.TestCase):
    def test_inventory_and_delete_ignore_hidden_files_and_changed_sources(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            session = root / "session"
            session.mkdir()
            (session / "ready.wav").write_bytes(b"ready")
            (session / "changed.wav").write_bytes(b"old")
            (session / ".hidden").write_bytes(b"secret")
            hidden_dir = root / ".hidden_dir"
            hidden_dir.mkdir()
            (hidden_dir / "file").write_bytes(b"secret")
            (root / "empty").mkdir()

            rows = inventory(root)
            self.assertEqual({row[0] for row in rows},
                             {"session/ready.wav", "session/changed.wav"})
            (session / "changed.wav").write_bytes(b"newer contents")

            self.assertEqual(delete_selected(rows, root), 1)
            self.assertFalse((session / "ready.wav").exists())
            self.assertTrue((session / "changed.wav").exists())
            self.assertTrue((session / ".hidden").exists())
            self.assertTrue((hidden_dir / "file").exists())
            self.assertFalse((root / "empty").exists())


if __name__ == "__main__":
    unittest.main()
