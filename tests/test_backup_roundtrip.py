"""Backup round-trip: export profiles (encrypted and plain text), import them
into a brand-new vault, and get exactly the same data back. Real encryption;
only terminal input is faked.
"""
import base64
import contextlib
import io
import json
import os
import shutil
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import main.DESKTOP as D
import main.INITIALIZE as I
from tests.test_vault_integrity import PASSWORD, key_for, quiet, run_setup

PASSPHRASE = "backup passphrase 2026"
PROFILES = [("example.com", "me@example.com", "me", "Sup3r-secret!"),
            ("bank.test", "N/A", "acct42", "another pw 9")]


def answers_for(encrypted, filename):
    table = {
        "export all profiles": "y",
        "export as encrypted": "y" if encrypted else "n",
        "see the password as you type": "y",
        "show your password while typing": "y",
        "passphrase for encryption": PASSPHRASE,
        "Confirm passphrase": PASSPHRASE,
        "passphrase used for encryption": PASSPHRASE,
        "file name to save profiles": filename,
        "Choose file to import": filename,
        "display passwords": "n",
        "import these profiles": "y",
        "Continue with export": "y",
        "Press 'enter'": "",
    }

    def answer(prompt, *_a, **_k):
        for key, value in table.items():
            if key in prompt:
                return value
        raise AssertionError(f"unexpected prompt: {prompt!r}")
    return answer


def make_vault_with_profiles():
    assert run_setup()
    key = key_for(PASSWORD)
    enc = lambda v: v if v == "N/A" else base64.b64encode(I.vault.encrypt_data(v.encode(), key)).decode()
    db = {f"id{i}": {"domain": enc(d), "email": enc(e), "username": enc(u),
                     "password": enc(p), "favorite": i == 0}
          for i, (d, e, u, p) in enumerate(PROFILES)}
    with contextlib.redirect_stdout(io.StringIO()):
        assert I.saveDatabase(db, key)
    return key


def decrypted_profiles(key):
    out = []
    for entry in I.loadDatabase(key).values():
        out.append(tuple(D.decode_and_decrypt(f, entry, key)
                         for f in ("domain", "email", "username", "password")))
    return sorted(out)


class BackupRoundTrip(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self.src = tempfile.mkdtemp()
        self.dst = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.src, True)
        self.addCleanup(shutil.rmtree, self.dst, True)
        self.addCleanup(os.chdir, self._cwd)

    def _io(self, encrypted, filename):
        responder = answers_for(encrypted, filename)
        return contextlib.ExitStack(), [
            mock.patch.object(D, "timeoutInput", responder),
            mock.patch.object(D, "timeout_getpass", responder),
            mock.patch("builtins.input", responder),
            mock.patch.object(D, "clear_screen", quiet),
            mock.patch.object(D, "displayHeader", quiet),
        ]

    def _call(self, func, key, encrypted, filename):
        stack, patches = self._io(encrypted, filename)
        with stack:
            for p in patches:
                stack.enter_context(p)
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            func(key, I.loadDatabase(key))

    def _roundtrip(self, encrypted):
        name = "backup.json"
        os.chdir(self.src)
        key = make_vault_with_profiles()
        expected = decrypted_profiles(key)
        self._call(D.exportProfiles, key, encrypted, name)
        exported = Path(name).read_text(encoding="utf-8")
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE(os.stat(name).st_mode), 0o600)
        shutil.copy(name, os.path.join(self.dst, name))

        os.chdir(self.dst)
        self.assertTrue(run_setup())
        new_key = key_for(PASSWORD)
        self._call(D.importProfiles, new_key, encrypted, name)
        self.assertEqual(decrypted_profiles(new_key), expected)
        return exported

    def test_encrypted_backup_restores_exactly_and_hides_secrets(self):
        exported = self._roundtrip(encrypted=True)
        for _domain, _email, _user, pw in PROFILES:
            self.assertNotIn(pw, exported)
        self.assertIn("verifier", json.loads(exported))

    def test_plain_text_backup_restores_exactly(self):
        exported = self._roundtrip(encrypted=False)
        self.assertIn(PROFILES[0][3], exported)  # plain text, by the user's choice


if __name__ == "__main__":
    unittest.main()
