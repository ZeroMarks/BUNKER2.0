"""The attempt that can destroy the vault is always announced first, and the
desktop and mobile interfaces count and warn the same way.

Real vaults (Argon2id + AES-GCM); only terminal I/O is faked.
"""
import contextlib
import io
import os
import tempfile
import unittest
from unittest import mock

import main.DESKTOP as D
import main.MOBILE as MB
import main.SHARED_RESOURCES_MOBILE as M
import main.VAULT_FILES as VF
from tests.test_vault_integrity import PASSWORD, quiet, run_setup

LAST = "LAST ATTEMPT"


def kinds(lines):
    return [k for k, _ in lines]


class Notice(unittest.TestCase):
    def test_counter_uses_the_configured_limit(self):
        self.assertEqual(VF.attempts_notice(1, 5, "ok", True),
                         [("info", "Failed attempts: 1 of 5")])
        self.assertNotIn("alert", kinds(VF.attempts_notice(3, 5, "ok", True)))
        self.assertIn("alert", kinds(VF.attempts_notice(4, 5, "ok", True)))

    def test_desktop_warns_before_the_destroying_attempt(self):
        for attempts in (0, 1):
            self.assertNotIn("alert", kinds(VF.attempts_notice(attempts, 3, "ok", True)))
        for attempts in (2, 3, 7):  # 3 and 7: counter carried over from mobile
            text = " ".join(t for _, t in VF.attempts_notice(attempts, 3, "ok", True))
            self.assertIn(LAST, text)
            self.assertIn("destroys", text)

    def test_mobile_warns_at_the_same_point_and_says_what_happens(self):
        self.assertEqual(kinds(VF.attempts_notice(1, 3, "ok", False)), ["info"])
        two = " ".join(t for _, t in VF.attempts_notice(2, 3, "ok", False))
        self.assertIn(LAST, two)
        self.assertIn("desktop", two)
        three = " ".join(t for _, t in VF.attempts_notice(3, 3, "ok", False))
        self.assertIn("never deletes", three)

    def test_no_destroy_warning_when_destroy_is_impossible(self):
        unknown = VF.attempts_notice(2, 3, "unknown", True)
        self.assertNotIn("alert", kinds(unknown))
        self.assertIn("Self-destruct is off", unknown[-1][1])
        interrupted = VF.attempts_notice(2, 3, "interrupted", True)
        self.assertEqual(kinds(interrupted), ["warn"])
        self.assertIn("not counted", interrupted[0][1])


class VaultCase(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)
        self.addCleanup(self._restore)
        self.assertTrue(run_setup())

    def _restore(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def set_attempts(self, n):
        cfg = M.load_ui_config()
        cfg["attempts"] = n
        M.save_ui_config(cfg)

    def attempts(self):
        return M.load_ui_config()["attempts"]


class DesktopLastAttempt(VaultCase):
    def login(self, passwords, answers):
        """Desktop login; records the screen text at each password prompt."""
        out = io.StringIO()
        pw = iter(passwords)
        ans = iter(answers)
        seen = {"destroyed": False, "menu": False, "screens": []}

        def password_prompt(*_a, **_k):
            seen["screens"].append(out.getvalue())
            return next(pw)

        def destroy():
            seen["destroyed"] = True
            raise SystemExit(9)

        def menu(_key):
            seen["menu"] = True

        with mock.patch("builtins.input", lambda *a, **k: next(ans)), \
             mock.patch.object(D, "timeout_getpass", password_prompt), \
             mock.patch.object(D, "clear_screen", quiet), \
             mock.patch.object(D, "check_terminal_size", quiet), \
             mock.patch.object(D, "spinning_line", quiet), \
             mock.patch.object(D, "display_bunker", quiet), \
             mock.patch.object(D.time, "sleep", quiet), \
             mock.patch.object(D, "self_destruct", destroy), \
             mock.patch.object(D, "manage_passwords_and_notes", menu), \
             contextlib.redirect_stdout(out):
            try:
                D.main("desktop")
            except SystemExit:
                pass
        return seen

    def test_warning_is_on_screen_before_the_third_password_is_typed(self):
        seen = self.login(["wrong one!", "wrong two!", "wrong three"],
                          ["n", "n", "last", "n"])
        self.assertNotIn(LAST, seen["screens"][1])
        # Printed after the second failure, before the third prompt.
        self.assertIn(LAST, seen["screens"][2][len(seen["screens"][1]):])
        self.assertTrue(seen["destroyed"])

    def test_counter_carried_over_from_mobile_is_shown_and_must_be_confirmed(self):
        self.set_attempts(3)  # three failures on mobile, vault intact
        seen = self.login([], [""])  # Enter at the confirmation
        self.assertFalse(seen["destroyed"])
        self.assertEqual(seen["screens"], [])  # never reached the password prompt
        self.assertEqual(self.attempts(), 3)  # nothing used or counted
        self.assertTrue(os.path.exists("Bunker.mmf"))

    def test_confirmed_last_attempt_with_the_right_password_logs_in(self):
        self.set_attempts(2)
        seen = self.login([PASSWORD], ["last", "n"])
        self.assertIn(LAST, seen["screens"][0])
        self.assertTrue(seen["menu"])
        self.assertFalse(seen["destroyed"])
        self.assertEqual(self.attempts(), 0)

    def test_no_confirmation_while_destroy_is_impossible(self):
        os.remove("bunker.chk")  # legacy vault: counted, never destroyed
        self.set_attempts(2)
        seen = self.login([PASSWORD], ["n"])
        self.assertTrue(seen["menu"])


class MobileSharesTheCounter(VaultCase):
    def login(self, passwords):
        out = io.StringIO()
        pw = iter(passwords)
        seen = {"menu": False}

        def answer(prompt="", *_a, **_k):
            if "Select option" in prompt:
                seen["menu"] = True
                return "0"
            return "n"

        with mock.patch("builtins.input", answer), \
             mock.patch.object(MB, "timeout_getpass", lambda *a, **k: next(pw)), \
             mock.patch.object(MB, "clear_screen", quiet), \
             mock.patch.object(MB.time, "sleep", quiet), \
             contextlib.redirect_stdout(out):
            try:
                MB.main("mobile")
            except (SystemExit, StopIteration):
                pass
        return seen, out.getvalue()

    def test_correct_password_still_works_at_the_limit(self):
        """Used to refuse even the right password once the shared counter
        reached the limit, which locked mobile users out for good."""
        self.set_attempts(3)
        seen, screen = self.login([PASSWORD])
        self.assertTrue(seen["menu"])
        self.assertIn("Failed attempts: 3 of 3", screen)
        self.assertEqual(self.attempts(), 0)

    def test_wrong_password_at_the_limit_is_counted_and_destroys_nothing(self):
        self.set_attempts(3)
        seen, _ = self.login(["not it at all"])
        self.assertFalse(seen["menu"])
        self.assertEqual(self.attempts(), 4)
        self.assertTrue(os.path.exists("Bunker.mmf"))

    def test_last_attempt_warning_matches_the_desktop(self):
        self.set_attempts(2)
        _, screen = self.login(["not it at all"])
        self.assertIn("Failed attempts: 2 of 3", screen)
        self.assertIn(LAST, screen)
        self.assertEqual(self.attempts(), 3)


if __name__ == "__main__":
    unittest.main()
