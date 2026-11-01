"""First run, end to end: create a vault with setup, then log in on desktop.

Uses the real key derivation and encryption; only terminal I/O is faked.
"""
import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import main.DESKTOP as D
import main.SHARED_RESOURCES_MOBILE as M

PASSWORD = "correct horse battery"


def quiet(*_a, **_k):
    return None


class FirstRun(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)
        self.addCleanup(self._restore)
        answers = iter(["y", "y", PASSWORD, PASSWORD, ""])
        with mock.patch("builtins.input", lambda *a, **k: next(answers)), \
             mock.patch.object(M, "setup_timeout", lambda *a, **k: 300), \
             mock.patch.object(M, "clear_screen", quiet), \
             mock.patch.object(M, "check_terminal_size", quiet), \
             mock.patch.object(M.time, "sleep", quiet), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(M.vaultSetup())

    def _restore(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def _login(self, password):
        reached = {}
        prompts = iter(["n"] * 10)
        patches = [
            mock.patch("builtins.input", lambda *a, **k: next(prompts)),
            mock.patch.object(D, "timeout_getpass", lambda *a, **k: password),
            mock.patch.object(D, "clear_screen", quiet),
            mock.patch.object(D, "check_terminal_size", quiet),
            mock.patch.object(D, "spinning_line", quiet),
            mock.patch.object(D, "display_bunker", quiet),
            mock.patch.object(D.time, "sleep", quiet),
            mock.patch.object(D, "self_destruct", lambda: (_ for _ in ()).throw(SystemExit(9))),
            mock.patch.object(D, "manage_passwords_and_notes",
                              lambda key: reached.setdefault("key", key)),
        ]
        with contextlib.ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            with self.assertRaises(SystemExit):
                D.main("desktop")
        return reached

    def test_setup_writes_every_file_login_needs(self):
        for name in ("Bunker.mmf", "bunker.salt", "bunker.cfg", "config.cfg"):
            self.assertTrue(Path(name).exists(), name)
            if os.name != "nt":
                self.assertEqual(os.stat(name).st_mode & 0o777, 0o600, name)

    def test_correct_password_opens_the_new_vault(self):
        reached = self._login(PASSWORD)
        self.assertIn("key", reached, "login never reached the main menu")
        self.assertEqual(D.loadDatabase(reached["key"]), {})

    def test_wrong_password_counts_one_attempt_and_keeps_vault(self):
        before = {n: Path(n).read_bytes() for n in ("Bunker.mmf", "bunker.salt", "bunker.cfg")}
        prompts = iter(["n", "e"])  # one wrong try, then exit
        with mock.patch("builtins.input", lambda *a, **k: next(prompts)), \
             mock.patch.object(D, "timeout_getpass", lambda *a, **k: "wrong password"), \
             mock.patch.object(D, "clear_screen", quiet), \
             mock.patch.object(D, "check_terminal_size", quiet), \
             mock.patch.object(D, "spinning_line", quiet), \
             mock.patch.object(D, "display_bunker", quiet), \
             mock.patch.object(D.time, "sleep", quiet), \
             contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):
                D.main("desktop")
        self.assertEqual(M.load_ui_config()["attempts"], 1)
        for name, data in before.items():
            self.assertEqual(Path(name).read_bytes(), data, name)


if __name__ == "__main__":
    unittest.main()
