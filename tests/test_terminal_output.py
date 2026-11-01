"""Terminal output: no crash on unencodable characters; optional emoji-free
output for screen readers (BUNKER_NO_EMOJI)."""
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBE = (
    "from main.TERMINAL import setup_output\n"
    "setup_output()\n"
    "print('\\U0001F512 Locked | \\u2B50 Fav |   )    (  |\\u2554\\u2550\\u2557')\n"
)


def run(env_extra, code=PROBE):
    env = {k: v for k, v in os.environ.items() if k not in ("BUNKER_NO_EMOJI", "PYTHONIOENCODING")}
    env.update(env_extra)
    return subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env,
                          capture_output=True, timeout=60, stdin=subprocess.DEVNULL)


class TerminalOutput(unittest.TestCase):
    def test_ascii_terminal_does_not_crash(self):
        out = run({"PYTHONIOENCODING": "ascii"})
        self.assertEqual(out.returncode, 0, out.stderr.decode(errors="replace"))
        self.assertIn(b"Locked", out.stdout)

    def test_without_setup_ascii_terminal_would_crash(self):
        """Shows what setup_output prevents."""
        out = run({"PYTHONIOENCODING": "ascii"}, code="print('\\U0001F512 Locked')\n")
        self.assertNotEqual(out.returncode, 0)
        self.assertIn(b"UnicodeEncodeError", out.stderr)

    def test_emoji_kept_by_default(self):
        out = run({"PYTHONIOENCODING": "utf-8"})
        self.assertIn("\U0001F512".encode(), out.stdout)

    def test_no_emoji_strips_pictographs_but_keeps_layout(self):
        out = run({"PYTHONIOENCODING": "utf-8", "BUNKER_NO_EMOJI": "1"})
        text = out.stdout.decode("utf-8")
        self.assertNotIn("\U0001F512", text)
        self.assertNotIn("⭐", text)
        self.assertIn("Locked | Fav |   )    (  |", text)   # spacing untouched
        self.assertIn("╔═╗", text)            # box drawing kept


if __name__ == "__main__":
    unittest.main()
