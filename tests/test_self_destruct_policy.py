"""Self-destruct policy: the vault is destroyed ONLY when the failed-login
limit is reached. Never on a crash, an error, EOF (Ctrl+D), Ctrl+C or a
timeout.
"""
import ast
import base64
import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cryptography.exceptions import InvalidTag

import main.DESKTOP as D
import main.INITIALIZE as I

ROOT = Path(__file__).resolve().parent.parent
VAULT_FILES = ("Bunker.mmf", "bunker.salt", "bunker.cfg", "config.cfg")
WIPERS = {"self_destruct", "secure_delete_on_failure"}


class PolicyIsStructural(unittest.TestCase):
    """Guard against new wipe calls creeping back in."""

    def _calls(self):
        found = []
        for path in sorted((ROOT / "main").glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            parents = {}
            for node in ast.walk(tree):
                for child in ast.iter_child_nodes(node):
                    parents[child] = node
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    f = node.func
                    name = getattr(f, "id", None) or getattr(f, "attr", None)
                    if name in WIPERS:
                        found.append((path.name, node, parents))
        return found

    def test_only_one_wipe_call_and_it_is_the_login_limit(self):
        calls = self._calls()
        self.assertEqual(len(calls), 1, [(c[0], c[1].lineno) for c in calls])
        fname, node, parents = calls[0]
        self.assertEqual(fname, "DESKTOP.py")
        self.assertEqual(getattr(node.func, "id", None), "self_destruct")
        guard, p = None, parents.get(node)
        while p is not None:
            if isinstance(p, ast.If):
                guard = ast.unparse(p.test)
                break
            p = parents.get(p)
        self.assertEqual(guard, "attempts >= max_attempts")


class LoginFlowNeverWipesOnErrors(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)
        for name in VAULT_FILES:
            Path(name).write_bytes(b"original-" + name.encode())
        self.ui = {"attempts": 0, "max_attempts": 3,
                   "disable_ipv4": True, "current_timeout": 60}
        self.saved_attempts = []
        self.wiped = []
        quiet = lambda *a, **k: None
        patches = [
            mock.patch.object(D, "clear_screen", quiet),
            mock.patch.object(D, "check_terminal_size", quiet),
            mock.patch.object(D, "spinning_line", quiet),
            mock.patch.object(D, "display_bunker", quiet),
            mock.patch.object(D, "load_salt", lambda *a, **k: b"s" * 32),
            mock.patch.object(D, "load_ui_config", lambda: dict(self.ui)),
            mock.patch.object(D, "save_ui_config",
                              lambda c: self.saved_attempts.append(c["attempts"])),
            mock.patch.object(D, "self_destruct", self._fake_destruct),
            mock.patch.object(D.vault, "derive_key_hybrid", lambda *a, **k: b"key"),
            mock.patch.object(D.time, "sleep", quiet),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def tearDown(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def _fake_destruct(self):
        self.wiped.append(True)
        raise SystemExit(1)

    def _run(self):
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):
                D.main("desktop")

    def assertVaultUntouched(self):
        self.assertEqual(self.wiped, [])
        for name in VAULT_FILES:
            self.assertEqual(Path(name).read_bytes(), b"original-" + name.encode(), name)

    def test_eof_at_first_prompt(self):
        with mock.patch("builtins.input", side_effect=EOFError):
            self._run()
        self.assertVaultUntouched()

    def test_eof_in_password_prompt(self):
        with mock.patch("builtins.input", return_value="n"), \
             mock.patch.object(D, "timeout_getpass", side_effect=ValueError("ERROR: EOFError")):
            self._run()
        self.assertVaultUntouched()

    def test_non_password_error_does_not_count_as_attempt(self):
        with mock.patch("builtins.input", return_value="n"), \
             mock.patch.object(D, "timeout_getpass", return_value="pw"), \
             mock.patch.object(D.vault, "decrypt_data", side_effect=ValueError("bad data")):
            self._run()
        self.assertEqual(self.saved_attempts, [])
        self.assertVaultUntouched()

    def test_vault_load_failure_after_login(self):
        config = json.dumps({"salt": base64.b64encode(b"s" * 32).decode(),
                             "verifier": base64.b64encode(b"v" * 32).decode()}).encode()
        with mock.patch("builtins.input", return_value="n"), \
             mock.patch.object(D, "timeout_getpass", return_value="pw"), \
             mock.patch.object(D.vault, "decrypt_data", return_value=config), \
             mock.patch.object(D.vault, "verify_password_enhanced", return_value=True), \
             mock.patch.object(D, "loadDatabase", side_effect=ValueError("corrupt")):
            self._run()
        self.assertVaultUntouched()

    def test_crash_in_main_menu(self):
        config = json.dumps({"salt": base64.b64encode(b"s" * 32).decode(),
                             "verifier": base64.b64encode(b"v" * 32).decode()}).encode()
        with mock.patch("builtins.input", return_value="n"), \
             mock.patch.object(D, "timeout_getpass", return_value="pw"), \
             mock.patch.object(D.vault, "decrypt_data", return_value=config), \
             mock.patch.object(D.vault, "verify_password_enhanced", return_value=True), \
             mock.patch.object(D, "loadDatabase", return_value={}), \
             mock.patch.object(D, "manage_passwords_and_notes", side_effect=RuntimeError("bug")):
            self._run()
        self.assertVaultUntouched()

    def test_manage_db_error_does_not_wipe(self):
        with mock.patch.object(D.vault, "decrypt_data", side_effect=ValueError("bad")), \
             mock.patch.object(D.vault, "secure_delete_on_failure") as wipe, \
             contextlib.redirect_stdout(io.StringIO()):
            D.manage_passwords_and_notes(b"key")
        wipe.assert_not_called()
        self.assertVaultUntouched()

    def test_failed_login_limit_still_self_destructs(self):
        """The one deliberate trigger: wrong master password max_attempts times."""
        with mock.patch("builtins.input", return_value="n"), \
             mock.patch.object(D, "timeout_getpass", return_value="wrong"), \
             mock.patch.object(D.vault, "decrypt_data", side_effect=InvalidTag()):
            self._run()
        self.assertEqual(self.saved_attempts, [1, 2, 3])
        self.assertEqual(self.wiped, [True])


class LoadDatabaseNeverWipes(unittest.TestCase):
    def test_missing_vault_raises_and_keeps_salt_and_config(self):
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                Path("bunker.salt").write_bytes(b"salt")
                Path("bunker.cfg").write_bytes(b"cfg")
                with mock.patch.object(I, "self_destruct") as wipe, \
                     contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaises(ValueError):
                        I.loadDatabase(b"key")
                wipe.assert_not_called()
                self.assertEqual(Path("bunker.salt").read_bytes(), b"salt")
                self.assertEqual(Path("bunker.cfg").read_bytes(), b"cfg")
            finally:
                os.chdir(cwd)


class InterruptAndTimeoutNeverWipe(unittest.TestCase):
    """Ctrl+C and the inactivity timeout end via os._exit after cleanup."""

    def _check(self, cleanup):
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                for name in VAULT_FILES:
                    Path(name).write_bytes(b"keep")
                with mock.patch.object(I.os, "_exit", side_effect=SystemExit), \
                     mock.patch.object(I, "clear_screen", lambda: None), \
                     contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaises(SystemExit):
                        cleanup()
                for name in VAULT_FILES:
                    self.assertEqual(Path(name).read_bytes(), b"keep", name)
            finally:
                os.chdir(cwd)

    def test_ctrl_c(self):
        self._check(I.interruptCleanup)

    def test_timeout(self):
        self._check(I.timeoutCleanup)

    def test_error_cleanup(self):
        self._check(lambda: I.errorCleanup("boom"))


if __name__ == "__main__":
    unittest.main()
