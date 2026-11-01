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

    def test_single_module_instance_under_both_names(self):
        import sys
        import SECURE_IO as top_level  # noqa: F401 (alias registered by module)
        self.assertIs(sys.modules["SECURE_IO"], sys.modules["main.SECURE_IO"])


if __name__ == "__main__":
    unittest.main()
