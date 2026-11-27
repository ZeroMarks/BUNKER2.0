"""Mobile interface messages: an error waits for Enter instead of vanishing
after one second, and "Error:" / "Done:" say what happened in words, so the
meaning does not depend on colour or on a symbol."""
import contextlib
import io
import unittest
from unittest import mock

import main.MOBILE as MB
from tests.test_login_attempts import PASSWORD, VaultCase
from tests.test_vault_integrity import quiet


class Messages(unittest.TestCase):
    def show(self, method, text):
        asked, slept = [], []
        out = io.StringIO()
        with mock.patch.object(MB, "timeoutInput", lambda p, t=None: asked.append((p, t))), \
             mock.patch.object(MB.time, "sleep", slept.append), \
             contextlib.redirect_stdout(out):
            getattr(MB.ModernUI, method)(text)
        return out.getvalue(), asked, slept

    def test_error_waits_for_enter(self):
        screen, asked, slept = self.show("error_message", "Invalid option")
        self.assertIn("Error: Invalid option", screen)
        self.assertEqual(len(asked), 1)
        self.assertIn("Press Enter to continue", asked[0][0])
        self.assertEqual(slept, [])

    def test_error_pause_still_logs_out_when_idle(self):
        with mock.patch.object(MB.ModernUI, "pause_timeout", 45):
            _, asked, _ = self.show("error_message", "x")
        self.assertEqual(asked[0][1], 45)

    def test_success_is_named_and_does_not_block(self):
        screen, asked, slept = self.show("success_message", "Note added successfully")
        self.assertIn("Done: Note added successfully", screen)
        self.assertEqual(asked, [])
        self.assertEqual(slept, [1])

    def test_farewell_is_not_called_done(self):
        screen, asked, _ = self.show("farewell", "Goodbye!")
        self.assertIn("Goodbye!", screen)
        self.assertNotIn("Done:", screen)
        self.assertEqual(asked, [])


class WrongPasswordAtLogin(VaultCase):
    def test_the_error_is_held_until_enter_before_the_next_prompt(self):
        events = []
        passwords = iter(["wrong-password", PASSWORD])

        def answer(prompt="", *_a, **_k):
            if "Press Enter to continue" in prompt:
                events.append("pause")
                return ""
            if "Select option" in prompt:
                events.append("menu")
                return "0"
            return "n"

        def password(*_a, **_k):
            events.append("password")
            return next(passwords)

        out = io.StringIO()
        with mock.patch("builtins.input", answer), \
             mock.patch.object(MB, "timeout_getpass", password), \
             mock.patch.object(MB, "clear_screen", quiet), \
             mock.patch.object(MB.time, "sleep", quiet), \
             contextlib.redirect_stdout(out):
            try:
                MB.main("mobile")
            except SystemExit:
                pass
        self.assertIn("Error: Incorrect access password.", out.getvalue())
        self.assertEqual(events, ["password", "pause", "password", "menu"])


if __name__ == "__main__":
    unittest.main()
