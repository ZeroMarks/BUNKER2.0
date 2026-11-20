"""Every write of Bunker.mmf is atomic.

A save that truncates the file first and then writes it leaves an empty or
cut-short vault if the disk fills up, the write fails or the process dies
part-way. AES-GCM then rejects the whole file and every entry is lost. All
saves therefore go through SECURE_IO.write_private_bytes (temp file, fsync,
os.replace), which leaves the previous vault byte-identical on failure.
"""
import ast
import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import main.DESKTOP as D
import main.INITIALIZE as I
from main import SECURE_IO
from tests.test_desktop_flows import ANSWERS
from tests.test_vault_integrity import PASSWORD, key_for, quiet, run_setup

MAIN = Path(__file__).resolve().parent.parent / "main"
DISK_FULL = OSError(28, "No space left on device")


def _opens_vault_for_writing(node):
    """True for open("Bunker.mmf", <mode with w, a, x or +>)."""
    if not (isinstance(node, ast.Call) and getattr(node.func, "id", None) == "open"):
        return False
    if not node.args or not isinstance(node.args[0], ast.Constant):
        return False
    if node.args[0].value != "Bunker.mmf":
        return False
    mode = None
    if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
        mode = node.args[1].value
    for kw in node.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
            mode = kw.value.value
    return isinstance(mode, str) and any(c in mode for c in "wax+")


class NoDirectWrites(unittest.TestCase):
    def test_no_source_opens_the_vault_for_writing(self):
        offenders = []
        for path in sorted(MAIN.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if _opens_vault_for_writing(node):
                    offenders.append(f"{path.name}:{node.lineno}")
        self.assertEqual(offenders, [], "write Bunker.mmf with write_private_bytes")

    def test_the_check_itself_catches_a_direct_write(self):
        tree = ast.parse('with open("Bunker.mmf", "wb") as f:\n    f.write(b"")\n')
        self.assertTrue(any(_opens_vault_for_writing(n) for n in ast.walk(tree)))
        tree = ast.parse('open("Bunker.mmf", "rb")')
        self.assertFalse(any(_opens_vault_for_writing(n) for n in ast.walk(tree)))


class DiskFullLeavesTheVault(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)
        self.addCleanup(self._restore)
        self.assertTrue(run_setup())
        self.key = key_for(PASSWORD)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(I.saveDatabase({"n1": {"title": "t", "content": "c",
                                                   "tags": [], "favorite": False,
                                                   "private": False}}, self.key))
        self.before = Path("Bunker.mmf").read_bytes()

    def _restore(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def assert_untouched(self):
        self.assertEqual(Path("Bunker.mmf").read_bytes(), self.before)
        self.assertEqual([n for n in os.listdir(".") if n.endswith(".tmp")], [])
        self.assertEqual(sorted(I.loadDatabase(self.key)), ["n1"])

    def test_save_database_reports_failure_and_keeps_the_old_vault(self):
        with mock.patch.object(SECURE_IO.os, "fsync", side_effect=DISK_FULL), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(I.saveDatabase({}, self.key))
        self.assert_untouched()

    def test_overwrite_db_keeps_the_old_vault(self):
        with mock.patch.object(SECURE_IO.os, "replace", side_effect=DISK_FULL), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(I.overwrite_db(b"x" * 200))
        # overwrite_db keeps its own timestamped backup; the vault itself
        # must be exactly what it was.
        self.assertEqual(Path("Bunker.mmf").read_bytes(), self.before)

    def test_cleanup_database_keeps_the_old_vault(self):
        db = I.loadDatabase(self.key)
        db["junk"] = "not an entry"
        with mock.patch.object(SECURE_IO.os, "fsync", side_effect=DISK_FULL), \
             contextlib.redirect_stdout(io.StringIO()):
            I.cleanupDatabase(self.key, db)
        self.assert_untouched()

    def test_desktop_add_profile_on_a_full_disk_keeps_the_old_vault(self):
        prompts = []

        def answer(prompt, *_a, **_k):
            prompts.append(prompt)
            if len(prompts) > 40:
                raise AssertionError("prompt loop")
            for key, value in ANSWERS.items():
                if key in prompt:
                    return value
            return ".c"  # cancel anything else (retry offers, menus)

        with mock.patch.object(SECURE_IO.os, "fsync", side_effect=DISK_FULL), \
             mock.patch.object(D, "timeoutInput", answer), \
             mock.patch.object(D, "timeout_getpass", answer), \
             mock.patch.object(D, "clear_screen", quiet), \
             mock.patch.object(D, "displayHeader", quiet), \
             contextlib.redirect_stdout(io.StringIO()):
            D.addProfile(self.key, I.loadDatabase(self.key))
        self.assertTrue(any("Website domain" in p for p in prompts))
        self.assert_untouched()


if __name__ == "__main__":
    unittest.main()
