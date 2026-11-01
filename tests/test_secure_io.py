"""Tests for main/SECURE_IO.py: clipboard clearing, reveal, error scrubbing."""
import io
import time
import unittest

from main import SECURE_IO


class FakeClipboard:
    def __init__(self):
        self.value = ""
        self.fail_paste = False

    def copy(self, text):
        self.value = text

    def paste(self):
        if self.fail_paste:
            raise RuntimeError("no clipboard")
        return self.value


class ClipboardTests(unittest.TestCase):
    def setUp(self):
        self.cb = FakeClipboard()
        SECURE_IO.set_clipboard_backend(self.cb.copy, self.cb.paste)

    def tearDown(self):
        SECURE_IO.clear_clipboard_if_ours()
        SECURE_IO.set_clipboard_backend(None, None)

    def test_secret_is_cleared_after_timeout(self):
        self.assertTrue(SECURE_IO.copy_secret("hunter2!", timeout=0.05))
        self.assertEqual(self.cb.value, "hunter2!")
        time.sleep(0.3)
        self.assertEqual(self.cb.value, "")
        self.assertFalse(SECURE_IO.has_pending_secret())

    def test_user_copy_after_secret_is_not_wiped(self):
        SECURE_IO.copy_secret("hunter2!", timeout=0.05)
        self.cb.copy("something the user copied")
        time.sleep(0.3)
        self.assertEqual(self.cb.value, "something the user copied")

    def test_new_copy_replaces_old_timer(self):
        SECURE_IO.copy_secret("first", timeout=0.05)
        SECURE_IO.copy_secret("second", timeout=5)
        time.sleep(0.3)
        self.assertEqual(self.cb.value, "second")
        self.assertTrue(SECURE_IO.clear_clipboard_if_ours())
        self.assertEqual(self.cb.value, "")

    def test_exit_clear_wipes_pending_secret(self):
        SECURE_IO.copy_secret("hunter2!", timeout=60)
        self.assertTrue(SECURE_IO.clear_clipboard_if_ours())
        self.assertEqual(self.cb.value, "")

    def test_unreadable_clipboard_fails_closed(self):
        SECURE_IO.copy_secret("hunter2!", timeout=60)
        self.cb.fail_paste = True
        self.assertTrue(SECURE_IO.clear_clipboard_if_ours())
        self.assertEqual(self.cb.value, "")

    def test_copy_failure_returns_false_without_raising(self):
        def broken(_):
            raise RuntimeError("hunter2!")
        SECURE_IO.set_clipboard_backend(broken, self.cb.paste)
        self.assertFalse(SECURE_IO.copy_secret("hunter2!"))
        self.assertFalse(SECURE_IO.has_pending_secret())

    def test_notice_does_not_contain_secret(self):
        self.assertNotIn("hunter2!", SECURE_IO.copy_notice("Password"))


class OutputTests(unittest.TestCase):
    def test_reveal_writes_only_to_given_stream(self):
        buf = io.StringIO()
        SECURE_IO.reveal_secret("Password: ", "hunter2!", out=buf)
        self.assertEqual(buf.getvalue(), "Password: hunter2!\n")

    def test_mask_hides_value_and_length(self):
        self.assertEqual(SECURE_IO.mask("a"), SECURE_IO.mask("a much longer secret"))
        self.assertNotIn("hunter2", SECURE_IO.mask("hunter2"))

    def test_safe_error_drops_message(self):
        try:
            b"hunter2\xff".decode("utf-8")
        except UnicodeDecodeError as e:
            self.assertEqual(SECURE_IO.safe_error(e), "UnicodeDecodeError")
        self.assertEqual(SECURE_IO.safe_error(ValueError("secret=hunter2")), "ValueError")

    def test_safe_error_keeps_os_reason(self):
        err = PermissionError(13, "Permission denied", "/vault/hunter2")
        self.assertEqual(SECURE_IO.safe_error(err), "PermissionError: Permission denied")

    def test_stale_timer_does_not_clear_newer_copy(self):
        cb = FakeClipboard()
        SECURE_IO.set_clipboard_backend(cb.copy, cb.paste)
        try:
            SECURE_IO.copy_secret("first", timeout=60)
            stale = SECURE_IO._generation
            SECURE_IO.copy_secret("second", timeout=60)
            self.assertFalse(SECURE_IO._timer_fired(stale))
            self.assertEqual(cb.value, "second")
            self.assertTrue(SECURE_IO.has_pending_secret())
        finally:
            SECURE_IO.clear_clipboard_if_ours()
            SECURE_IO.set_clipboard_backend(None, None)

    def test_line_ending_changes_still_match(self):
        cb = FakeClipboard()
        SECURE_IO.set_clipboard_backend(cb.copy, cb.paste)
        try:
            SECURE_IO.copy_secret("line one\nline two\n", timeout=60)
            cb.value = "line one\r\nline two"  # what some backends return
            self.assertTrue(SECURE_IO.clear_clipboard_if_ours())
            self.assertEqual(cb.value, "")
        finally:
            SECURE_IO.set_clipboard_backend(None, None)

    def test_fingerprint_set_before_copy(self):
        seen = {}
        def copy(text):
            seen["pending"] = SECURE_IO.has_pending_secret()
        SECURE_IO.set_clipboard_backend(copy, lambda: "")
        try:
            SECURE_IO.copy_secret("hunter2!", timeout=60)
            self.assertTrue(seen["pending"])
        finally:
            SECURE_IO.clear_clipboard_if_ours()
            SECURE_IO.set_clipboard_backend(None, None)

class OpenPrivateTests(unittest.TestCase):
    def test_export_file_is_owner_only(self):
        import os, stat, tempfile
        if os.name == "nt":
            self.skipTest("POSIX permissions only")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "export.json")
            with open(path, "w") as f:      # pre-existing, default mode
                f.write("old")
            os.chmod(path, 0o644)
            with SECURE_IO.open_private(path) as f:
                f.write("{}")
            self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
            with open(path) as f:
                self.assertEqual(f.read(), "{}")


class SignalTests(unittest.TestCase):
    def test_sigterm_clears_clipboard_before_exit(self):
        import os, signal, subprocess, sys, tempfile
        if not hasattr(signal, "SIGTERM") or os.name == "nt":
            self.skipTest("POSIX only")
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with tempfile.TemporaryDirectory() as tmp:
            box = os.path.join(tmp, "clipboard")
            child = (
                "import os, signal, time\n"
                "from main import SECURE_IO\n"
                f"box = {box!r}\n"
                "def copy(t):\n"
                "    open(box, 'w').write(t)\n"
                "def paste():\n"
                "    return open(box).read()\n"
                "SECURE_IO.set_clipboard_backend(copy, paste)\n"
                "assert 'SIGTERM' in SECURE_IO.install_exit_signal_handlers()\n"
                "SECURE_IO.copy_secret('hunter2!', timeout=60)\n"
                "os.kill(os.getpid(), signal.SIGTERM)\n"
                "time.sleep(5)\n"
            )
            proc = subprocess.run([sys.executable, "-c", child], cwd=root, timeout=20)
            self.assertEqual(proc.returncode, -signal.SIGTERM)
            with open(box) as f:
                self.assertEqual(f.read(), "")


if __name__ == "__main__":
    unittest.main()
