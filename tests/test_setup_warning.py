"""First-run setup says, before any password is asked for, that wrong master
passwords permanently delete the vault, and waits for Enter. The number in
that sentence, in the setup guide and in the user guide comes from the
attempt limit, never from a hard-coded "three". The (.g) option opens the
real setup guide on the desktop and a short one elsewhere.
"""
import contextlib
import io
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import main.DESKTOP as D
import main.INITIALIZE as I
import main.MOBILE as MOB
import main.SHARED_RESOURCES_MOBILE as M
import main.VAULT_FILES as VF

PASSWORD = "correct horse battery"
VAULT_FILES = ("Bunker.mmf", "bunker.salt", "bunker.cfg", "config.cfg", "bunker.chk")


def quiet(*_a, **_k):
    return None


class Wording(unittest.TestCase):
    def test_default_sentence(self):
        self.assertEqual(
            VF.self_destruct_warning(),
            "After 3 wrong master passwords in a row, this vault is permanently "
            "deleted. Keep an encrypted export as a backup.")

    def test_number_follows_the_limit(self):
        self.assertIn("After 5 wrong master passwords in a row,", VF.self_destruct_warning(5))
        self.assertIn("After 10 wrong master passwords in a row,", VF.self_destruct_warning(10))
        self.assertNotIn("3", VF.self_destruct_warning(5))

    def test_limit_of_one_reads_as_singular(self):
        self.assertIn("After 1 wrong master password, this vault", VF.self_destruct_warning(1))
        self.assertEqual(VF.attempts_phrase(1), "1 incorrect master password attempt")

    def test_broken_limit_falls_back_to_the_default(self):
        for bad in (None, 0, -2, "5", 2.5, True, [3]):
            with self.subTest(value=bad):
                self.assertEqual(VF.attempt_limit(bad), VF.DEFAULT_MAX_ATTEMPTS)
                self.assertEqual(VF.self_destruct_warning(bad), VF.self_destruct_warning())

    def test_mobile_sentence_says_who_deletes(self):
        text = VF.self_destruct_warning(4, destroys=False)
        self.assertIn("After 4 wrong master passwords in a row, the desktop interface "
                      "permanently deletes this vault", text)
        self.assertIn("this interface never does", text)
        self.assertNotIn("this vault is permanently deleted", text)

    def test_guide_phrases(self):
        self.assertEqual(VF.attempts_phrase(), "3 incorrect master password attempts")
        self.assertEqual(VF.attempts_phrase(7, kind="password"), "7 incorrect password attempts")

    def test_no_guide_text_hard_codes_the_number(self):
        pattern = re.compile(r"\b(three|3)\s+(incorrect|wrong|failed)\b", re.IGNORECASE)
        root = Path(I.__file__).resolve().parent
        for path in sorted(root.glob("*.py")):
            if path.name == "VAULT_FILES.py":
                continue  # where the phrases are built; its docstrings show examples
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                self.assertIsNone(pattern.search(line), f"{path.name}:{number}: {line.strip()}")


class SetupCase(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)
        self.addCleanup(self._restore)

    def _restore(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def run_setup(self, answers, hidden=(), **kwargs):
        """Run vaultSetup with scripted answers. Returns (result, events):
        events are ("prompt", text, everything printed before it)."""
        answers = iter(answers)
        hidden = iter(hidden)
        out = io.StringIO()
        events = []

        def fake_input(prompt="", *_a, **_k):
            events.append((prompt, out.getvalue()))
            return next(answers)

        def fake_getpass(prompt="", *_a, **_k):
            events.append((prompt, out.getvalue()))
            return next(hidden)

        with mock.patch("builtins.input", fake_input), \
             mock.patch.object(M.getpass, "getpass", fake_getpass), \
             mock.patch.object(M, "setup_timeout", lambda *a, **k: 300), \
             mock.patch.object(M, "clear_screen", quiet), \
             mock.patch.object(M, "check_terminal_size", quiet), \
             mock.patch.object(M.time, "sleep", quiet), \
             contextlib.redirect_stdout(out):
            result = M.vaultSetup(**kwargs)
        return result, events, out.getvalue()

    def assert_no_vault(self):
        for name in VAULT_FILES:
            self.assertFalse(Path(name).exists(), f"{name} was written")


class SetupWarning(SetupCase):
    def test_warning_is_printed_before_any_password_prompt(self):
        result, events, _ = self.run_setup(["y", "", "y", PASSWORD, PASSWORD, ""])
        self.assertTrue(result)
        warning = VF.self_destruct_warning()
        prompts = [p for p, _ in events]
        ack = next(i for i, p in enumerate(prompts) if "Press Enter to acknowledge" in p)
        first_password = next(i for i, p in enumerate(prompts) if "Enter Password" in p)
        show_choice = next(i for i, p in enumerate(prompts) if "show your password" in p)
        self.assertLess(ack, show_choice)
        self.assertLess(ack, first_password)
        # The sentence is already on screen when the acknowledgement is asked.
        self.assertIn(f"WARNING: {warning}", events[ack][1])
        # ...and nothing about a password was asked before it.
        for prompt in prompts[:ack]:
            self.assertNotIn("Password", prompt)

    def test_warning_precedes_the_hidden_password_prompt_too(self):
        result, events, _ = self.run_setup(["y", "", "n", ""], hidden=[PASSWORD, PASSWORD])
        self.assertTrue(result)
        prompts = [p for p, _ in events]
        ack = next(i for i, p in enumerate(prompts) if "Press Enter to acknowledge" in p)
        first_password = next(i for i, p in enumerate(prompts) if "Enter Password" in p)
        self.assertLess(ack, first_password)
        self.assertIn(VF.self_destruct_warning(), events[first_password][1])

    def test_only_enter_acknowledges(self):
        result, events, out = self.run_setup(
            ["y", "ok", "y", "", "y", PASSWORD, PASSWORD, ""])
        self.assertTrue(result)
        asks = [p for p, _ in events if "Press Enter to acknowledge" in p]
        self.assertEqual(len(asks), 3, "anything but Enter must ask again")
        self.assertIn("Press Enter on an empty line", out)

    def test_cancel_at_the_warning_creates_nothing(self):
        for answer in (".c", " .C "):
            with self.subTest(answer=answer):
                result, events, out = self.run_setup(["y", answer])
                self.assertFalse(result)
                self.assertIn("Operation cancelled", out)
                self.assertFalse(any("Password" in p for p, _ in events))
                self.assert_no_vault()

    def test_declining_setup_never_reaches_the_warning_prompt(self):
        result, events, _ = self.run_setup(["n"])
        self.assertFalse(result)
        self.assertEqual(len(events), 1)
        self.assert_no_vault()

    def test_number_in_the_warning_is_the_limit_setup_saves(self):
        with mock.patch.object(VF, "DEFAULT_MAX_ATTEMPTS", 5):
            result, events, out = self.run_setup(["y", "", "y", PASSWORD, PASSWORD, ""])
            self.assertTrue(result)
            self.assertIn("After 5 wrong master passwords in a row, this vault is "
                          "permanently deleted.", out)
        self.assertEqual(M.load_ui_config()["max_attempts"], 5)

    def test_new_vault_starts_with_the_default_limit(self):
        result, _, out = self.run_setup(["y", "", "y", PASSWORD, PASSWORD, ""])
        self.assertTrue(result)
        self.assertEqual(M.load_ui_config()["max_attempts"], VF.DEFAULT_MAX_ATTEMPTS)
        self.assertIn(f"After {VF.DEFAULT_MAX_ATTEMPTS} wrong", out)

    def test_mobile_setup_uses_the_mobile_sentence(self):
        result, _, out = self.run_setup(["y", "", "y", PASSWORD, PASSWORD, ""], destroys=False)
        self.assertTrue(result)
        self.assertIn(f"WARNING: {VF.self_destruct_warning(destroys=False)}", out)
        self.assertNotIn("this vault is permanently deleted", out)

    def test_warning_is_readable_without_colour_or_emoji(self):
        text = "WARNING: " + VF.self_destruct_warning()
        self.assertTrue(text.isascii())


class SetupGuideOption(SetupCase):
    def test_g_opens_the_guide_it_was_given_then_asks_again(self):
        guide = mock.Mock()
        result, events, out = self.run_setup([".g", "n"], setup_guide=guide)
        self.assertFalse(result)
        guide.assert_called_once_with()
        self.assertEqual(len(events), 2)
        self.assertNotIn("not implemented", out)

    def test_g_without_a_guide_prints_the_short_one(self):
        result, _, out = self.run_setup([".g", "n"], destroys=False)
        self.assertFalse(result)
        self.assertNotIn("not implemented", out)
        self.assertIn("SETUP GUIDE", out)
        self.assertIn(VF.self_destruct_warning(destroys=False), out)
        self.assertIn("cannot be recovered", out)
        self.assertLessEqual(max(len(line) for line in out.splitlines()), 400)

    def test_short_guide_desktop_wording(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            M.setup_guide_short()
        self.assertIn(VF.self_destruct_warning(), out.getvalue())


class FullSetupGuide(unittest.TestCase):
    def show(self, answers, **kwargs):
        answers = iter(answers)
        out = io.StringIO()
        with mock.patch("builtins.input", lambda *a, **k: next(answers)), \
             mock.patch.object(I, "clear_screen", quiet), \
             contextlib.redirect_stdout(out):
            I.display_setup_guide(**kwargs)
        return out.getvalue()

    def test_guide_runs_and_states_the_default_limit(self):
        out = self.show(["", "", ".c"])
        self.assertIn("after 3 incorrect master password attempts, the application "
                      "self-destructs", out)
        self.assertIn("self-destruct data after 3 incorrect password attempts.", out)
        self.assertIn("self-destruct all data after 3 incorrect password attempts.", out)
        self.assertNotIn("three", out.lower())
        self.assertIn("BUNKER SETUP", out, "leaving the guide puts the setup header back")

    def test_guide_follows_another_limit(self):
        out = self.show(["", "", ".c"], max_attempts=6)
        self.assertEqual(out.count("6 incorrect"), 3)
        self.assertNotIn("3 incorrect", out)

    def test_single_section_and_invalid_choice(self):
        out = self.show(["3", "", "9", "", ".c"])
        self.assertIn("Important Notes", out)
        self.assertIn("Invalid choice", out)


class UserGuide(unittest.TestCase):
    def show(self, max_attempts):
        answers = iter(["", ""])  # show every section, then return
        out = io.StringIO()
        with mock.patch.object(I, "timeoutInput", lambda *a, **k: next(answers)), \
             mock.patch.object(I, "load_ui_config", lambda: {"max_attempts": max_attempts}), \
             mock.patch.object(I, "clear_screen", quiet), \
             mock.patch.object(I, "displayHeader", quiet), \
             contextlib.redirect_stdout(out):
            I.display_user_guide(b"k" * 32, {})
        return out.getvalue()

    def test_user_guide_states_the_configured_limit(self):
        out = self.show(5)
        self.assertIn("after 5 incorrect master password attempts, the application "
                      "self-destructs", out)
        self.assertIn("self-destruct data after 5 incorrect password attempts.", out)
        self.assertIn("After 5 incorrect master password attempts, all stored data is "
                      "permanently deleted.", out)
        self.assertNotIn("three incorrect", out.lower())
        self.assertNotIn("3 incorrect", out)

    def test_user_guide_default_limit(self):
        self.assertEqual(self.show(3).count("3 incorrect"), 3)


class Wiring(SetupCase):
    """The interfaces hand setup the right guide and the right wording."""

    def desktop_setup_call(self, device_type):
        setup = mock.Mock(return_value=False)
        with mock.patch.object(D, "vaultSetup", setup), \
             mock.patch.object(D, "clear_screen", quiet), \
             mock.patch.object(D, "check_terminal_size", quiet), \
             mock.patch.object(D.time, "sleep", quiet), \
             contextlib.redirect_stdout(io.StringIO()):
            D.main(device_type)
        setup.assert_called_once()
        return setup.call_args

    def test_desktop_first_run_wires_g_to_the_setup_guide(self):
        call = self.desktop_setup_call("desktop")
        self.assertIs(call.kwargs["setup_guide"], I.display_setup_guide)
        self.assertTrue(call.kwargs["destroys"])

    def test_phone_first_run_gets_the_short_guide_and_mobile_wording(self):
        for device in ("mobile", "tablet"):
            with self.subTest(device=device):
                call = self.desktop_setup_call(device)
                self.assertIsNone(call.kwargs["setup_guide"])
                self.assertFalse(call.kwargs["destroys"])

    def test_mobile_interface_setup_uses_mobile_wording(self):
        setup = mock.Mock(return_value=False)
        with mock.patch.object(MOB, "vaultSetup", setup), \
             mock.patch.object(MOB, "clear_screen", quiet), \
             contextlib.redirect_stdout(io.StringIO()):
            MOB.main("mobile")
        setup.assert_called_once_with(destroys=False)

    def test_desktop_g_end_to_end(self):
        """(.g) at the real first-run prompt shows the real guide."""
        answers = iter([".g", "1", "", ".c", "n"])
        out = io.StringIO()
        with mock.patch("builtins.input", lambda *a, **k: next(answers)), \
             mock.patch.object(D, "clear_screen", quiet), \
             mock.patch.object(D, "check_terminal_size", quiet), \
             mock.patch.object(I, "clear_screen", quiet), \
             mock.patch.object(M, "clear_screen", quiet), \
             mock.patch.object(M, "check_terminal_size", quiet), \
             mock.patch.object(D.time, "sleep", quiet), \
             contextlib.redirect_stdout(out):
            D.main("desktop")
        text = out.getvalue()
        self.assertIn("Welcome to the Bunker Setup Guide", text)
        self.assertIn("after 3 incorrect master password attempts", text)
        self.assertNotIn("not implemented", text)
        self.assert_no_vault()


if __name__ == "__main__":
    unittest.main()
