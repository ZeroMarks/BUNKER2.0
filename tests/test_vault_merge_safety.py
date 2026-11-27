"""Edge cases of saving one vault from two BUNKER windows.

Each test sets up a second window's change with the real store functions
and real encryption, then saves from a copy held in memory the way the
desktop interface does:

* a vault removed by self-destruct in one window is not written back by a
  save from another window that still had it open;
* self-destruct takes the vault lock, so it never runs in the middle of a
  save, and it leaves the lock file in place;
* a merge never makes a private note readable again;
* re-saving an entry with the same values (an edit where every value was
  kept) does not bring back an entry the other window deleted;
* on Windows, a save retries briefly when another window has the vault
  open for reading at that moment.
"""
import base64
import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from main import SECURE_IO
from main import VAULT_STORE as S

ROOT = Path(__file__).resolve().parent.parent
LOCK_FILE = "Bunker.mmf.lock"


def random_key():
    return base64.urlsafe_b64encode(os.urandom(32))


def child(*args):
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    return subprocess.Popen([sys.executable, "-m", "tests._vault_child", *map(str, args)],
                            env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)


class VaultCase(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)
        self.addCleanup(self._restore)
        self.key = random_key()

    def _restore(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def elsewhere(self, mutate):
        """A change saved by another window (what the mobile interface does)."""
        S.modify(self.key, mutate)

    def on_disk(self):
        return S.load(self.key)


class SaveAfterTheVaultWasRemoved(VaultCase):
    def setUp(self):
        super().setUp()
        S.save({"a": S.make_profile("site", "u", "e", "secret", self.key)}, self.key)
        self.held = S.load(self.key)

    def test_held_copy_is_not_written_back(self):
        os.remove("Bunker.mmf")   # self-destruct in another window
        self.held["b"] = S.make_profile("x", "u", "e", "pw2", self.key)
        with self.assertRaises(S.VaultGone) as gone:
            S.commit(self.held, self.key)
        self.assertFalse(os.path.exists("Bunker.mmf"))
        # Callers that already handle VaultChangedElsewhere handle this too.
        self.assertIsInstance(gone.exception, S.VaultChangedElsewhere)
        msg = SECURE_IO.safe_error(gone.exception)
        self.assertIn("removed in another BUNKER window", msg)
        self.assertIn("nothing was saved", msg)

    def test_desktop_save_reports_it_and_keeps_nothing_in_memory(self):
        import main.DESKTOP as D
        os.remove("Bunker.mmf")
        self.held["b"] = S.make_profile("x", "u", "e", "pw2", self.key)
        out = io.StringIO()
        with mock.patch.object(D, "timeoutInput", return_value=""), \
             contextlib.redirect_stdout(out):
            with self.assertRaises(S.VaultGone):
                D._save_vault(self.held, self.key)
        self.assertNotIn("b", self.held)
        self.assertIn("Not saved", out.getvalue())
        self.assertFalse(os.path.exists("Bunker.mmf"))

    def test_a_first_save_of_a_plain_dict_still_creates_the_file(self):
        os.remove("Bunker.mmf")
        S.commit({"a": {"x": "1"}}, self.key)
        self.assertEqual(self.on_disk(), {"a": {"x": "1"}})


class SelfDestructAndTheLock(VaultCase):
    def setUp(self):
        super().setUp()
        S.save({"a": S.make_note("t", "c", self.key)}, self.key)
        for name in ("bunker.salt", "bunker.cfg"):
            Path(name).write_bytes(b"x" * 32)

    def destruct(self):
        import main.SHARED_RESOURCES as SR
        import main.VAULT_FILES as VF

        def fake_shred(cmd, **kw):   # no external tools in tests
            os.remove(cmd[-1])

        with mock.patch.object(VF, "destroy_allowed", return_value=True), \
             mock.patch.object(SR, "clear_screen"), \
             mock.patch.object(SR.time, "sleep"), \
             mock.patch.object(SR.subprocess, "run", side_effect=fake_shred), \
             contextlib.redirect_stdout(io.StringIO()):
            try:
                return SR.self_destruct()
            except SystemExit:
                return "exited"

    def test_lock_file_is_left_in_place(self):
        with S.locked():
            pass
        self.assertTrue(os.path.exists(LOCK_FILE))
        self.assertEqual(self.destruct(), "exited")
        self.assertFalse(os.path.exists("Bunker.mmf"))
        self.assertFalse(os.path.exists("bunker.salt"))
        self.assertTrue(os.path.exists(LOCK_FILE))

    def test_runs_while_holding_the_lock(self):
        import main.SHARED_RESOURCES as SR
        seen = []
        real_rename = os.rename

        def rename(src, dst):
            seen.append(bool(S._held.get(os.path.abspath(S.lock_path()))))
            return real_rename(src, dst)

        with mock.patch.object(SR.os, "rename", side_effect=rename):
            self.destruct()
        self.assertTrue(seen)
        self.assertTrue(all(seen), "a file was deleted without holding the vault lock")

    def test_waits_for_a_save_in_another_window_and_deletes_nothing_if_it_never_ends(self):
        proc = child("hold")
        self.addCleanup(lambda: (proc.poll() is None and proc.kill(), proc.communicate()))
        self.assertEqual(proc.stdout.readline().strip(), "locked", proc.stderr)
        with mock.patch.object(S, "LOCK_TIMEOUT", 0.3):
            self.assertIs(self.destruct(), False)
        for name in ("Bunker.mmf", "bunker.salt", "bunker.cfg"):
            self.assertTrue(os.path.exists(name), name)

    def test_a_window_that_was_logged_in_cannot_bring_the_vault_back(self):
        held = S.load(self.key)
        self.destruct()
        held["b"] = S.make_note("t2", "c2", self.key)
        with self.assertRaises(S.VaultGone):
            S.commit(held, self.key)
        self.assertFalse(os.path.exists("Bunker.mmf"))


class MergeNeverLowersPrivacy(VaultCase):
    def setUp(self):
        super().setUp()
        S.save({"n": S.make_note("t", "body", self.key, tags=["work"])}, self.key)
        self.held = S.load(self.key)

    def test_made_private_there_tags_edited_here(self):
        self.elsewhere(lambda db: db.__setitem__(
            "n", S.update_note(db["n"], self.key, private=True)))
        self.held["n"] = S.update_note(self.held["n"], self.key, tags=["work", "todo"])
        report = S.commit(self.held, self.key)
        got = S.read_note(self.on_disk()["n"], self.key)
        self.assertEqual((got["private"], got["tags"]), (True, ["PRIVATE"]))
        self.assertEqual(report.kept_private, 1)
        self.assertTrue(any("private" in line for line in report.notice()))
        # The window that saved now holds the merged result.
        self.assertTrue(S.read_note(self.held["n"], self.key)["private"])

    def test_made_private_here_tags_edited_there(self):
        self.elsewhere(lambda db: db.__setitem__(
            "n", S.update_note(db["n"], self.key, tags=["home"])))
        self.held["n"] = S.update_note(self.held["n"], self.key, private=True)
        report = S.commit(self.held, self.key)
        got = S.read_note(self.on_disk()["n"], self.key)
        self.assertEqual((got["private"], got["tags"]), (True, ["PRIVATE"]))
        self.assertEqual(report.kept_private, 0)

    def test_tags_changed_in_both_without_privacy_still_keeps_this_window(self):
        self.elsewhere(lambda db: db.__setitem__(
            "n", S.update_note(db["n"], self.key, tags=["home"])))
        self.held["n"] = S.update_note(self.held["n"], self.key, tags=["todo"])
        report = S.commit(self.held, self.key)
        got = S.read_note(self.on_disk()["n"], self.key)
        self.assertEqual((got["private"], got["tags"]), (False, ["todo"]))
        self.assertEqual((report.both_changed, report.kept_private), (1, 0))


class UnchangedResaveKeepsTheOtherWindowsDelete(VaultCase):
    def setUp(self):
        super().setUp()
        S.save({"a": S.make_profile("old-site", "u", "e", "pw", self.key),
                "n": S.make_note("t", "c", self.key)}, self.key)
        self.held = S.load(self.key)

    def test_profile_resaved_with_the_same_values(self):
        self.elsewhere(lambda db: db.pop("a"))
        # Desktop edit with Enter on every field: every value re-encrypted.
        self.held["a"] = S.make_profile("old-site", "u", "e", "pw", self.key)
        report = S.commit(self.held, self.key)
        self.assertNotIn("a", self.on_disk())
        self.assertEqual(report.kept_deleted, 0)
        self.assertNotIn("a", self.held)

    def test_note_resaved_with_the_same_values(self):
        self.elsewhere(lambda db: db.pop("n"))
        self.held["n"] = S.make_note("t", "c", self.key)
        S.commit(self.held, self.key)
        self.assertNotIn("n", self.on_disk())

    def test_a_real_edit_of_an_entry_deleted_there_is_still_kept(self):
        self.elsewhere(lambda db: db.pop("a"))
        self.held["a"] = S.make_profile("old-site", "u", "e", "pw-NEW", self.key)
        report = S.commit(self.held, self.key)
        self.assertEqual(S.read_profile(self.on_disk()["a"], self.key)["password"], "pw-NEW")
        self.assertEqual(report.kept_deleted, 1)

    def test_delete_here_of_an_entry_only_resaved_there_is_not_counted_as_edited(self):
        self.elsewhere(lambda db: db.__setitem__(
            "a", S.make_profile("old-site", "u", "e", "pw", self.key)))
        del self.held["a"]
        report = S.commit(self.held, self.key)
        self.assertNotIn("a", self.on_disk())
        self.assertEqual(report.kept_edited, 0)


class ReplaceRetriesWhileTheFileIsOpen(unittest.TestCase):
    """Windows refuses to replace a file that another process has open
    (Python's open() does not share delete access). Readers do not take the
    lock, so a save retries for a moment instead of failing at once."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = os.path.join(self._tmp.name, "f.bin")
        Path(self.path).write_bytes(b"old")

    def test_a_short_refusal_is_retried(self):
        real = os.replace
        calls = []

        def flaky(src, dst):
            calls.append(1)
            if len(calls) < 3:
                raise PermissionError(13, "Permission denied")
            return real(src, dst)

        with mock.patch.object(SECURE_IO, "_RETRY_REPLACE", True), \
             mock.patch.object(SECURE_IO.os, "replace", side_effect=flaky), \
             mock.patch.object(SECURE_IO.time, "sleep"):
            SECURE_IO.write_private_bytes(self.path, b"new")
        self.assertEqual(Path(self.path).read_bytes(), b"new")
        self.assertEqual(len(calls), 3)
        self.assertEqual(self._leftovers(), [])

    def test_a_lasting_refusal_fails_and_keeps_the_old_file(self):
        with mock.patch.object(SECURE_IO, "_RETRY_REPLACE", True), \
             mock.patch.object(SECURE_IO.os, "replace",
                               side_effect=PermissionError(13, "Permission denied")) as rep, \
             mock.patch.object(SECURE_IO.time, "sleep"):
            with self.assertRaises(PermissionError):
                SECURE_IO.write_private_bytes(self.path, b"new")
        self.assertEqual(rep.call_count, SECURE_IO._REPLACE_TRIES)
        self.assertEqual(Path(self.path).read_bytes(), b"old")
        self.assertEqual(self._leftovers(), [])

    def test_other_systems_do_not_retry(self):
        with mock.patch.object(SECURE_IO, "_RETRY_REPLACE", False), \
             mock.patch.object(SECURE_IO.os, "replace",
                               side_effect=PermissionError(13, "Permission denied")) as rep:
            with self.assertRaises(PermissionError):
                SECURE_IO.write_private_bytes(self.path, b"new")
        self.assertEqual(rep.call_count, 1)

    @unittest.skipUnless(os.name == "nt", "Windows file sharing rules")
    def test_save_while_another_process_reads_the_vault(self):
        cwd = os.getcwd()
        os.chdir(self._tmp.name)
        self.addCleanup(os.chdir, cwd)
        key = random_key()
        S.save({"a": S.make_note("t", "c", key)}, key)
        reader = subprocess.Popen(
            [sys.executable, "-c",
             "import sys, time\n"
             "f = open('Bunker.mmf', 'rb'); print('open', flush=True)\n"
             "time.sleep(0.3); f.close(); sys.stdin.readline()"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(reader.stdout.readline().strip(), "open")
            S.modify(key, lambda db: db.__setitem__("b", S.make_note("t2", "c2", key)))
        finally:
            reader.stdin.write("\n")
            reader.stdin.flush()
            reader.wait(30)
        self.assertEqual(sorted(S.load(key)), ["a", "b"])

    def _leftovers(self):
        return [n for n in os.listdir(self._tmp.name) if n.endswith(".tmp")]


if __name__ == "__main__":
    unittest.main()
