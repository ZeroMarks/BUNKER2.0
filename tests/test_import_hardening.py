"""Import hardening: damaged and hostile export files, and re-imports.

Properties checked with real encryption (only terminal input is faked):
- An import either adds only well-formed entries or changes nothing. It
  never raises, never alters an existing entry, and the vault always
  opens afterwards.
- Importing the same file twice adds nothing the second time.
- Terminal control characters from a file are shown escaped, and stored
  exactly as written.
- A failed save leaves the vault on disk and in memory as it was.
"""
import base64
import contextlib
import copy
import io
import json
import os
import random
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import main.DESKTOP as D
import main.IMPORT_FILES as F
import main.INITIALIZE as I
from tests.test_fuzz_vault_input import mutate
from tests.test_vault_integrity import PASSWORD, key_for, quiet, run_setup

SEED = 20261102
PASSPHRASE = "import passphrase 2026"

PROFILES = {
    "1": {"domain": "example.com", "email": "me@example.com", "username": "me",
          "password": "Sup3r-secret!", "favorite": True},
    "2": {"domain": "bank.test", "username": "acct42", "password": "another pw 9", "favorite": False},
}
NOTES = {
    "1": {"title": "Groceries", "content": "milk, eggs, bread, tea", "tags": ["home"],
          "favorite": False, "private": False},
    "2": {"title": "Plans", "content": "the launch codes are 0000", "tags": ["PRIVATE"],
          "favorite": True, "private": True},
}


def export_doc(section, entries):
    return {"watermark": F.WATERMARK, section: copy.deepcopy(entries)}


def responder(filename, *, show_passwords="n", confirm="y", passphrase=PASSPHRASE, log=None):
    table = {
        "Choose file to import": filename,
        "show your password while typing": "y",
        "passphrase used for encryption": passphrase,
        "display passwords": show_passwords,
        "import these": confirm,
        "Press 'enter'": "",
    }

    def answer(prompt, *_a, **_k):
        if log is not None:
            log.append(prompt)
        for key, value in table.items():
            if key in prompt:
                return value
        raise AssertionError(f"unexpected prompt: {prompt!r}")
    return answer


class ImportCase(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.addCleanup(os.chdir, self._cwd)
        os.chdir(self.dir)

    @classmethod
    def setUpClass(cls):
        # One real vault for the whole class; each test starts from a copy.
        cls._template = tempfile.mkdtemp()
        cwd = os.getcwd()
        os.chdir(cls._template)
        try:
            assert run_setup()
            cls.key = key_for(PASSWORD)
        finally:
            os.chdir(cwd)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._template, True)

    def fresh_vault(self, db=None):
        for name in os.listdir(self._template):
            shutil.copy(os.path.join(self._template, name), name)
        if db is not None:
            with contextlib.redirect_stdout(io.StringIO()):
                assert I.saveDatabase(db, self.key)

    def run_import(self, func, filename, db=None, **kw):
        out = io.StringIO()
        answer = responder(filename, **kw)
        if db is None:
            db = I.loadDatabase(self.key)
        with mock.patch.object(D, "timeoutInput", answer), \
             mock.patch.object(D, "timeout_getpass", answer), \
             mock.patch("builtins.input", answer), \
             mock.patch.object(D, "clear_screen", quiet), \
             mock.patch.object(D, "displayHeader", quiet), \
             contextlib.redirect_stdout(out):
            result = func(self.key, db)
        return result, out.getvalue(), db

    def write(self, name, doc):
        Path(name).write_text(json.dumps(doc), encoding="utf-8")

    def vault(self):
        return I.loadDatabase(self.key)

    def decrypted(self, kind):
        out = []
        for entry in self.vault().values():
            if kind == "profiles" and F.is_profile(entry):
                out.append(tuple(D.decode_and_decrypt(f, entry, self.key)
                                 for f in ("domain", "email", "username", "password")))
            elif kind == "notes" and F.is_note(entry):
                n = D.decrypt_note(entry, self.key)
                out.append((n["title"], n["content"], tuple(n["tags"])))
        return sorted(out)


class ReImport(ImportCase):
    def test_profiles_twice_adds_nothing_the_second_time(self):
        self.fresh_vault()
        self.write("p.json", export_doc("profiles", PROFILES))
        self.run_import(D.importProfiles, "p.json")
        first = self.vault()
        self.assertEqual(len(first), 2)
        _, out, _ = self.run_import(D.importProfiles, "p.json")
        self.assertEqual(self.vault(), first)
        self.assertIn("already in your vault", out)

    def test_notes_twice_adds_nothing_the_second_time(self):
        self.fresh_vault()
        self.write("n.json", export_doc("notes", NOTES))
        self.run_import(D.importNotes, "n.json")
        first = self.vault()
        self.assertEqual(len(first), 2)
        _, out, _ = self.run_import(D.importNotes, "n.json")
        self.assertEqual(self.vault(), first)
        self.assertIn("already in your vault", out)

    def test_encrypted_reimport_is_also_deduplicated(self):
        self.fresh_vault()
        self.write("p.json", export_doc("profiles", PROFILES))
        self.run_import(D.importProfiles, "p.json")
        # Export the vault encrypted, then import it back into itself.
        answers = {"export all profiles": "y", "export as encrypted": "y",
                   "see the password as you type": "y", "passphrase for encryption": PASSPHRASE,
                   "Confirm passphrase": PASSPHRASE, "file name to save profiles": "enc.json",
                   "Continue with export": "y", "Press 'enter'": ""}
        answer = lambda p, *_a, **_k: next(v for k, v in answers.items() if k in p)
        with mock.patch.object(D, "timeoutInput", answer), mock.patch.object(D, "timeout_getpass", answer), \
             mock.patch.object(D, "clear_screen", quiet), mock.patch.object(D, "displayHeader", quiet), \
             contextlib.redirect_stdout(io.StringIO()):
            D.exportProfiles(self.key, self.vault())
        before = self.vault()
        self.run_import(D.importProfiles, "enc.json")
        self.assertEqual(self.vault(), before)

    def test_only_the_new_entries_of_a_partly_known_file_are_added(self):
        self.fresh_vault()
        self.write("p.json", export_doc("profiles", {"1": PROFILES["1"]}))
        self.run_import(D.importProfiles, "p.json")
        self.write("p.json", export_doc("profiles", PROFILES))
        _, out, _ = self.run_import(D.importProfiles, "p.json")
        self.assertEqual(len(self.vault()), 2)
        self.assertIn("1 new profiles", out)

    def test_repeats_inside_one_file_are_imported_once(self):
        self.fresh_vault()
        self.write("p.json", export_doc("profiles", {"a": PROFILES["1"], "b": PROFILES["1"]}))
        self.run_import(D.importProfiles, "p.json")
        self.assertEqual(len(self.vault()), 1)

    def test_changed_password_is_added_alongside_and_reported(self):
        self.fresh_vault()
        self.write("p.json", export_doc("profiles", PROFILES))
        self.run_import(D.importProfiles, "p.json")
        changed = copy.deepcopy(PROFILES["1"])
        changed["password"] = "rotated-pw-2"
        self.write("p.json", export_doc("profiles", {"1": changed}))
        _, out, _ = self.run_import(D.importProfiles, "p.json")
        passwords = {p[3] for p in self.decrypted("profiles")}
        self.assertEqual(passwords, {"Sup3r-secret!", "another pw 9", "rotated-pw-2"})
        self.assertIn("same site and login", out)

    def test_in_memory_vault_matches_disk_after_import(self):
        self.fresh_vault()
        self.write("p.json", export_doc("profiles", PROFILES))
        _, _, db = self.run_import(D.importProfiles, "p.json")
        self.assertEqual(db, self.vault())


class HostileContent(ImportCase):
    EVIL = "evil.com\x1b]52;c;Y3VybCBldmlsLnNoIHwgYmFzaA==\x07\x1b[2J‮"

    def test_control_characters_are_shown_escaped_and_stored_exactly(self):
        self.fresh_vault()
        doc = export_doc("profiles", {"1": dict(PROFILES["1"], domain=self.EVIL, password="pw\x1b[8m")})
        self.write("p.json", doc)
        _, out, _ = self.run_import(D.importProfiles, "p.json", show_passwords="y")
        self.assertNotIn("\x1b]", out)
        self.assertNotIn("\x1b[2J", out)
        self.assertNotIn("‮", out)
        self.assertIn("\\x1b]52", out)
        self.assertIn("terminal control characters", out)
        stored = self.decrypted("profiles")
        self.assertEqual([p[0] for p in stored], [self.EVIL])
        self.assertEqual([p[3] for p in stored], ["pw\x1b[8m"])

    def test_note_titles_and_tags_are_escaped_too(self):
        self.fresh_vault()
        self.write("n.json", export_doc("notes", {"1": {"title": "t\x1b[31m", "content": "c\x9b2J",
                                                     "tags": ["x\x1b[0m"]}}))
        _, out, _ = self.run_import(D.importNotes, "n.json")
        self.assertNotIn("\x1b[31m", out)
        self.assertNotIn("\x9b", out)
        self.assertEqual(self.decrypted("notes"), [("t\x1b[31m", "c\x9b2J", ("x\x1b[0m",))])


class Rejections(ImportCase):
    def assert_rejected(self, func, filename, expect):
        self.fresh_vault()
        before = Path("Bunker.mmf").read_bytes()
        result, out, _ = self.run_import(func, filename)
        self.assertIs(result, False)
        self.assertIn(expect, out)
        self.assertEqual(Path("Bunker.mmf").read_bytes(), before)

    def test_wrong_kind_of_export(self):
        self.write("n.json", export_doc("notes", NOTES))
        self.assert_rejected(D.importProfiles, "n.json", "no 'profiles' section")

    def test_top_level_list(self):
        Path("l.json").write_text("[1, 2]", encoding="utf-8")
        self.assert_rejected(D.importNotes, "l.json", "not a BUNKER export")

    def test_deep_nesting(self):
        Path("d.json").write_text("[" * 100000 + "]" * 100000, encoding="utf-8")
        self.assert_rejected(D.importProfiles, "d.json", "nested too deeply")

    def test_not_utf8(self):
        Path("b.json").write_bytes(b"\xff\xfe{}")
        self.assert_rejected(D.importProfiles, "b.json", "not UTF-8")

    def test_oversized(self):
        self.write("big.json", export_doc("profiles", PROFILES))
        with mock.patch.object(F, "MAX_IMPORT_BYTES", 10), \
             mock.patch.object(D, "read_import_file", lambda p: F.read_import_file(p, limit=10)):
            self.assert_rejected(D.importProfiles, "big.json", "too large")

    def test_damaged_encrypted_wrapper(self):
        self.write("e.json", {"watermark": F.WATERMARK, "salt": 5, "verifier": "!!", "data": "x"})
        self.assert_rejected(D.importNotes, "e.json", "damaged")

    def test_wrong_typed_fields_are_skipped_and_explained(self):
        self.fresh_vault()
        bad = {"1": PROFILES["1"], "2": {"domain": ["x"], "password": "p"},
               "3": {"domain": "d", "password": 7}, "4": {"domain": "d", "password": "p", "favorite": "yes"},
               "5": "not a profile", "6": {"domain": "  ", "password": "p"}}
        self.write("p.json", export_doc("profiles", bad))
        _, out, _ = self.run_import(D.importProfiles, "p.json")
        self.assertEqual(len(self.vault()), 1)
        self.assertIn("5 could not be read", out)
        self.assertIn("'favorite' must be true or false", out)

    def test_vault_not_loaded_is_never_saved_over(self):
        self.fresh_vault({"keep": {"domain": "x" * 80, "password": "y" * 80, "favorite": False}})
        before = Path("Bunker.mmf").read_bytes()
        self.write("n.json", export_doc("notes", NOTES))
        result, out, _ = self.run_import(D.importNotes, "n.json", db=b"not a dict")
        self.assertIs(result, False)
        self.assertIn("vault is not loaded", out)
        self.assertEqual(Path("Bunker.mmf").read_bytes(), before)

    def test_failed_save_changes_nothing(self):
        self.fresh_vault()
        before = Path("Bunker.mmf").read_bytes()
        self.write("p.json", export_doc("profiles", PROFILES))
        db = self.vault()
        snapshot = copy.deepcopy(db)
        with mock.patch.object(D, "saveDatabase", return_value=False):
            _, out, db = self.run_import(D.importProfiles, "p.json", db=db)
        self.assertEqual(db, snapshot)
        self.assertEqual(Path("Bunker.mmf").read_bytes(), before)
        self.assertIn("Nothing was imported", out)

    def test_timeout_at_show_passwords_logs_out_instead_of_looping(self):
        self.fresh_vault()
        self.write("p.json", export_doc("profiles", PROFILES))
        with mock.patch.object(D, "timeoutGlobalCode", "\x00TIMEOUT"):
            result, _, _ = self.run_import(D.importProfiles, "p.json", show_passwords="\x00TIMEOUT")
        self.assertIs(result, True)
        self.assertEqual(self.vault(), {})


def structural_mutation(rng, doc, section):
    """Replace, delete or retype one random part of an export document."""
    doc = copy.deepcopy(doc)
    junk = [None, 0, -1, 2 ** 70, 1.5, True, "", "\x1b[2J", [], {}, ["a", 1], {"x": {}}, "A" * 5000]
    entries = doc.get(section)
    choice = rng.randrange(7)
    if choice == 0:
        doc[section] = rng.choice(junk)
    elif choice == 1 and isinstance(entries, dict) and entries:
        entries[rng.choice(list(entries))] = rng.choice(junk)
    elif isinstance(entries, dict) and entries:
        entry = entries[rng.choice(list(entries))]
        if isinstance(entry, dict) and entry:
            field = rng.choice(list(entry) + ["extra"])
            if choice in (2, 3, 4):
                entry[field] = rng.choice(junk)
            else:
                entry.pop(field, None)
    return doc


class FuzzImport(ImportCase):
    ROUNDS = 40

    def check_property(self, func, kind, filename, base_db):
        """After any import attempt: no exception, old entries untouched, vault opens,
        every new entry decrypts to text."""
        with contextlib.redirect_stdout(io.StringIO()):
            assert I.saveDatabase(base_db, self.key)
        result, _, _ = self.run_import(func, filename)
        self.assertIn(result, (True, False))
        after = self.vault()
        for k, v in base_db.items():
            self.assertEqual(after.get(k), v, "an existing entry was changed")
        added = [after[k] for k in after.keys() - base_db.keys()]
        for entry in added:
            fields = ("domain", "email", "username", "password") if kind == "profiles" else ("title", "content")
            for f in fields:
                self.assertIsInstance(D.decode_and_decrypt(f, entry, self.key), str)
            self.assertIsInstance(entry["favorite"], bool)
        return len(added)

    def _fuzz(self, func, kind, entries, seed):
        self.fresh_vault()
        rng = random.Random(seed)
        good = json.dumps(export_doc(kind, entries)).encode()
        added_any = 0
        # Control round: the unmodified file really imports.
        Path("f.json").write_bytes(good)
        self.assertEqual(self.check_property(func, kind, "f.json", {}), len(entries))
        base = self.vault()
        for i in range(self.ROUNDS):
            if i % 2:
                Path("f.json").write_bytes(mutate(rng, good))
            else:
                doc = structural_mutation(rng, export_doc(kind, entries), kind)
                doc = structural_mutation(rng, doc, kind)
                Path("f.json").write_text(json.dumps(doc), encoding="utf-8")
            self.fresh_vault()
            added_any += self.check_property(func, kind, "f.json", {})
            # Against a vault that already holds the originals, a mutated file never
            # re-adds them.
            self.check_property(func, kind, "f.json", base)
        return added_any

    def test_fuzz_profiles(self):
        self._fuzz(D.importProfiles, "profiles", PROFILES, SEED)

    def test_fuzz_notes(self):
        self._fuzz(D.importNotes, "notes", NOTES, SEED + 1)

    def test_fuzz_encrypted_wrapper(self):
        """Damaged encrypted exports are refused cleanly (the passphrase is right)."""
        self.fresh_vault()
        self.write("p.json", export_doc("profiles", PROFILES))
        answers = {"export all profiles": "y", "export as encrypted": "y",
                   "see the password as you type": "y", "passphrase for encryption": PASSPHRASE,
                   "Confirm passphrase": PASSPHRASE, "file name to save profiles": "enc.json",
                   "Continue with export": "y", "Press 'enter'": ""}
        answer = lambda p, *_a, **_k: next(v for k, v in answers.items() if k in p)
        self.run_import(D.importProfiles, "p.json")
        with mock.patch.object(D, "timeoutInput", answer), mock.patch.object(D, "timeout_getpass", answer), \
             mock.patch.object(D, "clear_screen", quiet), mock.patch.object(D, "displayHeader", quiet), \
             contextlib.redirect_stdout(io.StringIO()):
            D.exportProfiles(self.key, self.vault())
        wrapper = json.loads(Path("enc.json").read_text(encoding="utf-8"))
        rng = random.Random(SEED + 2)
        ciphertext = base64.b64decode(wrapper["data"])
        for _ in range(6):  # each round derives a key (slow), keep it small
            damaged = dict(wrapper, data=base64.b64encode(mutate(rng, ciphertext)).decode())
            self.write("bad.json", damaged)
            self.fresh_vault()
            before = Path("Bunker.mmf").read_bytes()
            result, _, _ = self.run_import(D.importProfiles, "bad.json")
            self.assertIs(result, False)
            self.assertEqual(Path("Bunker.mmf").read_bytes(), before)


class Printable(unittest.TestCase):
    def test_escapes_every_control_class(self):
        for ch in ("\x00", "\x07", "\x1b", "\x7f", "\x9b", "\x9d", "‮", "⁦"):
            self.assertNotIn(ch, F.printable(f"a{ch}b"))
            self.assertTrue(F.has_controls(f"a{ch}b"))

    def test_plain_text_unchanged(self):
        for text in ("example.com", "pässwörd ✓ 密码", "a b"):
            self.assertEqual(F.printable(text), text)
            self.assertFalse(F.has_controls(text))

    def test_newlines_flattened_and_limit_applied(self):
        self.assertEqual(F.printable("a\nb\tc"), "a b c")
        self.assertEqual(F.printable("abcdef", 3), "abc...")


if __name__ == "__main__":
    unittest.main()
