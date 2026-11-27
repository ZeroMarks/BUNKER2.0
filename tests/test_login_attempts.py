"""The attempt that can destroy the vault is always announced first, and the
desktop and mobile interfaces count, warn and enforce the limit the same way.

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
import main.SHARED_RESOURCES as SR
import main.SHARED_RESOURCES_MOBILE as M
import main.VAULT_FILES as VF
from tests.test_vault_integrity import PASSWORD, quiet, run_setup

LAST = "LAST ATTEMPT"


def kinds(lines):
    return [k for k, _ in lines]


class Notice(unittest.TestCase):
    def test_counter_uses_the_configured_limit(self):
        self.assertEqual(VF.attempts_notice(1, 5, "ok"),
                         [("info", "Failed attempts: 1 of 5")])
        self.assertNotIn("alert", kinds(VF.attempts_notice(3, 5, "ok")))
        self.assertIn("alert", kinds(VF.attempts_notice(4, 5, "ok")))

    def test_desktop_warns_before_the_destroying_attempt(self):
        for attempts in (0, 1):
            self.assertNotIn("alert", kinds(VF.attempts_notice(attempts, 3, "ok")))
        for attempts in (2, 3, 7):  # 3 and 7: counter carried over from mobile
            text = " ".join(t for _, t in VF.attempts_notice(attempts, 3, "ok"))
            self.assertIn(LAST, text)
            self.assertIn("destroys", text)

    def test_no_destroy_warning_when_destroy_is_impossible(self):
        unknown = VF.attempts_notice(2, 3, "unknown")
        self.assertNotIn("alert", kinds(unknown))
        self.assertIn("Self-destruct is off", unknown[-1][1])
        interrupted = VF.attempts_notice(2, 3, "interrupted")
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
    """Mobile applies the attempt limit exactly as the desktop does: same
    counter, same LAST confirmation, same self-destruct on verified files."""

    def login(self, passwords, confirm=()):
        """Mobile login. ``confirm`` answers the "Type LAST" prompts in order
        (Enter once they run out). Returns (seen, screen)."""
        out = io.StringIO()
        pw = iter(passwords)
        conf = iter(confirm)
        seen = {"menu": False, "destroyed": False, "prompts": 0, "confirms": 0}

        def answer(prompt="", *_a, **_k):
            if "Select option" in prompt:
                seen["menu"] = True
                return "0"
            if "LAST" in prompt:
                seen["confirms"] += 1
                return next(conf, "")
            return "n"

        def password_prompt(*_a, **_k):
            seen["prompts"] += 1
            return next(pw)

        def destroy():
            seen["destroyed"] = True
            raise SystemExit(9)

        with mock.patch("builtins.input", answer), \
             mock.patch.object(MB, "timeout_getpass", password_prompt), \
             mock.patch.object(MB, "clear_screen", quiet), \
             mock.patch.object(MB.time, "sleep", quiet), \
             mock.patch.object(SR, "self_destruct", destroy), \
             contextlib.redirect_stdout(out):
            try:
                MB.main("mobile")
            except (SystemExit, StopIteration):
                pass
        return seen, out.getvalue()

    def test_no_free_guess_per_launch_past_the_limit(self):
        """Used to allow one checked guess per launch at the limit, so
        relaunching in the mobile view gave unlimited guesses."""
        self.set_attempts(3)
        for i in range(5):
            seen, _ = self.login([f"guess {i}"])  # Enter at the LAST prompt
            self.assertEqual(seen["prompts"], 0, "password prompt reached past the limit")
            self.assertFalse(seen["menu"])
        self.assertEqual(self.attempts(), 3)
        self.assertTrue(os.path.exists("Bunker.mmf"))

    def test_confirmed_wrong_password_at_the_limit_self_destructs(self):
        self.set_attempts(3)  # e.g. three failures on the desktop
        seen, screen = self.login(["not it at all"], confirm=["LAST"])
        self.assertIn("Failed attempts: 3 of 3", screen)
        self.assertTrue(seen["destroyed"])
        self.assertFalse(seen["menu"])

    def test_correct_password_works_at_the_limit_once_confirmed(self):
        self.set_attempts(3)
        seen, screen = self.login([PASSWORD], confirm=["last"])
        self.assertIn(LAST, screen)
        self.assertTrue(seen["menu"])
        self.assertFalse(seen["destroyed"])
        self.assertEqual(self.attempts(), 0)

    def test_last_attempt_warning_and_destroy_match_the_desktop(self):
        self.set_attempts(2)
        seen, screen = self.login(["not it at all"], confirm=["LAST"])
        self.assertIn("Failed attempts: 2 of 3", screen)
        self.assertIn(LAST, screen)
        self.assertIn("destroys", screen)
        self.assertTrue(seen["destroyed"])

    def test_three_wrong_passwords_in_one_launch_self_destruct(self):
        seen, _ = self.login(["wrong one!", "wrong two!", "wrong three"], confirm=["LAST"])
        self.assertEqual(seen["prompts"], 3)
        self.assertEqual(seen["confirms"], 1)  # asked once, before the third
        self.assertTrue(seen["destroyed"])

    def test_limit_on_unverified_files_exits_without_destroying(self):
        os.remove("bunker.chk")  # legacy vault: counted, never destroyed
        seen, _ = self.login(["wrong one!", "wrong two!", "wrong three"])
        self.assertEqual(seen["confirms"], 0)
        self.assertFalse(seen["destroyed"])
        self.assertEqual(self.attempts(), 3)
        self.assertTrue(os.path.exists("Bunker.mmf"))


if __name__ == "__main__":
    unittest.main()
