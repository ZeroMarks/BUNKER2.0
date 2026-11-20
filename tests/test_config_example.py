"""config.example documents config.cfg truthfully.

config.cfg is created on first run and is tied to the machine and vault, so
it is git-ignored and not shipped; config.example describes it instead.
These tests keep the two in step: same keys, same defaults.
"""
import json
import os
import re
import tempfile
import unittest
from pathlib import Path

import main.SHARED_RESOURCES_MOBILE as M

ROOT = Path(__file__).resolve().parent.parent


def documented_defaults():
    text = (ROOT / "config.example").read_text(encoding="utf-8")
    pairs = re.findall(r'^#\s+"(\w+)":\s*([^,\s]+)', text, flags=re.M)
    return {k: json.loads(v) for k, v in pairs}


class ConfigExample(unittest.TestCase):
    def test_lists_every_setting_with_its_real_default(self):
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                defaults = M.load_ui_config()  # no config.cfg: creates defaults
            finally:
                os.chdir(cwd)
        self.assertEqual(documented_defaults(), defaults)

    def test_config_cfg_is_ignored_and_the_example_is_not(self):
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn("config.cfg", ignored)
        self.assertNotIn("config.example", ignored)


if __name__ == "__main__":
    unittest.main()
