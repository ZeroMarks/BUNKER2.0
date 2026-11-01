"""End-to-end desktop flows with real encryption: add a profile, view its
password, copy it. Only terminal input and the clipboard are faked.

These walk the code paths that route secrets through SECURE_IO, so a broken
reveal/copy/error path in DESKTOP.py shows up here.
"""
import contextlib
import io
import os
import tempfile
import unittest
from unittest import mock

import main.DESKTOP as D
import main.INITIALIZE as I
from main import SECURE_IO
from tests.test_vault_integrity import PASSWORD, key_for, quiet, run_setup

SECRET = "Sup3r-secret!pass"
ANSWERS = {
    "Website domain": "example.com",
    "Email address": "me@example.com",
    "Username": "me",
    "show your password while typing": "y",
    "Enter the password": SECRET,
    "favorite": "n",
    "Select the profile": "1",
    "Press 'enter'": "",
}


def responder(view_choice):
    def answer(prompt, *_a, **_k):
        if "Type 'v' to view" in prompt:
            return view_choice
        for key, value in ANSWERS.items():
            if key in prompt:
                return value
        raise AssertionError(f"unexpected prompt: {prompt!r}")
    return answer


class ProfileFlows(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)
        self.addCleanup(self._restore)
        self.assertTrue(run_setup())
        self.key = key_for(PASSWORD)
        self.clip = {"v": ""}
        SECURE_IO.set_clipboard_backend(lambda t: self.clip.update(v=t), lambda: self.clip["v"])
        self.addCleanup(SECURE_IO.set_clipboard_backend, None, None)
        self.addCleanup(SECURE_IO.clear_clipboard_if_ours)

    def _restore(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def _run(self, func, view_choice=""):
        out = io.StringIO()
        with mock.patch.object(D, "timeoutInput", responder(view_choice)), \
             mock.patch.object(D, "timeout_getpass", responder(view_choice)), \
             mock.patch.object(D, "clear_screen", quiet), \
             mock.patch.object(D, "displayHeader", quiet), \
             contextlib.redirect_stdout(out):
            func(self.key, I.loadDatabase(self.key))
        return out.getvalue()

    def _add(self):
        self._run(D.addProfile)
        db = I.loadDatabase(self.key)
        self.assertEqual(len(db), 1)
        return db

    def test_added_profile_is_encrypted_and_readable(self):
        db = self._add()
        entry = next(iter(db.values()))
        self.assertNotIn(SECRET, repr(entry))  # never stored in clear
        self.assertEqual(D.decode_and_decrypt("password", entry, self.key), SECRET)
        self.assertEqual(D.decode_and_decrypt("domain", entry, self.key), "example.com")
        with open("Bunker.mmf", "rb") as f:
            self.assertNotIn(SECRET.encode(), f.read())

    def test_view_shows_password_only_when_asked(self):
        self._add()
        shown = self._run(D.readAllProfiles, view_choice="v")
        self.assertIn(SECRET, shown)
        copied = self._run(D.readAllProfiles, view_choice="c")
        self.assertNotIn(SECRET, copied)

    def test_copy_puts_password_on_clipboard_and_it_is_cleared(self):
        self._add()
        out = self._run(D.readAllProfiles, view_choice="c")
        self.assertEqual(self.clip["v"], SECRET)
        self.assertIn("cleared", out)
        self.assertTrue(SECURE_IO.clear_clipboard_if_ours())
        self.assertEqual(self.clip["v"], "")


NOTE_BODY = "the launch codes are 0000"


def note_responder(private, view_choice):
    answers = {
        "title for the note": "Private plans" if private else "Groceries",
        "tags for the note": "home, todo",
        "content of the note": NOTE_BODY,
        "as a favorite": "n",
        "as private": "y" if private else "n",
        "Select the note": "1",
        "This is a private note": "view",
        "Press 'enter'": "",
    }

    def answer(prompt, *_a, **_k):
        if "Type 'v' to view full content" in prompt:
            return view_choice
        for key, value in answers.items():
            if key in prompt:
                return value
        raise AssertionError(f"unexpected prompt: {prompt!r}")
    return answer


class NoteFlows(ProfileFlows):
    def _note_run(self, func, private, view_choice=""):
        out = io.StringIO()
        with mock.patch.object(D, "timeoutInput", note_responder(private, view_choice)), \
             mock.patch.object(D, "clear_screen", quiet), \
             mock.patch.object(D, "displayHeader", quiet), \
             contextlib.redirect_stdout(out):
            func(self.key, I.loadDatabase(self.key))
        return out.getvalue()

    # The profile tests are inherited; skip re-running them here.
    test_added_profile_is_encrypted_and_readable = None
    test_view_shows_password_only_when_asked = None
    test_copy_puts_password_on_clipboard_and_it_is_cleared = None

    def test_private_note_is_hidden_in_list_and_shown_on_view(self):
        self._note_run(D.addNote, private=True)
        db = I.loadDatabase(self.key)
        entry = next(iter(db.values()))
        self.assertTrue(entry["private"])
        self.assertNotIn(NOTE_BODY, repr(entry))
        out = self._note_run(D.displayAllNotes, private=True, view_choice="v")
        listing, banner, revealed = out.partition("PRIVATE NOTE ACCESS")
        self.assertTrue(banner, "private note was not gated")
        self.assertIn("[PRIVATE]", listing)
        self.assertNotIn(NOTE_BODY, listing)   # hidden in the list
        self.assertIn(NOTE_BODY, revealed)     # shown only after typing view

    def test_note_copy_goes_to_clipboard_not_screen(self):
        self._note_run(D.addNote, private=False)
        out = self._note_run(D.displayAllNotes, private=False, view_choice="c")
        self.assertEqual(self.clip["v"], NOTE_BODY)
        import re  # not printed on copy (with or without colours)
        self.assertIsNone(re.search(r"Content:\s*(\x1b\[[0-9;]*m)?" + re.escape(NOTE_BODY), out))


if __name__ == "__main__":
    unittest.main()
