"""The mobile login handles an interrupted master password change the same
way the desktop login does.

Same method as test_interrupted_password_change: a real password change
(Argon2id + AES-GCM) runs in a child process and is killed right after each
file write or removal in turn. Then the mobile interface is used to log in,
with nothing mocked but terminal I/O:

* a wrong password is never counted while the change is unfinished, and the
  screen says the change did not finish;
* a password that opens both bunker.cfg and Bunker.mmf reaches the menu and
  finishes the change: the files are a verified set again and the *.prev
  copies are gone;
* a password that opens only bunker.cfg (the mixed middle of a change) is
  told to put the *.prev files back, and those files are still there.

Mobile never destroys the vault; that is checked on every case as well.
"""
import contextlib
import io
import os
import shutil
import unittest
from pathlib import Path
from unittest import mock

import main.DESKTOP as D
import main.INITIALIZE as I
import main.MOBILE as MB
import main.SHARED_RESOURCES_MOBILE as M
import main.VAULT_FILES as VF
import tests.test_interrupted_password_change as base
from tests.test_vault_integrity import NEW_PASSWORD, PASSWORD, key_for, quiet

NOT_FINISHED = "A master password change did not finish"
PUT_BACK = "Put the *.prev files back"


def mobile_login(passwords):
    """Start the mobile interface and type ``passwords`` in turn. Returns
    (reached_menu, screen text)."""
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
    return seen["menu"], out.getvalue()


class MobileLoginAfterAnInterruptedChange(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base.InterruptedPasswordChange.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        base.InterruptedPasswordChange.tearDownClass.__func__(cls)

    def setUp(self):
        base.InterruptedPasswordChange.setUp(self)

    _fully_opens = staticmethod(base.InterruptedPasswordChange._fully_opens)

    def fresh_copy_killed_after(self, k):
        os.chdir(self._cwd)  # Windows cannot remove the current folder
        shutil.rmtree(self.dir)
        shutil.copytree(self._template, self.dir)
        os.chdir(self.dir)
        run = base._child(k, self.dir)
        self.assertEqual(run.returncode, 0, run.stderr)

    def assert_reads_back(self, password):
        key = key_for(password)
        with contextlib.redirect_stdout(io.StringIO()):
            entry = I.loadDatabase(key)["p1"]
        self.assertEqual(D.decode_and_decrypt("password", entry, key), base.SECRET)

    def test_killed_after_every_step(self):
        outcomes = set()
        for k in range(1, len(self.steps)):  # the last step is a finished change
            with self.subTest(killed_after=self.steps[k - 1]):
                self.fresh_copy_killed_after(k)
                self.assertEqual(VF.integrity_status(), "interrupted")
                copies_before = VF.recovery_copies()

                if self.steps[k - 1] == "write:bunker.salt":
                    # Killed between the new salt and the settings file that
                    # is keyed to it: BUNKER stops before the login screen
                    # and changes nothing. docs/RECOVERY.md: delete
                    # config.cfg and BUNKER makes a fresh one.
                    menu, screen = mobile_login([PASSWORD])
                    self.assertFalse(menu)
                    self.assertIn("UI config file missing or corrupted", screen)
                    self.assertEqual(VF.recovery_copies(), copies_before)
                    os.remove("config.cfg")

                # A password that is neither: told the change did not finish,
                # not counted, nothing removed.
                menu, screen = mobile_login(["not either password"])
                self.assertFalse(menu)
                self.assertIn(NOT_FINISHED, screen)
                self.assertIn("Not counted", screen)
                self.assertEqual(M.load_ui_config()["attempts"], 0)
                self.assertEqual(VF.recovery_copies(), copies_before)
                self.assertEqual(VF.integrity_status(), "interrupted")

                opens = [p for p in (NEW_PASSWORD, PASSWORD) if self._fully_opens(p)]
                cfg_only = [p for p in (NEW_PASSWORD, PASSWORD)
                            if p not in opens and VF.try_password(p, I.vault)[0] == "ok"]

                # Opens the config but not the database: must not reach the
                # menu, must say how to recover, must keep the copies.
                for password in cfg_only:
                    menu, screen = mobile_login([password])
                    self.assertFalse(menu, "menu opened on a half-changed vault")
                    self.assertIn(PUT_BACK, screen)
                    self.assertEqual(VF.recovery_copies(), copies_before)
                    self.assertEqual(VF.integrity_status(), "interrupted")
                    outcomes.add("mixed")

                # Opens everything: reaches the menu and finishes the change.
                for password in opens[:1]:
                    menu, _screen = mobile_login([password])
                    self.assertTrue(menu)
                    self.assertEqual(VF.integrity_status(), "ok")
                    self.assertEqual(VF.recovery_copies(), [])
                    self.assert_reads_back(password)
                    outcomes.add("new" if password == NEW_PASSWORD else "old")
                    # The next login is an ordinary one again.
                    menu, screen = mobile_login([password])
                    self.assertTrue(menu)
                    self.assertNotIn(NOT_FINISHED, screen)

                for name in ("Bunker.mmf", "bunker.cfg", "bunker.salt"):
                    self.assertTrue(Path(name).exists(), name)
        # The kill points cover all three situations.
        self.assertEqual(outcomes, {"old", "new", "mixed"})

    def test_leftover_copies_alone_are_finished_by_a_good_login(self):
        """The change completed but died before removing the copies: the
        record is fine, only the *.prev files say "interrupted"."""
        for name in VF.VAULT_FILES_SET:
            shutil.copy(name, name + VF.BACKUP_SUFFIX)
        self.assertEqual(VF.integrity_status(), "interrupted")
        menu, screen = mobile_login([PASSWORD])
        self.assertTrue(menu)
        self.assertIn(NOT_FINISHED, screen)
        self.assertEqual(VF.recovery_copies(), [])
        self.assertEqual(VF.integrity_status(), "ok")

    def test_login_source_still_calls_finish_interrupted_change(self):
        """Guard for future merges of the mobile login block."""
        import inspect
        source = inspect.getsource(MB.main)
        self.assertIn("finish_interrupted_change()", source)
        self.assertIn("attempts_notice(", source)
        self.assertIn('status == "interrupted"', source)


if __name__ == "__main__":
    unittest.main()
