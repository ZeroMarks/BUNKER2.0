"""Auto-logout "off" (a timeout of 0) must not lock the user out.

Setup and the settings screen both accept 0 for "no auto-logout". The
prompt helpers used to wait 0 seconds for input and then log out, before
anything could be typed: on the desktop's "show password" path and on both
mobile login paths. Real vault; terminal I/O is faked with a typist who
needs a moment, like a person does.
"""
import contextlib
import io
import os
import tempfile
import time
import unittest
from unittest import mock

import main.DESKTOP as D
import main.MOBILE as MB
import main.SHARED_RESOURCES_MOBILE as M
from tests.test_vault_integrity import PASSWORD, quiet, run_setup


# The flows below silence the UI's own pauses by patching time.sleep; the
# typist must still take real time, or every prompt would look instant.
_typing_pause = time.sleep


class LoggedOut(BaseException):
    pass


def slow(value):
    def typist(*_a, **_k):
        _typing_pause(0.05)
        return value
    return typist


class Helpers(unittest.TestCase):
    def test_zero_or_less_or_none_waits_for_the_user(self):
        for timeout in (0, -5, None):
            with self.subTest(timeout=timeout), \
                 mock.patch("builtins.input", slow("typed")), \
                 mock.patch.object(M.getpass, "getpass", slow("secret")), \
                 mock.patch.object(M, "timeoutCleanup", side_effect=LoggedOut):
                self.assertEqual(M.timeoutInput("p: ", timeout), "typed")
                self.assertEqual(M.timeout_getpass("p: ", timeout), "secret")

    def test_a_real_timeout_still_logs_out(self):
        with mock.patch("builtins.input", slow("late")), \
             mock.patch.object(M, "timeoutCleanup", side_effect=LoggedOut):
            with self.assertRaises(LoggedOut):
                M.timeoutInput("p: ", 0.01)

    def test_end_of_input_is_not_an_answer(self):
        with mock.patch("builtins.input", side_effect=EOFError):
            self.assertIsNone(M.timeoutInput("p: ", 0))


class LoginWithAutoLogoutOff(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)
        self.addCleanup(self._restore)
        self.assertTrue(run_setup(timeout=0))
        self.assertEqual(M.load_ui_config()["current_timeout"], 0)

    def _restore(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def test_desktop_show_password_path(self):
        reached = []
        answers = iter(["y"])

        def answer(prompt="", *_a, **_k):
            if "access code" in prompt:
                _typing_pause(0.05)
                return PASSWORD
            return next(answers)

        with mock.patch("builtins.input", answer), \
             mock.patch.object(M, "timeoutCleanup", side_effect=LoggedOut), \
             mock.patch.object(D, "timeoutCleanup", side_effect=LoggedOut), \
             mock.patch.object(D, "clear_screen", quiet), \
             mock.patch.object(D, "check_terminal_size", quiet), \
             mock.patch.object(D, "spinning_line", quiet), \
             mock.patch.object(D, "display_bunker", quiet), \
             mock.patch.object(D.time, "sleep", quiet), \
             mock.patch.object(D, "manage_passwords_and_notes", reached.append), \
             contextlib.redirect_stdout(io.StringIO()):
            try:
                D.main("desktop")
            except SystemExit:
                pass  # normal exit after the menu returns
        self.assertEqual(len(reached), 1)

    def _mobile(self, show):
        seen = {"menu": False}

        def answer(prompt="", *_a, **_k):
            if "access code" in prompt:
                _typing_pause(0.05)
                return PASSWORD
            if "Select option" in prompt:
                seen["menu"] = True
                return "0"
            return show

        with mock.patch("builtins.input", answer), \
             mock.patch.object(M.getpass, "getpass", answer), \
             mock.patch.object(M, "timeoutCleanup", side_effect=LoggedOut), \
             mock.patch.object(MB, "timeoutCleanup", side_effect=LoggedOut), \
             mock.patch.object(MB, "clear_screen", quiet), \
             mock.patch.object(MB.time, "sleep", quiet), \
             contextlib.redirect_stdout(io.StringIO()):
            MB.main("mobile")
        return seen["menu"]

    def test_mobile_hidden_password(self):
        self.assertTrue(self._mobile("n"))

    def test_mobile_shown_password(self):
        self.assertTrue(self._mobile("y"))


if __name__ == "__main__":
    unittest.main()
