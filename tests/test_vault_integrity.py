"""Real-crypto tests for vault file integrity, setup safety and password change.

Each test creates a real vault with setup (Argon2id + AES-GCM, nothing
mocked except terminal I/O), then damages, swaps or changes files the way a
crash, disk problem or user mistake would.
"""
import base64
import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import main.DESKTOP as D
import main.INITIALIZE as I
import main.SHARED_RESOURCES_MOBILE as M
import main.VAULT_FILES as VF

PASSWORD = "correct horse battery"
NEW_PASSWORD = "a different long passphrase"
FILES = ("Bunker.mmf", "bunker.salt", "bunker.cfg", "config.cfg", "bunker.chk")


def quiet(*_a, **_k):
    return None


class Reached(BaseException):
    pass


def run_setup(password=PASSWORD, timeout=300):
    answers = iter(["y", "y", password, password, ""])
    with mock.patch("builtins.input", lambda *a, **k: next(answers)), \
         mock.patch.object(M, "setup_timeout", lambda *a, **k: timeout), \
         mock.patch.object(M, "clear_screen", quiet), \
         mock.patch.object(M, "check_terminal_size", quiet), \
         mock.patch.object(M.time, "sleep", quiet), \
         contextlib.redirect_stdout(io.StringIO()):
        return M.vaultSetup()


def key_for(password):
    salt = Path("bunker.salt").read_bytes()
    return I.vault.derive_key_hybrid(password, salt, password)


def desktop_login(passwords, prompts=None):
    """Run DESKTOP.main with the given passwords; returns (destroyed, reached_menu)."""
    pw = iter(passwords)
    answers = iter(prompts or ["n"] * len(passwords) + ["e"])
    state = {"destroyed": False, "menu": False}

    def destroy():
        state["destroyed"] = True
        raise SystemExit(9)

    def menu(_key):
        state["menu"] = True

    with mock.patch("builtins.input", lambda *a, **k: next(answers)), \
         mock.patch.object(D, "timeout_getpass", lambda *a, **k: next(pw)), \
         mock.patch.object(D, "clear_screen", quiet), \
         mock.patch.object(D, "check_terminal_size", quiet), \
         mock.patch.object(D, "spinning_line", quiet), \
         mock.patch.object(D, "display_bunker", quiet), \
         mock.patch.object(D.time, "sleep", quiet), \
         mock.patch.object(D, "self_destruct", destroy), \
         mock.patch.object(D, "manage_passwords_and_notes", menu), \
         contextlib.redirect_stdout(io.StringIO()):
        try:
            D.main("desktop")
        except SystemExit:
            pass
    return state["destroyed"], state["menu"]


class VaultTestCase(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)
        self.addCleanup(self._restore)

    def _restore(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def snapshot(self):
        return {n: Path(n).read_bytes() for n in FILES if Path(n).is_file()}


class DamagedFilesNeverCountAsWrongPassword(VaultTestCase):
    def setUp(self):
        super().setUp()
        self.assertTrue(run_setup())
        self.assertEqual(VF.integrity_status(), "ok")

    def test_truncated_config_with_correct_password_destroys_nothing(self):
        data = Path("bunker.cfg").read_bytes()
        Path("bunker.cfg").write_bytes(data[: len(data) // 2])
        before = self.snapshot()
        for _ in range(4):
            destroyed, menu = desktop_login([PASSWORD])
            self.assertFalse(destroyed)
            self.assertFalse(menu)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(M.load_ui_config()["attempts"], 0)

    def test_swapped_salt_destroys_nothing(self):
        Path("bunker.salt").write_bytes(os.urandom(32))
        before = self.snapshot()
        for _ in range(4):
            self.assertEqual(desktop_login([PASSWORD]), (False, False))
        self.assertEqual(self.snapshot(), before)

    def test_three_wrong_passwords_on_intact_files_still_self_destruct(self):
        destroyed, menu = desktop_login(["wrong one!", "wrong two!", "wrong three"],
                                        prompts=["n", "n", "n"])
        self.assertTrue(destroyed)
        self.assertFalse(menu)

    def test_legacy_vault_gets_integrity_record_on_successful_login(self):
        os.remove("bunker.chk")
        self.assertEqual(VF.integrity_status(), "unknown")
        self.assertEqual(desktop_login([PASSWORD]), (False, True))
        self.assertEqual(VF.integrity_status(), "ok")

    def test_legacy_vault_limit_does_not_destroy(self):
        os.remove("bunker.chk")
        destroyed, _ = desktop_login(["wrong one!", "wrong two!", "wrong three"],
                                     prompts=["n", "n", "n"])
        self.assertFalse(destroyed)
        self.assertTrue(Path("Bunker.mmf").exists())

    def test_mobile_shares_rules_and_counter(self):
        self.assertEqual(VF.try_password("nope nope", I.vault)[0], "wrong")
        status, key = VF.try_password(PASSWORD, I.vault)
        self.assertEqual(status, "ok")
        self.assertEqual(I.loadDatabase(key), {})
        Path("bunker.cfg").write_bytes(b"x" * 40)
        self.assertEqual(VF.try_password(PASSWORD, I.vault)[0], "mismatch")


class SetupNeverOverwritesAVault(VaultTestCase):
    def test_existing_salt_without_database_refuses_setup(self):
        self.assertTrue(run_setup())
        shutil.move("Bunker.mmf", "elsewhere.mmf")
        before = self.snapshot()
        self.assertFalse(run_setup(password="another password 9"))
        self.assertEqual(self.snapshot(), before)

    def test_cancel_at_timeout_prompt_writes_nothing(self):
        Path("config.cfg").write_bytes(b"shipped settings")
        self.assertFalse(run_setup(timeout=None))
        self.assertEqual(sorted(os.listdir(".")), ["config.cfg"])

    def test_interrupted_setup_can_be_redone(self):
        VF.begin_setup()
        Path("bunker.salt").write_bytes(os.urandom(32))
        self.assertTrue(run_setup())
        self.assertFalse(Path(VF.SETUP_MARKER).exists())
        self.assertEqual(desktop_login([PASSWORD]), (False, True))

    def test_unreadable_database_does_not_start_setup(self):
        self.assertTrue(run_setup())
        before = self.snapshot()
        os.remove("Bunker.mmf")
        os.mkdir("Bunker.mmf")  # exists, but opening it fails
        with mock.patch.object(D, "vaultSetup") as setup:
            self.assertEqual(desktop_login([PASSWORD]), (False, False))
        setup.assert_not_called()
        del before["Bunker.mmf"]
        self.assertEqual(self.snapshot(), before)


class ChangeMasterPassword(VaultTestCase):
    def setUp(self):
        super().setUp()
        self.assertTrue(run_setup())
        key = key_for(PASSWORD)
        enc = lambda v: base64.b64encode(I.vault.encrypt_data(v.encode(), key)).decode()
        self.db = {
            "p1": {"domain": enc("example.com"), "email": "N/A", "username": enc("me"),
                   "password": enc("s3cret!"), "favorite": False},
            "n1": {"title": enc("Note"), "content": enc("body"), "tags": [enc("work"), "N/A"],
                   "favorite": True, "private": False},
        }
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(I.saveDatabase(self.db, key))
        self.key = key

    def _change(self):
        with mock.patch("builtins.input", lambda *a, **k: "n"), \
             mock.patch.object(I, "timeout_getpass", lambda *a, **k: NEW_PASSWORD), \
             mock.patch.object(I, "timeoutInput", lambda *a, **k: ""), \
             mock.patch.object(I, "clear_screen", quiet), \
             contextlib.redirect_stdout(io.StringIO()):
            try:
                I.changeMasterPassword(self.key, I.loadDatabase(self.key))
            except SystemExit:
                pass

    def test_every_field_readable_with_new_password(self):
        self._change()
        status, new_key = VF.try_password(NEW_PASSWORD, I.vault)
        self.assertEqual(status, "ok")
        self.assertEqual(VF.try_password(PASSWORD, I.vault)[0], "wrong")
        db = I.loadDatabase(new_key)
        self.assertEqual(D.decode_and_decrypt("password", db["p1"], new_key), "s3cret!")
        self.assertEqual(D.decode_and_decrypt("email", db["p1"], new_key), "N/A")
        self.assertEqual(D.decrypt_note(db["n1"], new_key)["content"], "body")
        self.assertEqual([D.decode_and_decrypt_tag(t, new_key) for t in db["n1"]["tags"]],
                         ["work", "N/A"])
        self.assertEqual(M.load_ui_config()["current_timeout"], 300)
        self.assertEqual(VF.integrity_status(), "ok")
        self.assertFalse(any(n.endswith(".prev") for n in os.listdir(".")))

    def test_failure_part_way_restores_the_old_vault(self):
        real = VF.write_private_bytes
        failed = []

        def failing(path, data):
            # The new salt fails to write once (e.g. disk briefly full).
            if path == VF.SALT_FILE and not failed:
                failed.append(path)
                raise OSError(28, "No space left on device")
            return real(path, data)

        with mock.patch.object(VF, "write_private_bytes", failing):
            self._change()
        self.assertEqual(failed, [VF.SALT_FILE])
        status, key = VF.try_password(PASSWORD, I.vault)
        self.assertEqual(status, "ok")
        db = I.loadDatabase(key)
        self.assertEqual(D.decode_and_decrypt("password", db["p1"], key), "s3cret!")
        self.assertEqual(VF.integrity_status(), "ok")
        self.assertFalse(any(n.endswith(".prev") for n in os.listdir(".")))


class FreshVaultFlows(VaultTestCase):
    def test_add_profile_reaches_its_first_prompt(self):
        """Used to fail with KeyError('timeout_value') on a new vault."""
        self.assertTrue(run_setup())
        key = key_for(PASSWORD)

        def first_prompt(*_a, **_k):
            raise Reached()

        with mock.patch.object(D, "timeoutInput", first_prompt), \
             mock.patch.object(D, "clear_screen", quiet), \
             contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(Reached):
                D.addProfile(key, I.loadDatabase(key))


if __name__ == "__main__":
    unittest.main()


class FuzzLoginFiles(VaultTestCase):
    """Damage the files that unlock the vault in random ways, then log in
    with the correct password: nothing may ever be destroyed or counted,
    and the vault database must stay byte-identical."""

    ROUNDS = 6  # per file; each login runs the real (slow) key derivation

    def test_damaged_unlock_files_never_destroy_or_count(self):
        import random
        from tests.test_fuzz_vault_input import mutate
        self.assertTrue(run_setup())
        pristine = self.snapshot()
        # Control: the harness really logs in when nothing is damaged.
        self.assertEqual(desktop_login([PASSWORD]), (False, True))
        for n, data in pristine.items():
            Path(n).write_bytes(data)
        rng = random.Random(4242)
        outcomes = {}
        for name in ("bunker.cfg", "bunker.salt", "bunker.chk", "config.cfg"):
            for _ in range(self.ROUNDS):
                for n, data in pristine.items():
                    Path(n).write_bytes(data)
                Path(name).write_bytes(mutate(rng, pristine[name]))
                damaged = self.snapshot()
                destroyed, menu = desktop_login([PASSWORD])
                self.assertFalse(destroyed, f"destroyed after damaging {name}")
                outcomes.setdefault(name, []).append(menu)
                after = self.snapshot()
                self.assertEqual(after["Bunker.mmf"], pristine["Bunker.mmf"], name)
                for n in ("bunker.salt", "bunker.cfg"):
                    self.assertEqual(after.get(n), damaged.get(n), f"{n} rewritten ({name})")
        # Damage to salt/config/record must always stop the login; damaged
        # UI settings may or may not, but never destroy anything.
        for name in ("bunker.cfg", "bunker.salt"):
            self.assertNotIn(True, outcomes[name], f"login succeeded with damaged {name}")
