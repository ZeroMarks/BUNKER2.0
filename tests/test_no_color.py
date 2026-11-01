"""NO_COLOR (https://no-color.org): no ANSI colour codes when it is set."""
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBE = (
    "from main import SHARED_RESOURCES as S, SHARED_RESOURCES_MOBILE as M\n"
    "import main.DESKTOP as D\n"
    "text = S.RED + S.GOLD + S.nuke_art + S.title_art + M.CYAN + D.RESET\n"
    "print('COLOR' if '\\x1b[' in text else 'PLAIN')\n"
)


def probe(env_extra):
    env = {k: v for k, v in os.environ.items() if k != "NO_COLOR"}
    env.update(env_extra)
    out = subprocess.run([sys.executable, "-c", PROBE], cwd=ROOT, env=env,
                         capture_output=True, text=True, timeout=60,
                         stdin=subprocess.DEVNULL)
    return out.stdout.strip().splitlines()[-1]


class NoColor(unittest.TestCase):
    def test_colours_by_default(self):
        self.assertEqual(probe({}), "COLOR")

    def test_no_color_set_removes_colours(self):
        self.assertEqual(probe({"NO_COLOR": "1"}), "PLAIN")

    def test_empty_no_color_is_ignored(self):
        self.assertEqual(probe({"NO_COLOR": ""}), "COLOR")


if __name__ == "__main__":
    unittest.main()
