"""Two BUNKER windows on one vault never lose each other's changes.

The desktop and mobile interfaces work on the same Bunker.mmf, and nothing
stops a user from having both open. Before the vault lock, two saves that
overlapped silently dropped one side's change (both loaded, both saved, the
second file won), and the desktop interface saved the copy it had loaded at
login over anything saved since.

Covered here, with real encryption and real files:

* the lock itself, including against a second real process, and that a
  killed process does not leave the vault locked;
* VAULT_STORE.modify from several processes at once;
* VAULT_STORE.commit, which saves a copy held in memory: it merges what
  another window saved, or refuses when the file no longer opens;
* the desktop screens that save through it.
"""
import base64
import contextlib
import io
import os
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import main.DESKTOP as D
import main.INITIALIZE as I
from main import SECURE_IO
from main import VAULT_STORE as S
from tests.test_desktop_flows import ANSWERS

ROOT = Path(__file__).resolve().parent.parent
LOCK_FILE = "Bunker.mmf.lock"


def random_key():
    return base64.urlsafe_b64encode(os.urandom(32))


def child(*args, **kwargs):
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    return subprocess.Popen([sys.executable, "-m", "tests._vault_child", *map(str, args)],
                            env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, **kwargs)


class VaultCase(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)
        self.addCleanup(self._restore)
        self.key = random_key()
        S.save({}, self.key)

    def _restore(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def note(self, title="t", content="c", **kw):
        return S.make_note(title, content, self.key, **kw)

    def profile(self, domain="example.com", username="me", email="me@example.com",
                password="pw-1"):
        return S.make_profile(domain, username, email, password, self.key)

    def on_disk(self):
        return S.load(self.key)

    def elsewhere(self, mutate):
        """A change saved by another window (what the mobile interface does)."""
        S.modify(self.key, mutate)


class Lock(VaultCase):
    def test_lock_file_is_private_and_stays(self):
        with S.locked():
            self.assertTrue(os.path.exists(LOCK_FILE))
        self.assertTrue(os.path.exists(LOCK_FILE))  # kept on purpose
        self.assertEqual(os.path.getsize(LOCK_FILE), 0)
        if os.name != "nt":  # POSIX permissions only
            self.assertEqual(stat.S_IMODE(os.stat(LOCK_FILE).st_mode), 0o600)

    def test_reentrant_in_one_process(self):
        with S.locked():
            with S.locked(timeout=0):
                S.modify(self.key, lambda db: db.__setitem__("a", {"x": "1"}))
        self.assertEqual(list(self.on_disk()), ["a"])
        with S.locked(timeout=0):  # fully released afterwards
            pass

    def test_a_second_thread_waits_its_turn(self):
        order = []
        other = []

        def second():
            S.modify(self.key, lambda db: (order.append("second"),
                                           db.__setitem__("b", {"x": "2"})))

        def first(db):
            t = threading.Thread(target=second)
            t.start()
            other.append(t)
            t.join(0.3)  # give it every chance to barge in
            order.append("first")
            db["a"] = {"x": "1"}

        S.modify(self.key, first)
        other[0].join(30)
        self.assertEqual(order, ["first", "second"])
        self.assertEqual(sorted(self.on_disk()), ["a", "b"])

    def test_unlockable_folder_still_saves(self):
        """Some network and removable file systems cannot lock files. The
        lock is skipped there; the vault must not become read-only."""
        no_locks = OSError(S.errno.ENOLCK, "No locks available")
        with mock.patch.object(S, "_try_lock", side_effect=no_locks):
            S.modify(self.key, lambda db: db.__setitem__("a", {"x": "1"}))
        self.assertEqual(list(self.on_disk()), ["a"])

    def test_other_lock_errors_are_not_swallowed(self):
        with mock.patch.object(S, "_try_lock", side_effect=OSError(S.errno.EIO, "I/O error")):
            with self.assertRaises(OSError):
                S.modify(self.key, lambda db: db.__setitem__("a", {"x": "1"}))
        self.assertEqual(dict(self.on_disk()), {})


class LockAgainstAnotherProcess(VaultCase):
    def hold(self):
        proc = child("hold")
        self.addCleanup(self._reap, proc)
        self.assertEqual(proc.stdout.readline().strip(), "locked", proc.stderr)
        return proc

    @staticmethod
    def _reap(proc):
        if proc.poll() is None:
            proc.kill()
        proc.communicate()

    def test_change_waits_then_gives_up_without_touching_the_vault(self):
        self.hold()
        before = Path("Bunker.mmf").read_bytes()
        with mock.patch.object(S, "LOCK_TIMEOUT", 0.3):
            with self.assertRaises(S.VaultBusy) as busy:
                S.modify(self.key, lambda db: db.__setitem__("a", {"x": "1"}))
            db = S.load(self.key)
            db["b"] = {"x": "2"}
            with self.assertRaises(S.VaultBusy):
                S.commit(db, self.key)
        self.assertEqual(Path("Bunker.mmf").read_bytes(), before)
        # The message is safe to show and says what to do.
        self.assertIn("another BUNKER window", SECURE_IO.safe_error(busy.exception))

    def test_change_goes_through_once_the_other_process_lets_go(self):
        proc = self.hold()
        done = []
        t = threading.Thread(target=lambda: done.append(
            S.modify(self.key, lambda db: db.__setitem__("a", {"x": "1"}))))
        t.start()
        t.join(0.3)
        self.assertTrue(t.is_alive(), "the change did not wait for the lock")
        proc.stdin.write("\n")
        proc.stdin.flush()
        t.join(30)
        self.assertFalse(t.is_alive())
        self.assertEqual(list(self.on_disk()), ["a"])

    def test_a_killed_process_does_not_leave_the_vault_locked(self):
        proc = self.hold()
        proc.kill()
        proc.wait(30)
        with mock.patch.object(S, "LOCK_TIMEOUT", 5):
            S.modify(self.key, lambda db: db.__setitem__("a", {"x": "1"}))
        self.assertEqual(list(self.on_disk()), ["a"])


class SeveralProcessesAtOnce(VaultCase):
    def run_all(self, jobs):
        procs = [child(mode, self.key.decode(), prefix, count) for mode, prefix, count in jobs]
        for proc in procs:
            _out, err = proc.communicate(timeout=300)
            self.assertEqual(proc.returncode, 0, err)

    def expect(self, jobs, extra=()):
        want = sorted([f"{prefix}-{i}" for _m, prefix, count in jobs for i in range(count)]
                      + list(extra))
        self.assertEqual(sorted(self.on_disk()), want)

    def test_four_processes_adding_entries_lose_none(self):
        jobs = [("add", f"w{n}", 15) for n in range(4)]
        self.run_all(jobs)
        self.expect(jobs)

    def test_held_copies_and_reloading_writers_lose_none(self):
        """Two "desktop" processes each keep the copy they loaded at the
        start, two "mobile" processes reload for every change."""
        jobs = [("held", "d0", 12), ("held", "d1", 12), ("add", "m0", 12), ("add", "m1", 12)]
        self.run_all(jobs)
        self.expect(jobs)

    def test_this_process_and_another_interleave(self):
        jobs = [("add", "other", 20)]
        procs = [child(mode, self.key.decode(), prefix, count) for mode, prefix, count in jobs]
        db = S.load(self.key)  # held for the whole run, like the desktop
        with mock.patch.object(S, "LOCK_TIMEOUT", 120):
            for i in range(20):
                db[f"here-{i}"] = {"title": "x", "content": "y"}
                S.commit(db, self.key)
        for proc in procs:
            _out, err = proc.communicate(timeout=300)
            self.assertEqual(proc.returncode, 0, err)
        self.expect(jobs, extra=[f"here-{i}" for i in range(20)])


class CommitKeepsTheOtherWindowsChanges(VaultCase):
    """``held`` is the copy a desktop manager loaded when its menu opened."""

    def setUp(self):
        super().setUp()
        S.save({"n1": self.note("one", "first"), "p1": self.profile()}, self.key)
        self.held = S.load(self.key)

    def test_unchanged_file_is_simply_saved(self):
        self.held["n2"] = self.note("two")
        report = S.commit(self.held, self.key)
        self.assertFalse(report.merged)
        self.assertEqual(report.notice(), [])
        self.assertEqual(sorted(self.on_disk()), ["n1", "n2", "p1"])

    def test_add_here_and_add_there_are_both_kept(self):
        self.elsewhere(lambda db: db.__setitem__("m1", self.note("from mobile")))
        self.held["d1"] = self.note("from desktop")
        report = S.commit(self.held, self.key)
        self.assertTrue(report.merged)
        self.assertEqual(sorted(self.on_disk()), ["d1", "m1", "n1", "p1"])
        # The window that saved now shows the other window's entry too.
        self.assertEqual(sorted(self.held), ["d1", "m1", "n1", "p1"])
        self.assertIn("another BUNKER window", report.notice()[0])
        self.assertEqual(len(report.notice()), 1)

    def test_two_saves_in_a_row_from_the_held_copy(self):
        self.elsewhere(lambda db: db.__setitem__("m1", self.note("from mobile")))
        self.held["d1"] = self.note("d1")
        S.commit(self.held, self.key)
        self.elsewhere(lambda db: db.__setitem__("m2", self.note("again")))
        self.held["d2"] = self.note("d2")
        self.assertTrue(S.commit(self.held, self.key).merged)
        self.assertFalse(S.commit(self.held, self.key).merged)
        self.assertEqual(sorted(self.on_disk()), ["d1", "d2", "m1", "m2", "n1", "p1"])

    def test_delete_there_is_not_undone_by_a_save_here(self):
        self.elsewhere(lambda db: db.pop("n1"))
        self.held["d1"] = self.note("from desktop")
        S.commit(self.held, self.key)
        self.assertEqual(sorted(self.on_disk()), ["d1", "p1"])
        self.assertNotIn("n1", self.held)

    def test_delete_here_and_edit_there_of_different_entries(self):
        self.elsewhere(lambda db: db.__setitem__(
            "p1", S.update_profile(db["p1"], self.key, password="pw-2")))
        del self.held["n1"]
        report = S.commit(self.held, self.key)
        self.assertEqual(list(self.on_disk()), ["p1"])
        self.assertEqual(S.read_profile(self.on_disk()["p1"], self.key)["password"], "pw-2")
        self.assertEqual((report.both_changed, report.kept_edited, report.kept_deleted),
                         (0, 0, 0))

    def test_same_entry_different_fields_keeps_both(self):
        """The desktop edit screen re-encrypts every field of the entry, so
        unchanged fields are different bytes; they must still count as
        unchanged, or the other window's new password would be undone."""
        self.elsewhere(lambda db: db.__setitem__(
            "p1", S.update_profile(db["p1"], self.key, password="pw-2")))
        self.held["p1"] = S.make_profile("example.com", "new-name", "me@example.com",
                                         "pw-1", self.key)  # all fields re-encrypted
        report = S.commit(self.held, self.key)
        got = S.read_profile(self.on_disk()["p1"], self.key)
        self.assertEqual((got["username"], got["password"]), ("new-name", "pw-2"))
        self.assertEqual(report.both_changed, 0)
        self.assertEqual(S.read_profile(self.held["p1"], self.key), got)

    def test_same_field_changed_in_both_keeps_this_windows_and_says_so(self):
        self.elsewhere(lambda db: db.__setitem__(
            "p1", S.update_profile(db["p1"], self.key, password="theirs")))
        self.held["p1"] = S.update_profile(self.held["p1"], self.key, password="ours")
        report = S.commit(self.held, self.key)
        self.assertEqual(S.read_profile(self.on_disk()["p1"], self.key)["password"], "ours")
        self.assertEqual(report.both_changed, 1)
        self.assertTrue(any("changed in both windows" in line for line in report.notice()))

    def test_same_value_set_in_both_is_not_a_conflict(self):
        self.elsewhere(lambda db: db.__setitem__(
            "p1", S.update_profile(db["p1"], self.key, password="same")))
        self.held["p1"] = S.update_profile(self.held["p1"], self.key, password="same")
        self.assertEqual(S.commit(self.held, self.key).both_changed, 0)

    def test_deleted_here_but_edited_there_is_kept(self):
        self.elsewhere(lambda db: db.__setitem__(
            "n1", S.update_note(db["n1"], self.key, content="edited on the phone")))
        del self.held["n1"]
        report = S.commit(self.held, self.key)
        self.assertEqual(S.read_note(self.on_disk()["n1"], self.key)["content"],
                         "edited on the phone")
        self.assertIn("n1", self.held)
        self.assertEqual(report.kept_edited, 1)
        self.assertTrue(any("NOT deleted" in line for line in report.notice()))

    def test_edited_here_but_deleted_there_is_kept(self):
        self.elsewhere(lambda db: db.pop("n1"))
        self.held["n1"] = S.update_note(self.held["n1"], self.key, content="edited here")
        report = S.commit(self.held, self.key)
        self.assertEqual(S.read_note(self.on_disk()["n1"], self.key)["content"], "edited here")
        self.assertEqual(report.kept_deleted, 1)

    def test_private_and_tags_travel_together(self):
        """A private note's tags are replaced by the PRIVATE marker. Taking
        "private" from one window and "tags" from the other would leave a
        private note with readable tags."""
        self.elsewhere(lambda db: db.__setitem__(
            "n1", S.update_note(db["n1"], self.key, private=True)))
        self.held["n1"] = S.update_note(self.held["n1"], self.key, tags=["work"])
        report = S.commit(self.held, self.key)
        got = S.read_note(self.on_disk()["n1"], self.key)
        self.assertEqual((got["private"], got["tags"]), (False, ["work"]))
        self.assertEqual(report.both_changed, 1)
        # ...and the other way round, with the title changed here.
        self.elsewhere(lambda db: db.__setitem__(
            "n1", S.update_note(db["n1"], self.key, private=True)))
        self.held["n1"] = S.update_note(self.held["n1"], self.key, title="renamed")
        S.commit(self.held, self.key)
        got = S.read_note(self.on_disk()["n1"], self.key)
        self.assertEqual((got["title"], got["private"], got["tags"]),
                         ("renamed", True, ["PRIVATE"]))

    def test_entries_this_code_does_not_understand_pass_through(self):
        self.elsewhere(lambda db: db.__setitem__("x1", {"future": "field", "n": 1}))
        self.held["d1"] = self.note("d1")
        S.commit(self.held, self.key)
        self.assertEqual(self.on_disk()["x1"], {"future": "field", "n": 1})

    def test_refuses_when_the_file_no_longer_opens_with_this_key(self):
        """For example the master password was changed in another window:
        the vault is now encrypted under a different key."""
        other_key = random_key()
        S.save({"n1": S.make_note("one", "first", other_key)}, other_key)
        before = Path("Bunker.mmf").read_bytes()
        self.held["d1"] = self.note("d1")
        with self.assertRaises(S.VaultChangedElsewhere) as refused:
            S.commit(self.held, self.key)
        self.assertEqual(Path("Bunker.mmf").read_bytes(), before)
        self.assertIn("log in again", SECURE_IO.safe_error(refused.exception))
        # modify (the mobile path) cannot open it either, says why, and
        # writes nothing.
        with self.assertRaises(S.VaultChangedElsewhere):
            S.modify(self.key, lambda db: db.__setitem__("m", {"x": "1"}))
        self.assertEqual(Path("Bunker.mmf").read_bytes(), before)

    def test_refuses_when_the_file_was_damaged(self):
        Path("Bunker.mmf").write_bytes(b"\x00" * 64)
        self.held["d1"] = self.note("d1")
        with self.assertRaises(S.VaultChangedElsewhere):
            S.commit(self.held, self.key)
        self.assertEqual(Path("Bunker.mmf").read_bytes(), b"\x00" * 64)

    def test_failed_write_after_a_merge_can_be_retried(self):
        self.elsewhere(lambda db: db.__setitem__("m1", self.note("from mobile")))
        self.held["d1"] = self.note("d1")
        with mock.patch.object(SECURE_IO.os, "replace", side_effect=OSError(28, "full")):
            with self.assertRaises(OSError):
                S.commit(self.held, self.key)
        self.assertEqual(sorted(self.on_disk()), ["m1", "n1", "p1"])
        S.commit(self.held, self.key)
        self.assertEqual(sorted(self.on_disk()), ["d1", "m1", "n1", "p1"])

    def test_check_can_veto_the_write(self):
        before = Path("Bunker.mmf").read_bytes()

        def veto(_blob):
            raise ValueError("no")

        self.held["d1"] = self.note("d1")
        with self.assertRaises(ValueError):
            S.commit(self.held, self.key, check=veto)
        self.assertEqual(Path("Bunker.mmf").read_bytes(), before)

    def test_plain_dict_replaces_the_file_as_before(self):
        self.assertFalse(S.commit({"only": {"x": "1"}}, self.key).merged)
        self.assertEqual(list(self.on_disk()), ["only"])

    def test_revert_takes_unsaved_changes_back_out(self):
        self.held["d1"] = self.note("d1")
        del self.held["n1"]
        S.revert(self.held)
        self.assertEqual(sorted(self.held), ["n1", "p1"])
        self.assertFalse(S.commit(self.held, self.key).merged)
        self.assertEqual(sorted(self.on_disk()), ["n1", "p1"])

    def test_fork_and_adopt_keep_the_record_of_the_loaded_file(self):
        self.elsewhere(lambda db: db.__setitem__("m1", self.note("from mobile")))
        work = S.fork(self.held)
        work["d1"] = self.note("d1")
        self.assertEqual(sorted(self.held), ["n1", "p1"])  # original untouched so far
        S.commit(work, self.key)
        S.adopt(self.held, work)
        self.assertEqual(sorted(self.held), ["d1", "m1", "n1", "p1"])
        self.held["d2"] = self.note("d2")
        self.assertFalse(S.commit(self.held, self.key).merged)
        self.assertEqual(sorted(self.on_disk()), ["d1", "d2", "m1", "n1", "p1"])


class DesktopSavesMerge(VaultCase):
    """The desktop screens, driven through their prompts."""

    def run_screen(self, func, db, answers=ANSWERS):
        prompts = []

        def answer(prompt, *_a, **_k):
            prompts.append(prompt)
            if len(prompts) > 60:
                raise AssertionError("prompt loop")
            for key, value in answers.items():
                if key in prompt:
                    return value
            return ""

        out = io.StringIO()
        with mock.patch.object(D, "timeoutInput", answer), \
             mock.patch.object(D, "timeout_getpass", answer), \
             mock.patch.object(I, "timeoutInput", answer), \
             mock.patch.object(D, "clear_screen", lambda *a, **k: None), \
             mock.patch.object(D, "displayHeader", lambda *a, **k: None), \
             mock.patch.object(I.vault, "manage_config", return_value=None), \
             contextlib.redirect_stdout(out):
            result = func(self.key, db)
        return result, out.getvalue(), prompts

    def test_add_profile_from_a_stale_copy_keeps_the_phones_note(self):
        db = D._open_vault(Path("Bunker.mmf").read_bytes(), self.key)  # manager opens
        self.elsewhere(lambda d: d.__setitem__("m1", self.note("from mobile")))
        _r, screen, prompts = self.run_screen(D.addProfile, db)
        on_disk = self.on_disk()
        self.assertIn("m1", on_disk)
        self.assertEqual(len(on_disk), 2)
        self.assertEqual(sorted(db), sorted(on_disk))
        self.assertIn("also changed in another BUNKER window", screen)
        # The notice waits for Enter instead of being wiped by the next screen.
        self.assertTrue(any("Press 'enter' to continue" in p for p in prompts))

    def test_add_profile_without_another_window_shows_no_notice(self):
        db = D._open_vault(Path("Bunker.mmf").read_bytes(), self.key)
        _r, screen, _p = self.run_screen(D.addProfile, db)
        self.assertNotIn("another BUNKER window", screen)
        self.assertEqual(len(self.on_disk()), 1)

    def test_busy_vault_is_reported_and_the_change_is_not_kept_in_memory(self):
        db = D._open_vault(Path("Bunker.mmf").read_bytes(), self.key)
        db["d1"] = self.note("d1")
        out = io.StringIO()
        with mock.patch.object(S, "_try_lock", return_value=False), \
             mock.patch.object(S, "LOCK_TIMEOUT", 0.1), \
             mock.patch.object(D, "timeoutInput", lambda *a, **k: ""), \
             contextlib.redirect_stdout(out):
            with self.assertRaises(S.VaultBusy):
                D._save_vault(db, self.key)
        self.assertIn("Not saved", out.getvalue())
        self.assertIn("another BUNKER window is saving", out.getvalue())
        self.assertEqual(dict(db), {})
        self.assertEqual(dict(self.on_disk()), {})

    def test_import_from_a_stale_copy_keeps_the_phones_note(self):
        db = D._open_vault(Path("Bunker.mmf").read_bytes(), self.key)
        self.elsewhere(lambda d: d.__setitem__("m1", self.note("from mobile")))
        _r, screen, _p = self.run_screen(
            lambda key, d: D._finish_import(d, [self.note("imported")], key, "notes"), db)
        self.assertEqual(len(self.on_disk()), 2)
        self.assertIn("m1", self.on_disk())
        self.assertEqual(sorted(db), sorted(self.on_disk()))
        self.assertIn("also changed in another BUNKER window", screen)

    def test_save_database_and_load_database_round_trip_tracks_the_file(self):
        with contextlib.redirect_stdout(io.StringIO()), \
             mock.patch.object(I.vault, "manage_config", return_value=None):
            db = I.loadDatabase(self.key)
            self.elsewhere(lambda d: d.__setitem__("m1", self.note("from mobile")))
            db["d1"] = self.note("d1")
            self.assertTrue(I.saveDatabase(db, self.key))
        self.assertEqual(sorted(self.on_disk()), ["d1", "m1"])

    def test_note_manager_reloads_the_vault_before_adding(self):
        """The reload before "add note" opened the binary vault in text mode,
        failed every time and silently fell back to the stale copy."""
        contents = Path("Bunker.mmf").read_bytes()  # what the main menu passes in
        self.elsewhere(lambda d: d.__setitem__("m1", self.note("from mobile")))
        seen = {}

        def add_note(_key, db):
            seen["db"] = sorted(db)
            return True  # "timed out": leave the manager

        with mock.patch.object(D, "addNote", add_note), \
             mock.patch.object(D, "timeoutInput", lambda *a, **k: "a"), \
             mock.patch.object(D, "clear_screen", lambda *a, **k: None), \
             mock.patch.object(D, "check_terminal_size", lambda *a, **k: None), \
             mock.patch.object(D, "display_watermark", lambda *a, **k: None), \
             mock.patch.object(D, "load_ui_config", lambda *a, **k: {"disable_ipv4": True}), \
             mock.patch.object(D, "displayTimeout", lambda *a, **k: ""), \
             contextlib.redirect_stdout(io.StringIO()):
            D.main_note_manager(self.key, contents)
        self.assertEqual(seen["db"], ["m1"])


class NoStaleOrTextModeAccess(unittest.TestCase):
    """Source checks, so a new screen cannot quietly bring the problem back."""

    def sources(self):
        for path in sorted((ROOT / "main").glob("*.py")):
            yield path.name, path.read_text(encoding="utf-8")

    def test_vault_is_never_opened_in_text_mode(self):
        import ast
        offenders = []
        for name, text in self.sources():
            for node in ast.walk(ast.parse(text)):
                if not (isinstance(node, ast.Call) and getattr(node.func, "id", None) == "open"):
                    continue
                if not (node.args and isinstance(node.args[0], ast.Constant)
                        and node.args[0].value == "Bunker.mmf"):
                    continue
                mode = "r"
                if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                    mode = node.args[1].value
                for kw in node.keywords:
                    if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                        mode = kw.value.value
                if "b" not in str(mode):
                    offenders.append(f"{name}:{node.lineno}")
        self.assertEqual(offenders, [], "Bunker.mmf is binary: open it with 'rb'")

    def test_desktop_never_writes_the_vault_directly(self):
        """Every desktop save goes through _save_vault / saveDatabase, which
        merge. A direct write would save a stale copy over the file."""
        text = dict(self.sources())["DESKTOP.py"]
        code = "\n".join(line for line in text.splitlines()
                         if not line.lstrip().startswith("#"))
        self.assertNotIn("write_private_bytes", code)
        self.assertNotIn("write_bytes_atomic", code)
        self.assertNotIn("json.dumps(db)", code)


if __name__ == "__main__":
    unittest.main()
