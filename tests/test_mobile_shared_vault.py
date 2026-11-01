"""The mobile UI reads and writes the same Bunker.mmf as the desktop UI."""
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
import main.MOBILE as MB
from main import SECURE_IO
from main import VAULT_STORE as S


def random_key():
    return base64.urlsafe_b64encode(os.urandom(32))


class MobileCase(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)
        self.key = random_key()
        self.passwords = []
        patches = [
            mock.patch.object(MB.time, "sleep", lambda *a: None),
            mock.patch.object(MB, "clear_screen", lambda *a, **k: None),
            mock.patch.object(MB, "timeout_getpass",
                              lambda *a, **k: self.passwords.pop(0)),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.clip = {"v": ""}
        SECURE_IO.set_clipboard_backend(lambda t: self.clip.update(v=t),
                                        lambda: self.clip["v"])
        self.addCleanup(SECURE_IO.set_clipboard_backend, None, None)
        self.addCleanup(SECURE_IO.clear_clipboard_if_ours)

    def tearDown(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    # -- helpers
    def seed(self, db=None):
        S.save(db or {}, self.key)

    def db(self):
        return S.load(self.key)

    def drive(self, manager, *answers, passwords=()):
        """Run a manager with scripted keyboard input; returns its output."""
        self.passwords.extend(passwords)
        out = io.StringIO()
        with mock.patch("builtins.input", side_effect=list(answers)), \
                contextlib.redirect_stdout(out):
            manager(self.key, "mobile")
        return out.getvalue()

    def add_note(self, title="Shopping", body=("milk", "eggs"), private="n", tags="a, b", fav="n"):
        answers = ["2", title, *body, ".done", private]
        if private == "n":
            answers.append(tags)
        answers += [fav, "0"]
        return self.drive(MB.mobile_note_manager, *answers)

    def notes(self):
        return {i: S.read_note(e, self.key) for i, e in self.db().items() if S.is_note(e)}

    def profiles(self):
        return {i: S.read_profile(e, self.key) for i, e in self.db().items() if S.is_profile(e)}


class NoteManager(MobileCase):
    add = MobileCase.add_note

    def test_add_persists_in_desktop_format_and_survives_reload(self):
        self.seed()
        self.add()
        raw = json.loads(S.decrypt_bytes(Path("Bunker.mmf").read_bytes(), self.key))
        (nid, entry), = raw.items()
        self.assertIsInstance(entry, dict)
        dn = D.decrypt_note(entry, self.key)
        self.assertEqual((dn["title"], dn["content"], dn["tags"]),
                         ("Shopping", "milk\neggs", ["a", "b"]))
        self.assertEqual(list(self.notes()), [nid])

    def test_add_private_note_gets_private_tag(self):
        self.seed()
        self.add(private="y")
        (n,) = self.notes().values()
        self.assertEqual(n["tags"], ["PRIVATE"])
        self.assertTrue(n["private"])

    def test_edit_title_keeps_content_and_tags(self):
        self.seed()
        self.add()
        # edit note 1: new title, keep content, keep private, keep tags, keep favorite
        self.drive(MB.mobile_note_manager, "3", "1", "Groceries", "", "", "", "", "0")
        (n,) = self.notes().values()
        self.assertEqual((n["title"], n["content"], n["tags"]),
                         ("Groceries", "milk\neggs", ["a", "b"]))

    def test_edit_content_tags_favorite_and_private(self):
        self.seed()
        self.add()
        self.drive(MB.mobile_note_manager, "3", "1", "", "y", "new body", ".done",
                   "", "x,y", "y", "0")
        (n,) = self.notes().values()
        self.assertEqual((n["content"], n["tags"], n["favorite"]), ("new body", ["x", "y"], True))
        self.drive(MB.mobile_note_manager, "3", "1", "", "", "y", "", "0")
        (n,) = self.notes().values()
        self.assertEqual((n["private"], n["tags"]), (True, ["PRIVATE"]))
        self.drive(MB.mobile_note_manager, "3", "1", "", "", "n", "", "", "0")
        (n,) = self.notes().values()
        self.assertEqual((n["private"], n["tags"]), (False, ["N/A"]))

    def test_delete_requires_confirmation_and_persists(self):
        self.seed()
        self.add()
        self.drive(MB.mobile_note_manager, "4", "1", "n", "0")
        self.assertEqual(len(self.notes()), 1)
        self.drive(MB.mobile_note_manager, "4", "1", "y", "0")
        self.assertEqual(self.db(), {})

    def test_view_shows_content_only_after_choosing_a_note(self):
        self.seed()
        self.add(body=("top-secret-body",))
        listing = self.drive(MB.mobile_note_manager, "1", "", "", "0")
        self.assertNotIn("top-secret-body", listing)
        shown = self.drive(MB.mobile_note_manager, "1", "1", "", "0")
        self.assertIn("top-secret-body", shown)

    def test_private_note_needs_view_keyword(self):
        self.seed()
        self.add(body=("hidden-body",), private="y")
        out = self.drive(MB.mobile_note_manager, "1", "1", "no", "0")
        self.assertNotIn("hidden-body", out)
        out = self.drive(MB.mobile_note_manager, "1", "1", "view", "", "0")
        self.assertIn("hidden-body", out)

    def test_desktop_notes_are_listed_and_editable(self):
        nid = S.new_id()
        self.seed({nid: S.make_note("From desktop", "body", self.key, tags=["t"], favorite=True)})
        out = self.drive(MB.mobile_note_manager, "1", "", "0")
        self.assertIn("From desktop", out)
        self.drive(MB.mobile_note_manager, "3", "1", "", "y", "edited on mobile", ".done",
                   "", "", "", "0")
        n = self.notes()[nid]
        self.assertEqual(n["content"], "edited on mobile")
        self.assertEqual((n["title"], n["tags"], n["favorite"]), ("From desktop", ["t"], True))
        self.assertEqual(D.decrypt_note(self.db()[nid], self.key)["content"], "edited on mobile")


class PasswordManager(MobileCase):
    def add(self, site="example.com", user="bob", email="b@x.org", pw="pw-1", fav="n"):
        return self.drive(MB.mobile_password_manager, "2", site, user, email, fav, "0",
                          passwords=[pw])

    def test_add_is_a_desktop_profile(self):
        self.seed()
        self.add()
        (pid, entry), = self.db().items()
        for field, want in (("domain", "example.com"), ("username", "bob"),
                            ("email", "b@x.org"), ("password", "pw-1")):
            self.assertEqual(D.decode_and_decrypt(field, entry, self.key), want)
        self.assertIs(entry["favorite"], False)
        self.assertEqual(set(entry), {"domain", "username", "email", "password", "favorite"})

    def test_empty_username_and_email_become_na_like_desktop(self):
        self.seed()
        self.add(user="", email="")
        (p,) = self.profiles().values()
        self.assertEqual((p["username"], p["email"]), ("N/A", "N/A"))

    def test_edit_changes_only_given_fields(self):
        self.seed()
        self.add()
        self.drive(MB.mobile_password_manager, "3", "1", "", "alice", "", "0",
                   passwords=[""])
        (p,) = self.profiles().values()
        self.assertEqual((p["domain"], p["username"], p["email"], p["password"]),
                         ("example.com", "alice", "b@x.org", "pw-1"))
        self.drive(MB.mobile_password_manager, "3", "1", "", "", "", "0", passwords=["pw-2"])
        (p,) = self.profiles().values()
        self.assertEqual(p["password"], "pw-2")

    def test_delete_persists(self):
        self.seed()
        self.add()
        self.drive(MB.mobile_password_manager, "4", "1", "y", "0")
        self.assertEqual(self.db(), {})

    def test_password_shown_only_after_explicit_yes(self):
        self.seed()
        self.add(pw="Sup3r-Secret")
        out = self.drive(MB.mobile_password_manager, "1", "1", "n", "", "0")
        self.assertNotIn("Sup3r-Secret", out)
        out = self.drive(MB.mobile_password_manager, "1", "1", "y", "", "0")
        self.assertIn("Sup3r-Secret", out)

    def test_copy_goes_through_copy_secret(self):
        self.seed()
        self.add(pw="Sup3r-Secret")
        out = self.drive(MB.mobile_password_manager, "5", "1", "0")
        self.assertEqual(self.clip["v"], "Sup3r-Secret")
        self.assertNotIn("Sup3r-Secret", out)

    def test_desktop_written_profile_is_listed_and_readable(self):
        pid = S.new_id()
        self.seed({pid: S.make_profile("desk.example", "dave", "d@x.org", "dpw", self.key)})
        out = self.drive(MB.mobile_password_manager, "1", "1", "y", "", "0")
        self.assertIn("desk.example", out)
        self.assertIn("dpw", out)


class ProfileManager(MobileCase):
    def test_add_edit_and_favorite_persist(self):
        self.seed()
        self.drive(MB.mobile_profile_manager, "2", "work", "wu", "w@x.org", "0", passwords=["wpw"])
        (pid, p), = self.profiles().items()
        self.assertEqual((p["domain"], p["username"], p["email"], p["password"], p["favorite"]),
                         ("work", "wu", "w@x.org", "wpw", False))
        self.drive(MB.mobile_profile_manager, "3", "1", "work2", "", "new@x.org", "0")
        p = self.profiles()[pid]
        self.assertEqual((p["domain"], p["username"], p["email"], p["password"]),
                         ("work2", "wu", "new@x.org", "wpw"))
        self.drive(MB.mobile_profile_manager, "4", "1", "0")
        self.assertTrue(self.profiles()[pid]["favorite"])
        self.assertTrue(D.decode_and_decrypt("domain", self.db()[pid], self.key) == "work2")
        self.drive(MB.mobile_profile_manager, "4", "1", "0")
        self.assertFalse(self.profiles()[pid]["favorite"])

    def test_view_never_prints_password(self):
        self.seed({S.new_id(): S.make_profile("s", "u", "e", "never-shown", self.key)})
        out = self.drive(MB.mobile_profile_manager, "1", "1", "", "0")
        self.assertNotIn("never-shown", out)
        self.assertIn("u", out)


class ForeignEntriesAndFailures(MobileCase):
    def foreign_db(self):
        return {
            "weird-1": {"future_field": [1, {"a": None}], "password": "plain-not-encrypted"},
            "weird-2": {},
            "desktop-note": S.make_note("keep", "me", self.key, tags=["k"], private=True),
            "desktop-profile": S.make_profile("keep.example", "u", "e", "p", self.key, favorite=True),
        }

    def test_mobile_edits_leave_other_entries_untouched(self):
        before = self.foreign_db()
        self.seed(before)
        before_json = {k: json.dumps(v, sort_keys=True) for k, v in before.items()}
        # add a note, add a password, then delete the new note
        self.add_note()
        self.drive(MB.mobile_password_manager, "2", "new.example", "", "", "n", "0", passwords=["x"])
        after = self.db()
        for k, v in before_json.items():
            self.assertEqual(json.dumps(after[k], sort_keys=True), v, k)
        self.assertEqual(len(after), len(before) + 2)
        self.assertTrue(all(isinstance(v, dict) for v in after.values()))

    def test_editing_one_entry_keeps_unknown_fields_in_it(self):
        pid = "p1"
        entry = S.make_profile("a", "u", "e", "p", self.key)
        entry["future_field"] = {"x": 1}
        self.seed({pid: entry})
        self.drive(MB.mobile_password_manager, "3", "1", "b", "", "", "0", passwords=[""])
        self.assertEqual(self.db()[pid]["future_field"], {"x": 1})
        self.assertEqual(self.profiles()[pid]["domain"], "b")

    def test_legacy_empty_mobile_keys_are_dropped_on_first_save(self):
        S.write_bytes_atomic("Bunker.mmf", S.encrypt_bytes(
            json.dumps({"profiles": [], "notes": [], "accounts": []}).encode(), self.key))
        self.add_note()
        db = self.db()
        self.assertEqual(len(db), 1)
        self.assertTrue(all(isinstance(v, dict) for v in db.values()))

    def test_unsupported_shape_is_not_overwritten(self):
        raw = S.encrypt_bytes(json.dumps({"notes": ["x"]}).encode(), self.key)
        Path("Bunker.mmf").write_bytes(raw)
        out = self.add_note()
        self.assertEqual(Path("Bunker.mmf").read_bytes(), raw)
        self.assertIn("Could not complete", out)

    def test_save_failure_reports_class_only_and_keeps_vault(self):
        self.seed(self.foreign_db())
        before = Path("Bunker.mmf").read_bytes()
        with mock.patch.object(S, "encrypt_bytes", side_effect=RuntimeError("leaks hunter2")):
            out = self.add_note()
        self.assertIn("RuntimeError", out)
        self.assertNotIn("hunter2", out)
        self.assertEqual(Path("Bunker.mmf").read_bytes(), before)
        self.assertEqual(sorted(os.listdir(".")), ["Bunker.mmf"])

    def test_wrong_key_load_error_never_removes_files(self):
        self.seed(self.foreign_db())
        for name in ("bunker.salt", "bunker.cfg", "config.cfg"):
            Path(name).write_bytes(b"x")
        before = Path("Bunker.mmf").read_bytes()
        self.key = random_key()
        out = self.drive(MB.mobile_note_manager, "1", "0")
        self.assertIn("InvalidTag", out)
        self.assertEqual(Path("Bunker.mmf").read_bytes(), before)
        for name in ("bunker.salt", "bunker.cfg", "config.cfg"):
            self.assertTrue(os.path.exists(name))


class Login(MobileCase):
    SALT = b"s" * 32

    def setUp(self):
        super().setUp()
        self.ui_config = {"attempts": 0, "max_attempts": 3,
                          "disable_ipv4": True, "current_timeout": 60}
        for p in (mock.patch.object(MB, "load_ui_config", lambda: dict(self.ui_config)),
                  mock.patch.object(MB, "load_salt", lambda *a, **k: self.SALT),
                  mock.patch.object(MB, "title_with_label", lambda *a, **k: None)):
            p.start()
            self.addCleanup(p.stop)

    def vault_with(self, derive):
        """A complete vault: salt, bunker.cfg (salt + verifier), integrity
        record and database, as setup creates them."""
        import base64, json
        import main.INITIALIZE as I
        import main.VAULT_FILES as VF
        key = derive("correct-horse", self.SALT)
        Path("bunker.salt").write_bytes(self.SALT)
        cfg = {"salt": base64.b64encode(self.SALT).decode(),
               "verifier": base64.b64encode(I.vault.encrypt_data(b"BUNKER_VERIFIED", key)).decode()}
        Path("bunker.cfg").write_bytes(I.vault.encrypt_data(json.dumps(cfg).encode(), key))
        VF.record_integrity()
        S.save({"n": S.make_note("t", "c", key)}, key)
        return key

    def test_three_wrong_passwords_end_the_session_and_touch_nothing(self):
        self.vault_with(S.derive_key)
        before = Path("Bunker.mmf").read_bytes()
        Path("bunker.salt").write_bytes(self.SALT)
        self.passwords.extend(["bad-1", "bad-2", "bad-3"])
        out = io.StringIO()
        with mock.patch("builtins.input", side_effect=["n", "n", "n"]), \
                contextlib.redirect_stdout(out):
            MB.main("mobile")
        self.assertIn("Maximum login attempts exceeded", out.getvalue())
        self.assertEqual(Path("Bunker.mmf").read_bytes(), before)
        self.assertTrue(os.path.exists("bunker.salt"))

    def test_login_then_add_note_is_visible_to_desktop(self):
        key = self.vault_with(S.derive_key)
        self.passwords.append("correct-horse")
        answers = ["n",                      # hide password
                   "1",                      # notes
                   "2", "From mobile", "hello", ".done", "n", "", "n", "0",
                   "0"]                      # exit
        with mock.patch("builtins.input", side_effect=answers), \
                contextlib.redirect_stdout(io.StringIO()):
            MB.main("mobile")
        notes = [e for e in S.load(key).values() if S.is_note(e)]
        titles = sorted(D.decode_and_decrypt("title", e, key) for e in notes)
        self.assertEqual(titles, ["From mobile", "t"])


if __name__ == "__main__":
    unittest.main()
