"""Mobile edit, delete and favorite when another BUNKER window changed the
entry after the list was shown.

The mobile screens list the entries, the user picks one and answers a few
prompts, and only then is the vault reloaded and changed. In between,
another window may have removed or edited that entry. These tests make that
happen at a chosen prompt and check that:

* a removed entry gives a plain message, not "KeyError", and never a false
  "deleted successfully";
* an entry edited elsewhere is not deleted from a list that showed the old
  version;
* an edit here only writes the fields the user changed, so the other
  window's edit to the other fields survives;
* the favorite star flips the value in the vault now, not the listed one.
"""
import contextlib
import io
from unittest import mock

import main.MOBILE as MB
from main import VAULT_STORE as S
from tests.test_mobile_shared_vault import MobileCase

REMOVED = "removed in another BUNKER window"
CHANGED = "changed in another BUNKER window"


class StaleEntries(MobileCase):
    def setUp(self):
        super().setUp()
        self.seed({
            "n1": S.make_note("Shopping", "milk", self.key, tags=["a"]),
            "p1": S.make_profile("example.com", "bob", "b@x.org", "pw-1", self.key),
        })

    def drive(self, manager, *answers, passwords=()):
        """Like MobileCase.drive, but an answer may be a function: it runs
        when that prompt is reached (the other window's change) and its
        return value is typed."""
        self.passwords.extend(passwords)
        queue = list(answers)

        def answer(*_a, **_k):
            item = queue.pop(0)
            return item() if callable(item) else item

        out = io.StringIO()
        with mock.patch("builtins.input", answer), contextlib.redirect_stdout(out):
            manager(self.key, "mobile")
        return out.getvalue()

    def elsewhere(self, mutate, then=""):
        def act():
            S.modify(self.key, mutate)
            return then
        return act

    def remove(self, entry_id, then=""):
        return self.elsewhere(lambda db: db.pop(entry_id), then)

    # -- notes
    def test_edit_note_removed_elsewhere(self):
        screen = self.drive(MB.mobile_note_manager, "3", "1",
                            self.remove("n1", "New title"), "", "", "", "", "0")
        self.assertIn(REMOVED, screen)
        self.assertNotIn("KeyError", screen)
        self.assertNotIn("updated successfully", screen)
        self.assertEqual(list(self.db()), ["p1"])  # not brought back

    def test_delete_note_removed_elsewhere_does_not_claim_success(self):
        screen = self.drive(MB.mobile_note_manager, "4", "1", self.remove("n1", "y"), "0")
        self.assertIn(REMOVED, screen)
        self.assertNotIn("deleted successfully", screen)

    def test_delete_note_edited_elsewhere_is_not_deleted(self):
        edit = self.elsewhere(lambda db: db.__setitem__(
            "n1", S.update_note(db["n1"], self.key, content="milk, eggs, do not lose")), "y")
        screen = self.drive(MB.mobile_note_manager, "4", "1", edit, "0")
        self.assertIn(CHANGED, screen)
        self.assertNotIn("deleted successfully", screen)
        self.assertEqual(self.notes()["n1"]["content"], "milk, eggs, do not lose")

    def test_edit_note_keeps_fields_changed_elsewhere(self):
        """Title changed here; content, favorite and private changed in the
        other window while the prompts were open."""
        edit = self.elsewhere(lambda db: db.__setitem__(
            "n1", S.update_note(db["n1"], self.key, content="from the desktop",
                                favorite=True)), "Groceries")
        screen = self.drive(MB.mobile_note_manager, "3", "1", edit, "", "", "", "", "0")
        self.assertIn("updated successfully", screen)
        n = self.notes()["n1"]
        self.assertEqual((n["title"], n["content"], n["favorite"], n["tags"]),
                         ("Groceries", "from the desktop", True, ["a"]))

    def test_edit_note_still_changes_favorite_and_private_when_asked(self):
        self.drive(MB.mobile_note_manager, "3", "1", "", "", "y", "y", "0")
        n = self.notes()["n1"]
        self.assertEqual((n["private"], n["tags"], n["favorite"]), (True, ["PRIVATE"], True))
        self.drive(MB.mobile_note_manager, "3", "1", "", "", "n", "", "n", "0")
        n = self.notes()["n1"]
        self.assertEqual((n["private"], n["tags"], n["favorite"]), (False, ["N/A"], False))

    # -- passwords
    def test_edit_password_removed_elsewhere(self):
        screen = self.drive(MB.mobile_password_manager, "3", "1",
                            self.remove("p1", ""), "alice", "", "0", passwords=[""])
        self.assertIn(REMOVED, screen)
        self.assertNotIn("KeyError", screen)
        self.assertEqual(list(self.db()), ["n1"])

    def test_delete_password_removed_elsewhere_does_not_claim_success(self):
        screen = self.drive(MB.mobile_password_manager, "4", "1", self.remove("p1", "y"), "0")
        self.assertIn(REMOVED, screen)
        self.assertNotIn("deleted successfully", screen)

    def test_delete_password_changed_elsewhere_is_not_deleted(self):
        edit = self.elsewhere(lambda db: db.__setitem__(
            "p1", S.update_profile(db["p1"], self.key, password="the-new-one")), "y")
        screen = self.drive(MB.mobile_password_manager, "4", "1", edit, "0")
        self.assertIn(CHANGED, screen)
        self.assertEqual(self.profiles()["p1"]["password"], "the-new-one")

    def test_edit_password_keeps_fields_changed_elsewhere(self):
        edit = self.elsewhere(lambda db: db.__setitem__(
            "p1", S.update_profile(db["p1"], self.key, password="the-new-one")), "")
        self.drive(MB.mobile_password_manager, "3", "1", edit, "alice", "", "0",
                   passwords=[""])
        p = self.profiles()["p1"]
        self.assertEqual((p["username"], p["password"]), ("alice", "the-new-one"))

    # -- profile view
    def test_edit_profile_removed_elsewhere(self):
        screen = self.drive(MB.mobile_profile_manager, "3", "1",
                            self.remove("p1", "work"), "", "", "0")
        self.assertIn(REMOVED, screen)
        self.assertNotIn("KeyError", screen)

    def test_favorite_flips_the_value_in_the_vault_now(self):
        """The list showed "not a favorite"; the other window starred it
        before the pick. Flipping must un-star it and say so, not star it
        again and report "Added"."""
        star = self.elsewhere(lambda db: db.__setitem__(
            "p1", S.update_profile(db["p1"], self.key, favorite=True)), "1")
        screen = self.drive(MB.mobile_profile_manager, "4", star, "0")
        self.assertFalse(self.profiles()["p1"]["favorite"])
        self.assertIn("Removed from favorites", screen)

    def test_favorite_removed_elsewhere(self):
        screen = self.drive(MB.mobile_profile_manager, "4", self.remove("p1", "1"), "0")
        self.assertIn(REMOVED, screen)
        self.assertNotIn("favorites", screen.split(REMOVED)[1].split("\n")[0])


if __name__ == "__main__":
    import unittest
    unittest.main()
