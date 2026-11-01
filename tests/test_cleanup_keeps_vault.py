"""Exit cleanup must never delete the vault or the salt it depends on."""
import os
import tempfile
import unittest

from main.SHARED_RESOURCES_MOBILE import secure_cleanup_common


class CleanupKeepsVault(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)

    def tearDown(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def test_vault_and_salt_survive_cleanup(self):
        for name in ("Bunker.mmf", "bunker.salt", "bunker.cfg", "config.cfg"):
            with open(name, "wb") as f:
                f.write(b"data")
        secure_cleanup_common()
        for name in ("Bunker.mmf", "bunker.salt", "bunker.cfg", "config.cfg"):
            self.assertTrue(os.path.exists(name), f"{name} was deleted by cleanup")

    def test_temporary_files_are_removed(self):
        for name in ("config.cfg.tmp", "vault.tmp"):
            with open(name, "wb") as f:
                f.write(b"tmp")
        secure_cleanup_common()
        self.assertFalse(os.path.exists("config.cfg.tmp"))
        self.assertFalse(os.path.exists("vault.tmp"))

    def test_cleanup_clears_copied_secret(self):
        from main import SECURE_IO
        box = {"v": ""}
        SECURE_IO.set_clipboard_backend(lambda t: box.update(v=t), lambda: box["v"])
        try:
            SECURE_IO.copy_secret("hunter2!", timeout=60)
            secure_cleanup_common()
            self.assertEqual(box["v"], "")
        finally:
            SECURE_IO.set_clipboard_backend(None, None)

    def test_to_clipboard_message_has_no_secret(self):
        from main import SECURE_IO
        from main.SHARED_RESOURCES import to_clipboard
        box = {"v": ""}
        SECURE_IO.set_clipboard_backend(lambda t: box.update(v=t), lambda: box["v"])
        try:
            msg = to_clipboard("hunter2!")
            self.assertEqual(box["v"], "hunter2!")
            self.assertNotIn("hunter2!", msg)
        finally:
            SECURE_IO.clear_clipboard_if_ours()
            SECURE_IO.set_clipboard_backend(None, None)


if __name__ == "__main__":
    unittest.main()
