import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from utilities import get_settings


class SettingsTests(unittest.TestCase):
    def test_user_settings_override_nested_values_and_keep_defaults(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            default_file = root / "default_settings.yaml"
            user_file = root / "mavrs_pi_config.yaml"
            default_file.write_text(
                "camera:\n"
                "  sensor_mode: HDR\n"
                "  autofocus: false\n"
                "  quality: MEDIUM\n"
                "recordings:\n"
                "  video: true\n"
                "  audio: true\n"
            )
            user_file.write_text(
                "camera:\n"
                "  autofocus: true\n"
            )

            with patch("utilities.DEFAULT_SETTINGS_FILE", default_file), patch(
                "utilities.USER_SETTINGS_FILE", user_file
            ):
                settings = get_settings()

        self.assertEqual(
            settings,
            {
                "camera": {
                    "sensor_mode": "HDR",
                    "autofocus": True,
                    "quality": "MEDIUM",
                },
                "recordings": {"video": True, "audio": True},
            },
        )


if __name__ == "__main__":
    unittest.main()
