"""A master password change killed part-way never leads to self-destruct.

Each case runs a real password change (Argon2id + AES-GCM) in a child
process and kills it with os._exit() right after one file write or one
removal of a recovery copy: the same as closing the terminal, a shutdown or
a power cut at that moment. Then, with nothing mocked but terminal I/O:

* three tries of the new password and three of the old one destroy nothing
  and are not counted;
* the vault can always be opened again, either directly with one of the two
  passwords, or by following docs/RECOVERY.md (put the *.prev files back,
  log in with the old password), and every entry reads back exactly;
* once opened, the files are a verified set again and the copies are gone.
"""
import base64
import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import main.DESKTOP as D
import main.INITIALIZE as I
import main.SHARED_RESOURCES_MOBILE as M
import main.VAULT_FILES as VF
from tests.test_vault_integrity import (NEW_PASSWORD, PASSWORD, desktop_login, key_for,
                                        run_setup)

ROOT = Path(__file__).resolve().parent.parent
SECRET = "s3cret-for-crash-test"


def _child(kill_after, folder):
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    return subprocess.run(
        [sys.executable, "-m", "tests._crash_child", str(kill_after), PASSWORD, NEW_PASSWORD],
        cwd=folder, env=env, capture_output=True, text=True, timeout=300)


class InterruptedPasswordChange(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._template = tempfile.mkdtemp()
        cwd = os.getcwd()
        os.chdir(cls._template)
        try:
            assert run_setup()
            key = key_for(PASSWORD)
            enc = lambda v: base64.b64encode(I.vault.encrypt_data(v.encode(), key)).decode()
            db = {"p1": {"domain": enc("example.com"), "email": "N/A", "username": enc("me"),
                         "password": enc(SECRET), "favorite": False}}
            with contextlib.redirect_stdout(io.StringIO()):
                assert I.saveDatabase(db, key)
        finally:
            os.chdir(cwd)
        # Find how many steps a full change takes (run it to the end once).
        probe = tempfile.mkdtemp()
        shutil.copytree(cls._template, probe, dirs_exist_ok=True)
        done = _child(10_000, probe)
        shutil.rmtree(probe, True)
        assert done.returncode == 3, done.stderr
        cls.steps = [l for l in done.stdout.splitlines() if l.startswith("STEPS: ")][-1].split()[1:]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._template, True)

    def setUp(self):
        self._cwd = os.getcwd()
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.addCleanup(os.chdir, self._cwd)
        shutil.copytree(self._template, self.dir, dirs_exist_ok=True)
        os.chdir(self.dir)

    def test_the_change_has_the_expected_steps(self):
        # Copies first, then the record is invalidated before anything is
        # replaced; the final record comes after every vault file.
        self.assertEqual(self.steps[:4], ["write:Bunker.mmf.prev", "write:bunker.cfg.prev",
                                          "write:bunker.salt.prev", "write:bunker.chk"])
        self.assertEqual(self.steps[-4:], ["write:bunker.chk", "remove:Bunker.mmf.prev",
                                           "remove:bunker.cfg.prev", "remove:bunker.salt.prev"])
        self.assertIn("write:config.cfg", self.steps)

    @staticmethod
    def _fully_opens(password):
        """Side-effect-free check: does this password open bunker.cfg and
        Bunker.mmf as they are on disk now?"""
        try:
            status, key = VF.try_password(password, I.vault)
            if status != "ok":
                return False
            with contextlib.redirect_stdout(io.StringIO()):
                I.loadDatabase(key)
            return True
        except BaseException:
            return False

    def _opens(self, password):
        """Log in on the desktop with one password; True if the menu opened
        (the key opened bunker.cfg and Bunker.mmf)."""
        destroyed, menu = desktop_login([password])
        self.assertFalse(destroyed)
        return menu

    def _recover(self):
        """What a user can do, in the order RECOVERY.md gives. Returns the
        password that opened the vault and the route taken."""
        for password, route in ((NEW_PASSWORD, "new"), (PASSWORD, "old")):
            if self._opens(password):
                return password, route
        for prev in VF.recovery_copies():
            os.replace(prev, prev[: -len(VF.BACKUP_SUFFIX)])
        if self._opens(PASSWORD):
            return PASSWORD, "restored"
        # The settings file was re-saved for the new salt: delete it and
        # BUNKER makes a fresh one (RECOVERY.md, "UI config ... corrupted").
        os.remove("config.cfg")
        self.assertTrue(self._opens(PASSWORD), "vault could not be recovered")
        return PASSWORD, "restored+settings"

    def test_killed_after_every_step_never_destroys_and_always_recovers(self):
        routes = {}
        for k in range(1, len(self.steps) + 1):
            with self.subTest(killed_after=self.steps[k - 1]):
                os.chdir(self._cwd)  # Windows cannot remove the current folder
                shutil.rmtree(self.dir)
                shutil.copytree(self._template, self.dir)
                os.chdir(self.dir)
                run = _child(k, self.dir)
                self.assertEqual(run.returncode, 0, run.stderr)

                last_step = k == len(self.steps)
                self.assertEqual(VF.integrity_status(), "ok" if last_step else "interrupted")
                if not last_step:
                    self.assertFalse(VF.destroy_allowed())

                # The scenario from the review: unsure whether the change
                # took, the user types a password that fails, three times.
                # (A password that fully opens the vault finishes the change,
                # after which the other one is simply wrong, as designed.)
                # Once the change has fully finished the files are a verified
                # set again and three wrong passwords destroy, as designed
                # (covered in test_vault_integrity), so only the unfinished
                # states are checked here.
                failing = []
                if not last_step:
                    failing = [p for p in (NEW_PASSWORD, PASSWORD) if not self._fully_opens(p)]
                    failing.append("not either password")
                for wrong in failing:
                    destroyed, _ = desktop_login([wrong] * 3, prompts=["n", "n", "n", "e"])
                    self.assertFalse(destroyed, wrong)
                    self.assertTrue(Path("Bunker.mmf").exists())

                password, routes[k] = self._recover()
                self.assertEqual(VF.integrity_status(), "ok")
                self.assertEqual(VF.recovery_copies(), [])
                key = key_for(password)
                entry = I.loadDatabase(key)["p1"]
                self.assertEqual(D.decode_and_decrypt("password", entry, key), SECRET)
                self.assertEqual(M.load_ui_config()["attempts"], 0)
        # Sanity: the cases cover a crash before the swap (old password
        # still works), a finished swap (new works) and the mixed middle
        # (needs the copies).
        self.assertIn("old", routes.values())
        self.assertIn("new", routes.values())
        self.assertTrue({"restored", "restored+settings"} & set(routes.values()))


class SelfDestructRefusesWithoutAVerifiedSet(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)
        self.addCleanup(self._restore)
        self.assertTrue(run_setup())

    def _restore(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def _destroy(self):
        from main import SHARED_RESOURCES as S
        from unittest import mock
        with contextlib.redirect_stdout(io.StringIO()), \
             mock.patch.object(S.time, "sleep", lambda *_: None), \
             mock.patch.object(S, "clear_screen", lambda *_: None):
            try:
                return S.self_destruct()
            except SystemExit:
                return "destroyed"

    def test_refuses_while_a_recovery_copy_exists(self):
        shutil.copy("Bunker.mmf", "Bunker.mmf.prev")
        self.assertEqual(VF.integrity_status(), "interrupted")
        self.assertIs(self._destroy(), False)
        self.assertTrue(Path("Bunker.mmf").exists())
        self.assertTrue(Path("Bunker.mmf.prev").exists())

    def test_refuses_while_the_record_says_changing(self):
        VF._begin_change()
        self.assertIs(self._destroy(), False)
        self.assertTrue(Path("Bunker.mmf").exists())

    def test_refuses_without_a_record(self):
        os.remove("bunker.chk")
        self.assertIs(self._destroy(), False)
        self.assertTrue(Path("Bunker.mmf").exists())

    def test_unrelated_prev_files_are_left_alone(self):
        Path("notes.prev").write_text("mine")
        self.assertEqual(self._destroy(), "destroyed")
        self.assertFalse(Path("Bunker.mmf").exists())
        self.assertEqual(Path("notes.prev").read_text(), "mine")


if __name__ == "__main__":
    unittest.main()
