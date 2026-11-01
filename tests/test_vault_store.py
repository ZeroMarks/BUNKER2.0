"""VAULT_STORE: desktop-format compatibility and atomic, owner-only saves."""
import base64
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import main.DESKTOP as D
import main.INITIALIZE as I
from main import VAULT_STORE as S


def random_key():
    return base64.urlsafe_b64encode(os.urandom(32))


class StoreCase(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)
        self.key = random_key()

    def tearDown(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()


class DesktopCompatibility(StoreCase):
    def test_derive_key_matches_desktop(self):
        salt = os.urandom(32)
        self.assertEqual(S.derive_key("pw-123456", salt),
                         I.vault.derive_key_hybrid("pw-123456", salt, "pw-123456"))

    def test_profile_written_here_is_readable_by_desktop(self):
        p = S.make_profile("example.com", "bob", "b@example.com", "s3cret!", self.key, favorite=True)
        for field, want in (("domain", "example.com"), ("username", "bob"),
                            ("email", "b@example.com"), ("password", "s3cret!")):
            self.assertEqual(D.decode_and_decrypt(field, p, self.key), want)
        self.assertIs(p["favorite"], True)
        self.assertTrue(S.is_profile(p))
        self.assertFalse(S.is_note(p))

    def test_profile_written_by_desktop_encoding_is_readable_here(self):
        enc = lambda v: base64.b64encode(I.vault.encrypt_data(v.encode(), self.key)).decode()
        entry = {"domain": enc("d.org"), "email": enc("e@d.org"),
                 "username": enc("u"), "password": enc("pw"), "favorite": False}
        self.assertEqual(S.read_profile(entry, self.key),
                         {"domain": "d.org", "username": "u", "email": "e@d.org",
                          "password": "pw", "favorite": False})

    def test_note_written_here_is_readable_by_desktop(self):
        n = S.make_note("Title", "line1\nline2", self.key, tags=[" a ", "b", ""])
        dn = D.decrypt_note(n, self.key)
        self.assertEqual(dn["title"], "Title")
        self.assertEqual(dn["content"], "line1\nline2")
        self.assertEqual(dn["tags"], ["a", "b"])
        self.assertIs(dn["favorite"], False)
        self.assertIs(dn["private"], False)
        self.assertTrue(S.is_note(n))

    def test_note_without_tags_gets_na_and_private_gets_private_tag(self):
        self.assertEqual(D.decrypt_note(S.make_note("t", "c", self.key), self.key)["tags"], ["N/A"])
        n = S.make_note("t", "c", self.key, tags=["x"], private=True)
        self.assertEqual(D.decrypt_note(n, self.key)["tags"], ["PRIVATE"])
        self.assertIs(n["private"], True)

    def test_note_written_by_desktop_encoding_is_readable_here(self):
        enc = lambda v: base64.b64encode(I.vault.encrypt_data(v.encode(), self.key)).decode()
        entry = {"title": enc("T"), "content": enc("C"), "tags": [enc("N/A")],
                 "favorite": True, "private": False}
        self.assertEqual(S.read_note(entry, self.key),
                         {"title": "T", "content": "C", "tags": ["N/A"],
                          "favorite": True, "private": False})

    def test_file_is_readable_by_desktop_loader(self):
        db = {S.new_id(): S.make_profile("a.com", "u", "e", "p", self.key)}
        S.save(db, self.key)
        self.assertEqual(I.loadDatabase(self.key), db)

    def test_file_written_by_desktop_save_is_readable_here(self):
        db = {S.new_id(): S.make_note("t", "c", self.key)}
        with mock.patch.object(I.vault, "manage_config", return_value=None):
            self.assertTrue(I.saveDatabase(db, self.key))
        self.assertEqual(S.load(self.key), db)

    def test_update_changes_only_requested_fields_and_keeps_extras(self):
        p = S.make_profile("a.com", "u", "e", "p", self.key)
        p["extra"] = {"x": 1}
        q = S.update_profile(p, self.key, password="new")
        self.assertEqual(q["extra"], {"x": 1})
        self.assertEqual(q["domain"], p["domain"])
        self.assertEqual(S.read_profile(q, self.key)["password"], "new")
        n = S.make_note("t", "c", self.key, tags=["a"])
        m = S.update_note(n, self.key, content="c2")
        self.assertEqual(m["title"], n["title"])
        self.assertEqual(m["tags"], n["tags"])
        self.assertEqual(S.read_note(m, self.key)["content"], "c2")
        m = S.update_note(m, self.key, private=True)
        self.assertEqual(S.read_note(m, self.key)["tags"], ["PRIVATE"])


class SaveBehaviour(StoreCase):
    def test_save_is_owner_only_and_leaves_no_temp_files(self):
        S.save({S.new_id(): S.make_note("t", "c", self.key)}, self.key)
        mode = stat.S_IMODE(os.stat("Bunker.mmf").st_mode)
        self.assertEqual(mode, 0o600)
        self.assertEqual(os.listdir("."), ["Bunker.mmf"])

    def test_resave_over_existing_file_stays_0600(self):
        Path("Bunker.mmf").write_bytes(b"old")
        os.chmod("Bunker.mmf", 0o644)
        S.save({}, self.key)
        self.assertEqual(stat.S_IMODE(os.stat("Bunker.mmf").st_mode), 0o600)

    def test_failure_before_replace_keeps_previous_file_identical(self):
        S.save({S.new_id(): S.make_note("t", "c", self.key)}, self.key)
        before = Path("Bunker.mmf").read_bytes()
        with mock.patch("os.fsync", side_effect=OSError("disk gone")):
            with self.assertRaises(OSError):
                S.save({}, self.key)
        self.assertEqual(Path("Bunker.mmf").read_bytes(), before)
        self.assertEqual(os.listdir("."), ["Bunker.mmf"])

    def test_failure_during_replace_keeps_previous_file_identical(self):
        S.save({S.new_id(): S.make_note("t", "c", self.key)}, self.key)
        before = Path("Bunker.mmf").read_bytes()
        with mock.patch("os.replace", side_effect=OSError("nope")):
            with self.assertRaises(OSError):
                S.save({}, self.key)
        self.assertEqual(Path("Bunker.mmf").read_bytes(), before)
        self.assertEqual(os.listdir("."), ["Bunker.mmf"])

    def test_failure_while_writing_keeps_previous_file_identical(self):
        S.save({S.new_id(): S.make_note("t", "c", self.key)}, self.key)
        before = Path("Bunker.mmf").read_bytes()
        with mock.patch.object(S, "encrypt_bytes", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                S.save({}, self.key)
        self.assertEqual(Path("Bunker.mmf").read_bytes(), before)

    def test_save_refuses_foreign_shapes(self):
        for bad in ({"notes": []}, {"a": "str"}, [], {"a": None}):
            with self.assertRaises(ValueError):
                S.save(bad, self.key)
        self.assertFalse(os.path.exists("Bunker.mmf"))

    def test_load_errors_are_not_swallowed(self):
        with self.assertRaises(FileNotFoundError):
            S.load(self.key)
        S.save({}, self.key)
        with self.assertRaises(Exception):
            S.load(random_key())
        Path("Bunker.mmf").write_bytes(S.encrypt_bytes(b"[1]", self.key))
        with self.assertRaises(ValueError):
            S.load(self.key)

    def test_unknown_entries_survive_load_save(self):
        weird = {"future": {"a": [1, 2], "b": None}, "password": "x"}
        db = {"id-1": weird, "id-2": S.make_note("t", "c", self.key)}
        S.save(db, self.key)
        self.assertEqual(S.load(self.key)["id-1"], weird)
        self.assertEqual(json.loads(S.decrypt_bytes(Path("Bunker.mmf").read_bytes(), self.key)), db)


if __name__ == "__main__":
    unittest.main()
