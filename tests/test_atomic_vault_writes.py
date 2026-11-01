"""Every write of Bunker.mmf goes through the atomic helper, so a crash or
failure while saving can never leave a truncated vault behind."""
import ast
import base64
import contextlib
import io
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import main.INITIALIZE as I

ROOT = Path(__file__).resolve().parent.parent


class NoDirectWrites(unittest.TestCase):
    def test_no_source_opens_bunker_mmf_for_writing(self):
        offenders = []
        for path in sorted((ROOT / "main").glob("*.py")) + [ROOT / "BUNKER.py"]:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Call) and getattr(node.func, "id", None) == "open"):
                    continue
                args = node.args
                if len(args) >= 2 and isinstance(args[0], ast.Constant) \
                        and args[0].value == "Bunker.mmf" \
                        and isinstance(args[1], ast.Constant) \
                        and any(c in str(args[1].value) for c in "wa+x"):
                    offenders.append((path.name, node.lineno))
        self.assertEqual(offenders, [])


class FailureLeavesOldVault(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)
        self.key = base64.urlsafe_b64encode(os.urandom(32))
        self.old = b"previous-vault-bytes" * 5
        Path("Bunker.mmf").write_bytes(self.old)
        os.chmod("Bunker.mmf", 0o600)
        mock.patch.object(I.vault, "manage_config", return_value=None).start()
        self.addCleanup(mock.patch.stopall)

    def tearDown(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def _quiet(self, fn, *a):
        with contextlib.redirect_stdout(io.StringIO()):
            return fn(*a)

    def assertOldIntact(self):
        self.assertEqual(Path("Bunker.mmf").read_bytes(), self.old)
        self.assertEqual(os.listdir("."), ["Bunker.mmf"])

    def test_saveDatabase_failure_during_write(self):
        with mock.patch("os.fsync", side_effect=OSError("disk full")):
            self.assertFalse(self._quiet(I.saveDatabase, {"a": {"b": "c"}}, self.key))
        self.assertOldIntact()

    def test_saveDatabase_failure_during_replace(self):
        with mock.patch("os.replace", side_effect=OSError("denied")):
            self.assertFalse(self._quiet(I.saveDatabase, {"a": {"b": "c"}}, self.key))
        self.assertOldIntact()

    def test_saveDatabase_success_is_0600_and_decryptable(self):
        db = {"a": {"b": "c" * 200}}
        self.assertTrue(self._quiet(I.saveDatabase, db, self.key))
        self.assertEqual(stat.S_IMODE(os.stat("Bunker.mmf").st_mode), 0o600)
        self.assertEqual(I.loadDatabase(self.key), db)

    def test_overwrite_db_failure_during_write(self):
        with mock.patch("os.fsync", side_effect=OSError("disk full")):
            self.assertFalse(self._quiet(I.overwrite_db, b"new-bytes"))
        self.assertEqual(Path("Bunker.mmf").read_bytes(), self.old)
        # the helper's temp file is gone; only the vault and its backup remain
        extras = [n for n in os.listdir(".") if n != "Bunker.mmf"]
        self.assertTrue(all(n.startswith("Bunker.mmf.bak.") for n in extras), extras)

    def test_overwrite_db_success_writes_exact_bytes(self):
        self.assertTrue(self._quiet(I.overwrite_db, b"new-bytes"))
        self.assertEqual(Path("Bunker.mmf").read_bytes(), b"new-bytes")
        self.assertEqual(stat.S_IMODE(os.stat("Bunker.mmf").st_mode), 0o600)


if __name__ == "__main__":
    unittest.main()
