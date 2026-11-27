"""Generated secrets are handed over clipboard-first: copied with auto-clear,
shown on screen only when the user types 'v'. Also: the Klipper clipboard
tool is refused, and a revealed secret is shown exactly as stored.
"""
import contextlib
import io
import os
import sys
import tempfile
import types
import unittest
from unittest import mock

import main.DESKTOP as D
from main import SECURE_IO, TERMINAL
from tests.test_vault_integrity import quiet

SECRET = "Gen3rated-secret!"


class Clip:
    def __init__(self, broken=False):
        self.value = ""
        self.broken = broken

    def copy(self, text):
        if self.broken:
            raise RuntimeError("no clipboard")
        self.value = text

    def paste(self):
        return self.value


class Base(unittest.TestCase):
    def use_clip(self, broken=False):
        self.clip = Clip(broken)
        SECURE_IO.set_clipboard_backend(self.clip.copy, self.clip.paste)
        self.addCleanup(SECURE_IO.set_clipboard_backend, None, None)
        self.addCleanup(SECURE_IO.clear_clipboard_if_ours)

    def offer(self, answer, **kw):
        prompts = []

        def ask(prompt):
            prompts.append(prompt)
            return answer
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = SECURE_IO.offer_secret("Generated password", SECRET, ask, **kw)
        return out.getvalue(), prompts, result


class OfferSecret(Base):
    def test_enter_copies_and_never_prints(self):
        self.use_clip()
        out, prompts, result = self.offer("")
        self.assertEqual(self.clip.value, SECRET)
        self.assertNotIn(SECRET, out)
        self.assertNotIn(SECRET, "".join(prompts))
        self.assertIn("copied to clipboard", out)
        self.assertIn("cleared in", out)
        self.assertEqual(result, "")
        self.assertTrue(SECURE_IO.has_pending_secret())

    def test_v_shows_it_once_and_still_copies(self):
        self.use_clip()
        for typed in ("v", " V "):
            out, _prompts, _result = self.offer(typed)
            self.assertEqual(out.count(SECRET), 1)
            self.assertEqual(self.clip.value, SECRET)

    def test_other_answers_do_not_show_it(self):
        self.use_clip()
        for typed in ("y", "view", ".c", "vv", None, 0):
            out, _prompts, result = self.offer(typed)
            self.assertNotIn(SECRET, out)
            self.assertEqual(result, typed)

    def test_copy_is_cleared_after_the_delay(self):
        import time
        self.use_clip()
        self.offer("", timeout=0.05)
        time.sleep(1.0)
        self.assertEqual(self.clip.value, "")

    def test_broken_clipboard_is_said_plainly_and_nothing_leaks(self):
        self.use_clip(broken=True)
        out, prompts, _result = self.offer("")
        self.assertIn("NOT copied", out)
        self.assertNotIn("copied to clipboard", out)
        self.assertIn("without it", prompts[0])
        self.assertNotIn(SECRET, out)
        shown, _p, _r = self.offer("v")
        self.assertEqual(shown.count(SECRET), 1)

    def test_required_secret_cannot_be_skipped_when_not_copied(self):
        self.use_clip(broken=True)
        typed = iter(["", "y", ".c", "v"])
        prompts = []

        def ask(prompt):
            prompts.append(prompt)
            return next(typed)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = SECURE_IO.offer_secret("Passphrase", SECRET, ask, required=True)
        self.assertEqual(result, "v")
        self.assertEqual(len(prompts), 4)
        self.assertNotIn("continue without", "".join(prompts))
        self.assertEqual(out.getvalue().count(SECRET), 1)
        self.assertTrue(out.getvalue().rstrip().endswith(SECRET))  # shown only at the end

    def test_required_secret_stops_on_the_callers_timeout_code(self):
        self.use_clip(broken=True)
        out, prompts, result = self.offer("*T*", required=True, stop=("*T*",))
        self.assertEqual((result, len(prompts)), ("*T*", 1))
        self.assertNotIn(SECRET, out)
        out, prompts, result = self.offer(None, required=True)
        self.assertIsNone(result)

    def test_required_secret_that_was_copied_can_be_skipped(self):
        self.use_clip()
        out, prompts, result = self.offer("", required=True)
        self.assertEqual(len(prompts), 1)
        self.assertNotIn(SECRET, out)
        self.assertEqual(self.clip.value, SECRET)

    def test_failed_clear_is_retried_when_the_clipboard_comes_back(self):
        self.use_clip()
        SECURE_IO.copy_secret(SECRET, timeout=60)
        with mock.patch.object(SECURE_IO, "_clipboard", side_effect=RuntimeError("down")):
            self.assertFalse(SECURE_IO.clear_clipboard_if_ours())
        self.assertTrue(SECURE_IO.has_pending_secret())
        self.assertTrue(SECURE_IO.clear_clipboard_if_ours())
        self.assertEqual(self.clip.value, "")

    def test_warning_comes_before_the_prompt(self):
        self.use_clip()
        out, prompts, _result = self.offer("", warning="Keep it safe.")
        self.assertIn("Keep it safe.", out)
        self.assertEqual(len(prompts), 1)

    def test_text_is_plain_for_screen_readers(self):
        self.use_clip()
        out, prompts, _result = self.offer("v")
        text = out.replace(SECRET, "") + "".join(prompts)
        self.assertNotIn("\x1b", text)                  # no colour codes
        self.assertEqual(TERMINAL.strip_emoji(text), text)  # no pictographs
        self.assertTrue(text.isascii())
        self.assertIn("Enter", prompts[0])              # says how to answer


class GeneratorScreen(Base):
    """Desktop 'Generate random password' with real generation."""

    def run_generator(self, show):
        self.use_clip()
        asked = []

        def answer(prompt, *_a, **_k):
            asked.append(prompt)
            if "Password length" in prompt:
                return "24"
            if "show it on screen" in prompt:
                return show
            if "Press 'enter'" in prompt:
                return ""
            raise AssertionError(f"unexpected prompt: {prompt!r}")
        out = io.StringIO()
        with mock.patch.object(D, "timeoutInput", answer), \
             mock.patch.object(D, "clear_screen", quiet), \
             mock.patch.object(D, "displayHeader", quiet), \
             contextlib.redirect_stdout(out):
            D.pwdGenerate(None, {})
        return out.getvalue(), asked

    def test_generated_password_is_copied_not_printed(self):
        out, asked = self.run_generator("")
        password = self.clip.value
        self.assertEqual(len(password), 24)
        self.assertNotIn(password, out)
        self.assertNotIn(password, "".join(asked))
        self.assertIn(SECURE_IO.MASK, out)

    def test_generated_password_is_shown_on_request(self):
        out, _asked = self.run_generator("v")
        self.assertEqual(out.count(self.clip.value), 1)

    def test_timeout_code_at_the_offer_returns_without_printing(self):
        # A real timeout exits the process inside timeoutInput; this is the
        # fallback path where the prompt hands back its timeout code.
        out, asked = self.run_generator(D.timeoutGlobalCode)
        self.assertNotIn(self.clip.value, out)
        self.assertEqual(sum("Press 'enter'" in p for p in asked), 0)


class GeneratedExportPassphrase(Base):
    """Encrypted export with a generated passphrase (.g): the passphrase goes
    to the clipboard, is not printed, and opens the export in a new vault."""

    def run_flow(self, func, key, table, show_answers=None):
        import main.INITIALIZE as I

        def answer(prompt, *_a, **_k):
            if show_answers is not None and "show it on screen" in prompt:
                return next(show_answers)
            for needle, value in table.items():
                if needle in prompt:
                    return value
            raise AssertionError(f"unexpected prompt: {prompt!r}")
        out = io.StringIO()
        with mock.patch.object(D, "timeoutInput", answer), \
             mock.patch.object(D, "timeout_getpass", answer), \
             mock.patch("builtins.input", answer), \
             mock.patch.object(D, "clear_screen", quiet), \
             mock.patch.object(D, "displayHeader", quiet), \
             contextlib.redirect_stdout(out):
            func(key, I.loadDatabase(key))
        return out.getvalue()

    def export_with_generated_passphrase(self, show, show_answers=None, passphrase_from=None):
        import shutil
        from tests import test_backup_roundtrip as R
        from tests.test_vault_integrity import PASSWORD, key_for, run_setup
        cwd = os.getcwd()
        src, dst = tempfile.mkdtemp(), tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, src, True)
        self.addCleanup(shutil.rmtree, dst, True)
        self.addCleanup(os.chdir, cwd)
        self.use_clip()
        os.chdir(src)
        key = R.make_vault_with_profiles()
        expected = R.decrypted_profiles(key)
        out = self.run_flow(D.exportProfiles, key, {
            "export all profiles": "y", "export as encrypted": "y",
            "see the password as you type": "y", "show your password while typing": "y",
            "passphrase for encryption": ".g", "file name to save profiles": "b.json",
            "Continue with export": "y", "show it on screen": show, "Press 'enter'": "",
        }, show_answers)
        passphrase = passphrase_from["v"] if passphrase_from else self.clip.value
        shutil.copy("b.json", os.path.join(dst, "b.json"))
        os.chdir(dst)
        self.assertTrue(run_setup())
        key2 = key_for(PASSWORD)
        self.run_flow(D.importProfiles, key2, {
            "see the password as you type": "y", "show your password while typing": "y",
            "passphrase used for encryption": passphrase, "Choose file to import": "b.json",
            "display passwords": "n", "import these profiles": "y", "Press 'enter'": "",
        })
        self.assertEqual(R.decrypted_profiles(key2), expected)
        return out, passphrase

    def test_passphrase_is_copied_not_printed_and_opens_the_export(self):
        out, passphrase = self.export_with_generated_passphrase(show="")
        self.assertEqual(len(passphrase), 16)
        self.assertNotIn(passphrase, out)
        self.assertIn("without it this export cannot be opened", out)

    def test_without_a_clipboard_the_passphrase_must_be_shown(self):
        self.use_clip = lambda broken=False: Base.use_clip(self, broken=True)
        seen = {}
        real_reveal = SECURE_IO.reveal_secret

        def spy(label, value, out=None):
            seen["v"] = value
            return real_reveal(label, value, out)
        answers = iter(["", "v"])
        with mock.patch.object(SECURE_IO, "reveal_secret", spy):
            out, _empty = self.export_with_generated_passphrase(
                show=None, show_answers=answers, passphrase_from=seen)
        self.assertEqual(out.count(seen["v"]), 1)
        self.assertIn("NOT copied", out)

    def test_passphrase_is_shown_on_request(self):
        out, passphrase = self.export_with_generated_passphrase(show="v")
        self.assertEqual(out.count(passphrase), 1)


class NoSecretPrintedWithoutAsking(unittest.TestCase):
    def test_desktop_prints_secrets_only_through_secure_io(self):
        """Every reveal in DESKTOP.py sits under an explicit choice; the
        generated password and passphrase are never passed to reveal_secret
        or print directly."""
        import ast
        with open(D.__file__, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "id", "")
            if name not in ("print", "reveal_secret", "to_clipboard"):
                continue
            used = {n.id for a in node.args for n in ast.walk(a) if isinstance(n, ast.Name)}
            self.assertFalse(
                used & {"generated_passphrase", "passphrase", "add_password", "edit_password"},
                f"line {node.lineno}: {name}() is given a generated secret")
        generator = next(n for n in ast.walk(tree)
                         if isinstance(n, ast.FunctionDef) and n.name == "pwdGenerate")
        for node in ast.walk(generator):
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") in (
                    "print", "reveal_secret", "to_clipboard"):
                used = {n.id for a in node.args for n in ast.walk(a) if isinstance(n, ast.Name)}
                self.assertNotIn("password", used, f"line {node.lineno}")


class KlipperRefused(Base):
    def fake_pyperclip(self, copy_name):
        calls = []

        def copy(text):
            calls.append(text)
        copy.__name__ = copy_name
        module = types.ModuleType("pyperclip")
        module.determine_clipboard = lambda: (copy, lambda: calls[-1] if calls else "")
        return module, calls

    def setUp(self):
        SECURE_IO.set_clipboard_backend(None, None)
        self._saved = SECURE_IO._system_clipboard
        SECURE_IO._system_clipboard = None
        self.addCleanup(setattr, SECURE_IO, "_system_clipboard", self._saved)
        self.addCleanup(SECURE_IO.clear_clipboard_if_ours)
        # These tests are about the pyperclip path (Linux); keep the native
        # Windows and macOS backends out of the way on those systems.
        patcher = mock.patch.object(SECURE_IO, "_native_clipboard", lambda: None)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_klipper_never_receives_the_secret(self):
        module, calls = self.fake_pyperclip("copy_klipper")
        with mock.patch.dict(sys.modules, {"pyperclip": module}):
            self.assertFalse(SECURE_IO.copy_secret(SECRET))
        self.assertEqual(calls, [])
        self.assertFalse(SECURE_IO.has_pending_secret())

    def test_other_tools_still_work(self):
        module, calls = self.fake_pyperclip("copy_xclip")
        with mock.patch.dict(sys.modules, {"pyperclip": module}):
            self.assertTrue(SECURE_IO.copy_secret(SECRET))
            self.assertEqual(calls, [SECRET])
            self.assertTrue(SECURE_IO.clear_clipboard_if_ours())
        self.assertEqual(calls[-1], "")


class RevealIsExact(unittest.TestCase):
    def test_emoji_in_a_secret_survives_no_emoji_mode(self):
        secret = "p★ss\U0001F511 word❤️!"
        raw = io.StringIO()
        with mock.patch.object(sys, "stdout", TERMINAL._EmojiFreeStream(raw)):
            print("\U0001F512 Vault")                    # normal text is filtered
            SECURE_IO.reveal_secret("\U0001F511 Password: ", secret)
        self.assertEqual(raw.getvalue(), f"Vault\nPassword: {secret}\n")


if __name__ == "__main__":
    unittest.main()
