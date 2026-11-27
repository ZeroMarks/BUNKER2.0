"""A new vault makes no network connection: creating it, logging in on the
desktop and drawing both banners all work with every network call blocked,
and no lookup thread is started. The public IP display is off until the
user turns it on.
"""
import contextlib
import io
import os
import tempfile
import threading
import unittest
from unittest import mock

import main.DESKTOP as D
import main.SHARED_RESOURCES as S
import main.SHARED_RESOURCES_MOBILE as M

PASSWORD = "correct horse battery"


class NetworkTouched(AssertionError):
    pass


TOUCHED = []  # every blocked call, even one the app code catches


def _blocked(*_a, **_k):
    TOUCHED.append(_a)
    raise NetworkTouched("network was touched")


def quiet(*_a, **_k):
    return None


class OfflineByDefault(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)
        self.addCleanup(self._restore)
        S.stop_ip_fetch_thread()
        TOUCHED.clear()
        self.thread_errors = []
        self.ip_starts = []
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        for target in ("socket.socket.connect", "socket.socket.connect_ex",
                       "socket.create_connection", "socket.getaddrinfo",
                       "socket.gethostbyname", "socket.gethostbyname_ex"):
            self.stack.enter_context(mock.patch(target, side_effect=_blocked))
        self.stack.enter_context(mock.patch.object(S.requests, "get", side_effect=_blocked))
        self.stack.enter_context(mock.patch.object(S.subprocess, "check_output", side_effect=_blocked))
        self.stack.enter_context(mock.patch.object(S, "check_internet_connection", _blocked))
        self.stack.enter_context(mock.patch.object(S, "get_public_ipv4", _blocked))
        self.stack.enter_context(mock.patch.object(S, "get_external_ip", _blocked))
        self.stack.enter_context(mock.patch.object(D, "get_external_ip", _blocked))
        self.stack.enter_context(mock.patch.object(
            threading, "excepthook", lambda args: self.thread_errors.append(args.exc_value)))
        real_start = S.start_ip_fetch_thread
        self.stack.enter_context(mock.patch.object(
            S, "start_ip_fetch_thread",
            lambda: (self.ip_starts.append(1), real_start())))

    def _restore(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def lookup_threads(self):
        return [t for t in threading.enumerate() if t.name == S.IP_THREAD_NAME]

    def test_setup_then_desktop_login_with_the_network_blocked(self):
        out = io.StringIO()
        answers = iter(["y", "", "y", PASSWORD, PASSWORD, ""])
        with mock.patch("builtins.input", lambda *a, **k: next(answers)), \
             mock.patch.object(M, "setup_timeout", lambda *a, **k: 300), \
             mock.patch.object(M, "clear_screen", quiet), \
             mock.patch.object(M, "check_terminal_size", quiet), \
             mock.patch.object(M.time, "sleep", quiet), \
             contextlib.redirect_stdout(out):
            self.assertTrue(M.vaultSetup())
        self.assertIs(M.load_ui_config()["disable_ipv4"], True,
                      "a new vault must start with the public IP display off")

        reached = {}
        prompts = iter(["n"] * 10)
        with mock.patch("builtins.input", lambda *a, **k: next(prompts)), \
             mock.patch.object(D, "timeout_getpass", lambda *a, **k: PASSWORD), \
             mock.patch.object(D, "clear_screen", quiet), \
             mock.patch.object(D, "check_terminal_size", quiet), \
             mock.patch.object(D, "spinning_line", quiet), \
             mock.patch.object(D.time, "sleep", quiet), \
             mock.patch.object(D, "manage_passwords_and_notes",
                               lambda key: reached.setdefault("key", key)), \
             contextlib.redirect_stdout(out):
            # display_bunker is the real one here: the login banner is drawn.
            with self.assertRaises(SystemExit):
                D.main("desktop")
        self.assertIn("key", reached, "login never reached the main menu")
        self.assertIn("IP fetching disabled", out.getvalue())
        self.assertNotIn("INTERNET IP", out.getvalue())
        self.assertEqual(self.lookup_threads(), [])
        self.assertEqual(self.ip_starts, [], "the IP lookup thread was started")
        self.assertEqual(TOUCHED, [], "the network was touched (even if the error was caught)")
        self.assertEqual(self.thread_errors, [])

    def test_harness_catches_a_swallowed_touch(self):
        """Control: a network call that the app catches is still caught here."""
        self.assertEqual(S.local_ipv4() is not None, True)  # local, allowed
        try:
            S.requests.get("https://example.invalid")
        except NetworkTouched:
            pass
        self.assertEqual(len(TOUCHED), 1)


if __name__ == "__main__":
    unittest.main()
