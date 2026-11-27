"""The Windows and macOS clipboard backends in main/SECURE_IO.py.

Most of this file runs everywhere with the operating-system calls replaced
by fakes: it checks which calls BUNKER makes, in which order, with which
bytes, and what it does when one of them fails. That proves the logic, not
that Windows or macOS behave as documented.

The two ``Real...`` classes at the end use the real clipboard. They replace
whatever is on it, so they only run when BUNKER_TEST_REAL_CLIPBOARD=1 is
set (the CI workflow sets it) and only on the matching system.
"""
import ctypes
import os
import subprocess
import sys
import time
import unittest
from unittest import mock

from main import SECURE_IO

SECRET = "Tr0ub4dor&3 é中\U0001F511"
REAL = os.environ.get("BUNKER_TEST_REAL_CLIPBOARD") == "1"


class FakeWindows:
    """Stands in for user32 and kernel32. Memory blocks are real ctypes
    buffers, so the bytes BUNKER writes can be read back and checked."""

    def __init__(self):
        self.blocks = {}        # handle -> ctypes buffer (still allocated)
        self.freed = []
        self.formats = {}       # registered name -> id
        self.clipboard = {}     # format id -> handle
        self.log = []
        self.is_open = False
        self.busy_for = 0       # OpenClipboard fails this many times first
        self.fail_set = set()   # format names/ids SetClipboardData refuses
        self.fail_empty = False
        self.fail_alloc = False
        self.windows = set()
        self._next = 0x1000
        self.user32 = self
        self.kernel32 = self

    # user32
    def CreateWindowExW(self, *args):
        self._next += 8
        self.windows.add(self._next)
        return self._next

    def DestroyWindow(self, window):
        self.windows.discard(window)
        return 1

    def OpenClipboard(self, window):
        if self.busy_for:
            self.busy_for -= 1
            return 0
        assert not self.is_open
        self.is_open = True
        self.log.append("open")
        return 1

    def CloseClipboard(self):
        assert self.is_open
        self.is_open = False
        self.log.append("close")
        return 1

    def EmptyClipboard(self):
        assert self.is_open
        if self.fail_empty:
            return 0
        for handle in self.clipboard.values():
            self.blocks.pop(handle, None)   # the system frees what it owns
        self.clipboard = {}
        self.log.append("empty")
        return 1

    def RegisterClipboardFormatW(self, name):
        return self.formats.setdefault(name, 0xC000 + len(self.formats))

    def name_of(self, fmt):
        for name, value in self.formats.items():
            if value == fmt:
                return name
        return fmt

    def SetClipboardData(self, fmt, handle):
        assert self.is_open
        name = self.name_of(fmt)
        if name in self.fail_set:
            return 0
        self.clipboard[fmt] = handle
        self.log.append(("set", name))
        return handle

    def GetClipboardData(self, fmt):
        assert self.is_open
        return self.clipboard.get(fmt, 0)

    def IsClipboardFormatAvailable(self, fmt):
        return 1 if fmt in self.clipboard else 0

    # kernel32
    def GlobalAlloc(self, flags, size):
        assert flags == 0x0002
        if self.fail_alloc:
            return 0
        self._next += 8
        self.blocks[self._next] = ctypes.create_string_buffer(size + 6)  # padded, as real blocks can be
        return self._next

    def GlobalLock(self, handle):
        return ctypes.addressof(self.blocks[handle])

    def GlobalUnlock(self, handle):
        return 0

    def GlobalSize(self, handle):
        return len(self.blocks[handle])

    def GlobalFree(self, handle):
        self.freed.append(bytes(self.blocks.pop(handle)))
        return 0

    # helpers for assertions
    def data(self, name_or_fmt, size):
        fmt = self.formats.get(name_or_fmt, name_or_fmt)
        return bytes(self.blocks[self.clipboard[fmt]])[:size]


class WindowsBackend(unittest.TestCase):
    def setUp(self):
        self.win = FakeWindows()
        self.sleeps = []
        self.cb = SECURE_IO._WindowsClipboard(self.win, self.win, sleep=self.sleeps.append)

    def test_copy_sets_the_three_marks_then_the_text(self):
        self.cb.copy(SECRET)
        self.assertEqual(self.win.log, [
            "open", "empty",
            ("set", "ExcludeClipboardContentFromMonitorProcessing"),
            ("set", "CanIncludeInClipboardHistory"),
            ("set", "CanUploadToCloudClipboard"),
            ("set", 13),
            "close"])

    def test_marks_are_a_dword_of_zero(self):
        self.cb.copy(SECRET)
        for name in SECURE_IO._WindowsClipboard.MARKS:
            self.assertEqual(self.win.data(name, 4), b"\x00\x00\x00\x00", name)

    def test_text_is_utf16_with_a_terminator(self):
        self.cb.copy(SECRET)
        expected = SECRET.encode("utf-16-le") + b"\x00\x00"
        self.assertEqual(self.win.data(13, len(expected)), expected)

    def test_paste_returns_what_was_copied(self):
        for text in (SECRET, "a", "two\r\nlines", "trailing space "):
            self.cb.copy(text)
            self.assertEqual(self.cb.paste(), text)

    def test_paste_with_no_text_on_the_clipboard_is_empty(self):
        self.assertEqual(self.cb.paste(), "")

    def test_clear_empties_everything(self):
        self.cb.copy(SECRET)
        self.cb.clear()
        self.assertEqual(self.win.clipboard, {})
        self.assertEqual(self.cb.marks_present(), [])

    def test_copying_an_empty_string_clears(self):
        self.cb.copy(SECRET)
        self.cb.copy("")
        self.assertEqual(self.win.clipboard, {})

    def test_marks_present_lists_all_three_after_a_copy(self):
        self.cb.copy(SECRET)
        self.assertEqual(self.cb.marks_present(), list(SECURE_IO._WindowsClipboard.MARKS))

    def test_a_mark_that_cannot_be_set_stops_the_copy(self):
        for name in SECURE_IO._WindowsClipboard.MARKS:
            win = FakeWindows()
            win.fail_set = {name}
            cb = SECURE_IO._WindowsClipboard(win, win, sleep=lambda s: None)
            with self.assertRaises(OSError):
                cb.copy(SECRET)
            self.assertEqual(win.clipboard, {}, name)
            self.assertNotIn(("set", 13), win.log, name)
            self.assertFalse(win.is_open)
            self.assertEqual(win.windows, set())
            self.assertEqual(win.blocks, {}, "no memory left allocated")

    def test_text_that_cannot_be_set_leaves_nothing_and_wipes_its_memory(self):
        self.win.fail_set = {13}
        with self.assertRaises(OSError):
            self.cb.copy(SECRET)
        self.assertEqual(self.win.clipboard, {})
        self.assertEqual(self.win.blocks, {})
        encoded = SECRET.encode("utf-16-le")
        for block in self.win.freed:
            self.assertNotIn(encoded[:8], block)
        self.assertEqual(self.win.freed[-1][:len(encoded)], bytes(len(encoded)))

    def test_error_text_never_contains_the_secret(self):
        self.win.fail_set = {13}
        with self.assertRaises(OSError) as caught:
            self.cb.copy(SECRET)
        self.assertNotIn(SECRET, str(caught.exception))

    def test_previous_content_is_removed_even_when_the_copy_fails(self):
        self.cb.copy("older secret")
        self.win.fail_set = {"CanIncludeInClipboardHistory"}
        with self.assertRaises(OSError):
            self.cb.copy(SECRET)
        self.assertEqual(self.win.clipboard, {})

    def test_busy_clipboard_is_retried(self):
        self.win.busy_for = 3
        self.cb.copy(SECRET)
        self.assertEqual(len(self.sleeps), 3)
        self.assertEqual(self.cb.paste(), SECRET)

    def test_clipboard_that_stays_busy_fails_cleanly(self):
        self.win.busy_for = 10 ** 6
        with self.assertRaises(OSError):
            self.cb.copy(SECRET)
        self.assertEqual(len(self.sleeps), SECURE_IO._WindowsClipboard.OPEN_TRIES)
        self.assertNotIn("close", self.win.log)   # never opened, so never closed
        self.assertEqual(self.win.windows, set())
        self.assertEqual(self.win.blocks, {})

    def test_empty_failure_stops_before_any_data(self):
        self.win.fail_empty = True
        with self.assertRaises(OSError):
            self.cb.copy(SECRET)
        self.assertEqual(self.win.log, ["open", "close"])
        with self.assertRaises(OSError):
            self.cb.clear()

    def test_out_of_memory_fails_cleanly(self):
        self.win.fail_alloc = True
        with self.assertRaises(OSError):
            self.cb.copy(SECRET)
        self.assertFalse(self.win.is_open)

    def test_text_with_a_nul_is_refused_not_truncated(self):
        with self.assertRaises(ValueError):
            self.cb.copy("abc\x00def")
        self.assertEqual(self.win.log, [])

    def test_window_and_clipboard_are_released_after_every_call(self):
        self.cb.copy(SECRET)
        self.cb.paste()
        self.cb.marks_present()
        self.cb.clear()
        self.assertFalse(self.win.is_open)
        self.assertEqual(self.win.windows, set())


class FakeMac:
    """Stands in for the Objective-C runtime: just enough of NSPasteboard,
    NSString, NSArray and NSAutoreleasePool for the backend's messages."""

    def __init__(self):
        self.objects = {}
        self.items = {}          # type -> text on the pasteboard
        self.log = []
        self.live_strings = set()
        self.live_pools = set()
        self.refuse_types = set()
        self.missing_classes = set()
        self.no_pasteboard = False
        self.unreadable = False
        self._next = 100

    def _new(self, value):
        self._next += 1
        self.objects[self._next] = value
        return self._next

    def get_class(self, name):
        if name in self.missing_classes:
            return None
        return self._new(("class", name))

    def send(self, receiver, selector, *args, restype=ctypes.c_void_p, argtypes=()):
        assert len(args) == len(argtypes), selector
        target = self.objects[receiver]
        if target[0] == "class":
            if selector == "alloc":
                return self._new(("alloc", target[1]))
            if selector == "generalPasteboard":
                return None if self.no_pasteboard else self._new(("pasteboard",))
        if target[0] == "alloc":
            if selector == "init" and target[1] == "NSAutoreleasePool":
                pool = self._new(("pool",))
                self.live_pools.add(pool)
                return pool
            if selector == "initWithBytes:length:encoding:":
                data, length, encoding = args
                assert encoding == 0x94000100 and length == len(data)
                string = self._new(("string", data.decode("utf-16-le", "surrogatepass")))
                self.live_strings.add(string)
                return string
        if target[0] == "pool" and selector == "drain":
            self.live_pools.discard(receiver)
            return None
        if target[0] == "string":
            if selector == "release":
                self.live_strings.discard(receiver)
                return None
            if selector == "UTF8String":
                return None if self.unreadable else target[1].encode("utf-8")
        if target[0] == "pasteboard":
            assert self.live_pools, "pasteboard used outside an autorelease pool"
            if selector == "prepareForNewContentsWithOptions:":
                self.items = {}
                self.log.append(("prepare", args[0]))
                return 1
            if selector == "clearContents":
                self.items = {}
                self.log.append("clear")
                return 1
            if selector == "setString:forType:":
                value, kind = self.objects[args[0]][1], self.objects[args[1]][1]
                if kind in self.refuse_types:
                    return False
                self.items[kind] = value
                self.log.append(("set", kind))
                return True
            if selector == "stringForType:":
                kind = self.objects[args[0]][1]
                return self._new(("string", self.items[kind])) if kind in self.items else None
            if selector == "types":
                return self._new(("array", list(self.items)))
        if target[0] == "array" and selector == "containsObject:":
            return self.objects[args[0]][1] in target[1]
        raise AssertionError(f"unexpected message {selector} to {target[0]}")


TEXT = "public.utf8-plain-text"
CONCEALED = "org.nspasteboard.ConcealedType"


class MacBackend(unittest.TestCase):
    def setUp(self):
        self.mac = FakeMac()
        self.cb = SECURE_IO._MacClipboard(self.mac.send, self.mac.get_class)

    def test_copy_marks_before_text_and_stays_on_this_device(self):
        self.cb.copy(SECRET)
        self.assertEqual(self.mac.log, [("prepare", 1), ("set", CONCEALED), ("set", TEXT)])
        self.assertEqual(self.mac.items, {CONCEALED: "", TEXT: SECRET})

    def test_paste_returns_what_was_copied(self):
        self.cb.copy(SECRET)
        self.assertEqual(self.cb.paste(), SECRET)

    def test_paste_with_no_text_is_empty(self):
        self.assertEqual(self.cb.paste(), "")

    def test_unreadable_text_raises_instead_of_looking_empty(self):
        self.cb.copy(SECRET)
        self.mac.unreadable = True
        with self.assertRaises(OSError):
            self.cb.paste()

    def test_clear_and_empty_copy_remove_everything(self):
        self.cb.copy(SECRET)
        self.cb.clear()
        self.assertEqual(self.mac.items, {})
        self.cb.copy(SECRET)
        self.cb.copy("")
        self.assertEqual(self.mac.items, {})
        self.assertEqual(self.cb.marks_present(), [])

    def test_marks_present_after_a_copy(self):
        self.cb.copy(SECRET)
        self.assertEqual(self.cb.marks_present(), [CONCEALED])

    def test_marker_refused_means_the_text_is_never_written(self):
        self.mac.refuse_types = {CONCEALED}
        with self.assertRaises(OSError):
            self.cb.copy(SECRET)
        self.assertEqual(self.mac.items, {})
        self.assertNotIn(("set", TEXT), self.mac.log)

    def test_text_refused_leaves_nothing_behind(self):
        self.mac.refuse_types = {TEXT}
        with self.assertRaises(OSError) as caught:
            self.cb.copy(SECRET)
        self.assertEqual(self.mac.items, {})
        self.assertNotIn(SECRET, str(caught.exception))

    def test_strings_and_pools_are_always_released(self):
        self.cb.copy(SECRET)
        self.cb.paste()
        self.cb.marks_present()
        self.cb.clear()
        self.mac.refuse_types = {TEXT}
        with self.assertRaises(OSError):
            self.cb.copy(SECRET)
        self.assertEqual(self.mac.live_strings, set())
        self.assertEqual(self.mac.live_pools, set())

    def test_missing_runtime_pieces_fail_at_start(self):
        for name in ("NSPasteboard", "NSString", "NSAutoreleasePool"):
            mac = FakeMac()
            mac.missing_classes = {name}
            with self.assertRaises(OSError):
                SECURE_IO._MacClipboard(mac.send, mac.get_class)
        mac = FakeMac()
        mac.no_pasteboard = True
        with self.assertRaises(OSError):
            SECURE_IO._MacClipboard(mac.send, mac.get_class)


class Selection(unittest.TestCase):
    """Which backend copy_secret ends up with on each system."""

    def setUp(self):
        SECURE_IO.set_clipboard_backend(None, None)
        saved = SECURE_IO._system_clipboard
        SECURE_IO._system_clipboard = None
        self.addCleanup(setattr, SECURE_IO, "_system_clipboard", saved)
        self.addCleanup(SECURE_IO.clear_clipboard_if_ours)
        self.pyperclip_calls = []
        fake = mock.Mock()
        fake.determine_clipboard = lambda: (self.pyperclip_calls.append, lambda: "")
        patcher = mock.patch.dict(sys.modules, {"pyperclip": fake})
        patcher.start()
        self.addCleanup(patcher.stop)

    def on(self, platform):
        patcher = mock.patch.object(sys, "platform", platform)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_windows_uses_the_marking_backend_end_to_end(self):
        win = FakeWindows()
        self.on("win32")
        with mock.patch.object(SECURE_IO, "_WindowsClipboard",
                               lambda: REAL_WINDOWS_CLASS(win, win, sleep=lambda s: None)):
            self.assertTrue(SECURE_IO.copy_secret(SECRET, timeout=0.05))
            self.assertEqual(len(win.clipboard), 4)
            time.sleep(1.0)
        self.assertEqual(win.clipboard, {})
        self.assertFalse(SECURE_IO.has_pending_secret())
        self.assertEqual(self.pyperclip_calls, [])

    def test_windows_never_falls_back_to_an_unmarked_copy(self):
        self.on("win32")
        with mock.patch.object(SECURE_IO, "_WindowsClipboard", side_effect=OSError("no user32")):
            self.assertFalse(SECURE_IO.copy_secret(SECRET))
        self.assertEqual(self.pyperclip_calls, [])
        self.assertFalse(SECURE_IO.has_pending_secret())

    def test_windows_copy_that_cannot_be_marked_reports_not_copied(self):
        win = FakeWindows()
        win.fail_set = {"CanUploadToCloudClipboard"}
        self.on("win32")
        with mock.patch.object(SECURE_IO, "_WindowsClipboard",
                               lambda: REAL_WINDOWS_CLASS(win, win, sleep=lambda s: None)):
            self.assertFalse(SECURE_IO.copy_secret(SECRET))
        self.assertEqual(win.clipboard, {})
        self.assertEqual(self.pyperclip_calls, [])

    def test_macos_uses_the_marking_backend(self):
        mac = FakeMac()
        self.on("darwin")
        with mock.patch.object(SECURE_IO, "_MacClipboard",
                               lambda: REAL_MAC_CLASS(mac.send, mac.get_class)):
            self.assertTrue(SECURE_IO.copy_secret(SECRET))
            self.assertEqual(mac.items, {CONCEALED: "", TEXT: SECRET})
            self.assertTrue(SECURE_IO.clear_clipboard_if_ours())
        self.assertEqual(mac.items, {})
        self.assertEqual(self.pyperclip_calls, [])

    def test_macos_falls_back_to_pbcopy_when_the_api_is_unreachable(self):
        self.on("darwin")
        with mock.patch.object(SECURE_IO, "_MacClipboard", side_effect=OSError("no AppKit")):
            self.assertTrue(SECURE_IO.copy_secret(SECRET))
        self.assertEqual(self.pyperclip_calls, [SECRET])

    def test_linux_uses_pyperclip(self):
        self.on("linux")
        self.assertIsNone(SECURE_IO._native_clipboard())
        self.assertTrue(SECURE_IO.copy_secret(SECRET))
        self.assertEqual(self.pyperclip_calls, [SECRET])


REAL_WINDOWS_CLASS = SECURE_IO._WindowsClipboard
REAL_MAC_CLASS = SECURE_IO._MacClipboard


class RealBase(unittest.TestCase):
    def setUp(self):
        SECURE_IO.set_clipboard_backend(None, None)
        saved = SECURE_IO._system_clipboard
        SECURE_IO._system_clipboard = None
        self.addCleanup(setattr, SECURE_IO, "_system_clipboard", saved)
        self.addCleanup(SECURE_IO.clear_clipboard_if_ours)

    def round_trip(self, backend, other_reader):
        self.assertTrue(SECURE_IO.copy_secret(SECRET, timeout=60))
        # BUNKER picked the marking backend, not the plain one.
        self.assertIs(type(SECURE_IO._system_clipboard[0].__self__), type(backend))
        self.assertEqual(backend.paste(), SECRET)
        self.assertEqual(other_reader().rstrip("\r\n"), SECRET)   # another program can paste it
        marks = backend.marks_present()
        self.assertTrue(SECURE_IO.clear_clipboard_if_ours())
        self.assertEqual(backend.paste(), "")
        self.assertEqual(other_reader().rstrip("\r\n"), "")
        self.assertEqual(backend.marks_present(), [])
        return marks

    def leaves_a_later_copy_alone(self, backend, other_writer):
        self.assertTrue(SECURE_IO.copy_secret(SECRET, timeout=60))
        other_writer("something the user copied")
        self.assertFalse(SECURE_IO.clear_clipboard_if_ours())
        self.assertEqual(backend.paste().rstrip("\r\n"), "something the user copied")
        backend.clear()


@unittest.skipUnless(REAL and sys.platform == "win32",
                     "needs Windows and BUNKER_TEST_REAL_CLIPBOARD=1")
class RealWindowsClipboard(RealBase):
    def test_copy_mark_read_and_clear(self):
        import pyperclip
        marks = self.round_trip(SECURE_IO._WindowsClipboard(), pyperclip.paste)
        self.assertEqual(marks, list(SECURE_IO._WindowsClipboard.MARKS))

    def test_a_later_copy_by_another_program_is_left_alone(self):
        import pyperclip
        self.leaves_a_later_copy_alone(SECURE_IO._WindowsClipboard(), pyperclip.copy)

    def test_timer_thread_clears(self):
        backend = SECURE_IO._WindowsClipboard()
        self.assertTrue(SECURE_IO.copy_secret(SECRET, timeout=0.2))
        time.sleep(2.0)
        self.assertEqual(backend.paste(), "")


@unittest.skipUnless(REAL and sys.platform == "darwin",
                     "needs macOS and BUNKER_TEST_REAL_CLIPBOARD=1")
class RealMacClipboard(RealBase):
    @staticmethod
    def pbpaste():
        return subprocess.run(["pbpaste"], capture_output=True, timeout=20,
                              env={**os.environ, "LANG": "en_US.UTF-8"}).stdout.decode("utf-8")

    @staticmethod
    def pbcopy(text):
        subprocess.run(["pbcopy"], input=text.encode("utf-8"), timeout=20, check=True,
                       env={**os.environ, "LANG": "en_US.UTF-8"})

    def test_copy_mark_read_and_clear(self):
        marks = self.round_trip(SECURE_IO._MacClipboard(), self.pbpaste)
        self.assertEqual(marks, [CONCEALED])

    def test_a_later_copy_by_another_program_is_left_alone(self):
        self.leaves_a_later_copy_alone(SECURE_IO._MacClipboard(), self.pbcopy)

    def test_timer_thread_clears(self):
        backend = SECURE_IO._MacClipboard()
        self.assertTrue(SECURE_IO.copy_secret(SECRET, timeout=0.2))
        time.sleep(2.0)
        self.assertEqual(backend.paste(), "")


if __name__ == "__main__":
    unittest.main()
