"""
SECURE_IO - the one place where BUNKER lets a secret leave the vault.

Rules this module enforces for the rest of the code base:

* Clipboard: every password or note copied to the clipboard goes through
  ``copy_secret``. The clipboard is cleared after ``CLIPBOARD_CLEAR_SECONDS``
  and again when BUNKER exits - but only if it still holds that secret, so
  something the user copied afterwards is left alone. On Windows and macOS
  the copy is also marked as a secret, so the system's clipboard history and
  device sync leave it out (``_WindowsClipboard``, ``_MacClipboard``).
* Screen: a secret is only shown when the user explicitly asked to see it,
  and only through ``reveal_secret``. Nothing else prints secrets. A secret
  BUNKER has just generated is handed over with ``offer_secret``: clipboard
  first, screen only if the user types ``v``.
* Errors: exception text can contain decrypted data (for example a
  ``UnicodeDecodeError`` quotes the bytes it failed on). Error messages shown
  to the user are built with ``safe_error``, which never includes the
  exception's message for non-OS errors.

Nothing in this module writes to disk or to a log, and it never keeps the
secret itself after copying - only a keyed fingerprint (HMAC-SHA256 under a
random per-process key) used to recognise it on the clipboard later.
"""

import atexit
import contextlib
import hashlib
import hmac
import os
import sys
import threading

def _clipboard_seconds(default=30, low=5, high=300):
    """Clipboard clear delay. Set BUNKER_CLIPBOARD_SECONDS to change it
    (5-300 s); anything else falls back to the default."""
    raw = os.environ.get("BUNKER_CLIPBOARD_SECONDS", "")
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if low <= value <= high else default


CLIPBOARD_CLEAR_SECONDS = _clipboard_seconds()
MASK = "********"

# Always import this module as ``main.SECURE_IO`` so the process has one
# clipboard timer and one fingerprint.

_lock = threading.RLock()
_timer = None
_fingerprint = None
_generation = 0  # bumped on every copy; a timer only acts on its own copy
_backend = None  # (copy, paste) callables; None means "use pyperclip"


def set_clipboard_backend(copy, paste):
    """Replace the clipboard backend (used by tests). Pass None, None to reset."""
    global _backend
    _backend = None if copy is None else (copy, paste)


_system_clipboard = None  # the system (copy, paste), once one has been found


def _native_clipboard():
    """Return (copy, paste) for a backend that also marks the copy as a
    secret, or None where BUNKER has none (Linux and other systems).

    Windows has no fallback: if the marks cannot be set there, nothing is
    copied. On macOS, if the pasteboard API cannot be reached at all, the
    plain ``pbcopy`` path is used instead, without the marks.
    """
    if sys.platform == "win32":
        backend = _WindowsClipboard()
        return backend.copy, backend.paste
    if sys.platform == "darwin":
        try:
            backend = _MacClipboard()
        except Exception:
            return None
        return backend.copy, backend.paste
    return None


def _clipboard():
    """Return (copy, paste). Raises if the only clipboard tool is unsafe."""
    global _system_clipboard
    if _backend is not None:
        return _backend
    if _system_clipboard is not None:
        return _system_clipboard
    native = _native_clipboard()
    if native is not None:
        _system_clipboard = native
        return native
    import pyperclip
    copy, paste = pyperclip.determine_clipboard()
    # pyperclip's Klipper backend passes the text as a command-line argument
    # (qdbus ... setClipboardContents <text>), where other local users can
    # read it from the process list. Treat it as "no clipboard" instead.
    if "klipper" in getattr(copy, "__name__", "").lower():
        raise RuntimeError("clipboard tool refused")
    if callable(copy) and type(copy).__name__ != "ClipboardUnavailable":
        _system_clipboard = (copy, paste)
    return copy, paste


class _WindowsClipboard:
    """Windows clipboard through the Win32 API, with the copy marked so that
    clipboard history (Win+V) and cloud clipboard sync leave it out.

    Windows documents three registered clipboard formats for this ("Cloud
    Clipboard and Clipboard History Formats",
    https://learn.microsoft.com/windows/win32/dataxchg/clipboard-formats):

    * ``ExcludeClipboardContentFromMonitorProcessing`` - any data: keep every
      format out of the history and off the user's other devices;
    * ``CanIncludeInClipboardHistory`` - a DWORD of zero: not in the history;
    * ``CanUploadToCloudClipboard`` - a DWORD of zero: not synchronised.

    All three are placed before the text, inside one open/close of the
    clipboard, so the text is never on the clipboard without them. If any
    of them cannot be set, the clipboard is emptied and the copy fails.

    These marks are requests that Windows itself honours. A third-party
    clipboard manager only honours them if its author chose to.

    ``user32`` and ``kernel32`` can be passed in for tests; by default the
    real libraries are loaded, which only works on Windows.
    """

    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002
    DWORD_ZERO = b"\x00\x00\x00\x00"
    MARKS = (
        "ExcludeClipboardContentFromMonitorProcessing",
        "CanIncludeInClipboardHistory",
        "CanUploadToCloudClipboard",
    )
    OPEN_TRIES = 50          # another program may hold the clipboard briefly
    OPEN_WAIT_SECONDS = 0.01

    def __init__(self, user32=None, kernel32=None, sleep=None):
        import time
        if user32 is None or kernel32 is None:
            user32, kernel32 = self._load()
        self._user32 = user32
        self._kernel32 = kernel32
        self._sleep = sleep if sleep is not None else time.sleep

    @staticmethod
    def _load():
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        # Handles and pointers are 64-bit on 64-bit Windows; without these
        # declarations ctypes would truncate them to 32-bit ints.
        handle = ctypes.c_void_p
        user32.OpenClipboard.argtypes = [handle]
        user32.OpenClipboard.restype = wintypes.BOOL
        user32.CloseClipboard.argtypes = []
        user32.CloseClipboard.restype = wintypes.BOOL
        user32.EmptyClipboard.argtypes = []
        user32.EmptyClipboard.restype = wintypes.BOOL
        user32.SetClipboardData.argtypes = [wintypes.UINT, handle]
        user32.SetClipboardData.restype = handle
        user32.GetClipboardData.argtypes = [wintypes.UINT]
        user32.GetClipboardData.restype = handle
        user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
        user32.IsClipboardFormatAvailable.restype = wintypes.BOOL
        user32.RegisterClipboardFormatW.argtypes = [wintypes.LPCWSTR]
        user32.RegisterClipboardFormatW.restype = wintypes.UINT
        user32.CreateWindowExW.argtypes = [
            wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            handle, handle, handle, handle]
        user32.CreateWindowExW.restype = handle
        user32.DestroyWindow.argtypes = [handle]
        user32.DestroyWindow.restype = wintypes.BOOL
        kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
        kernel32.GlobalAlloc.restype = handle
        kernel32.GlobalLock.argtypes = [handle]
        kernel32.GlobalLock.restype = ctypes.c_void_p
        kernel32.GlobalUnlock.argtypes = [handle]
        kernel32.GlobalUnlock.restype = wintypes.BOOL
        kernel32.GlobalFree.argtypes = [handle]
        kernel32.GlobalFree.restype = handle
        kernel32.GlobalSize.argtypes = [handle]
        kernel32.GlobalSize.restype = ctypes.c_size_t
        return user32, kernel32

    @contextlib.contextmanager
    def _open(self):
        # SetClipboardData fails if the clipboard was opened without an
        # owner window and then emptied, so open it with a hidden window of
        # our own (never shown; destroyed straight after).
        window = self._user32.CreateWindowExW(
            0, "STATIC", None, 0, 0, 0, 0, 0, None, None, None, None)
        try:
            for attempt in range(self.OPEN_TRIES):
                if self._user32.OpenClipboard(window):
                    break
                self._sleep(self.OPEN_WAIT_SECONDS)
            else:
                raise OSError("clipboard busy")
            try:
                yield
            finally:
                self._user32.CloseClipboard()
        finally:
            if window:
                self._user32.DestroyWindow(window)

    def _put(self, fmt, data):
        import ctypes
        handle = self._kernel32.GlobalAlloc(self.GMEM_MOVEABLE, len(data))
        if not handle:
            raise OSError("clipboard memory")
        try:
            pointer = self._kernel32.GlobalLock(handle)
            if not pointer:
                raise OSError("clipboard memory")
            ctypes.memmove(pointer, data, len(data))
            self._kernel32.GlobalUnlock(handle)
            if not self._user32.SetClipboardData(fmt, handle):
                raise OSError("clipboard refused the data")
        except BaseException:
            # Windows owns the memory only after SetClipboardData succeeds.
            # Overwrite before freeing: this block may hold the secret.
            pointer = self._kernel32.GlobalLock(handle)
            if pointer:
                ctypes.memset(pointer, 0, len(data))
                self._kernel32.GlobalUnlock(handle)
            self._kernel32.GlobalFree(handle)
            raise

    def _mark_format(self, name):
        fmt = self._user32.RegisterClipboardFormatW(name)
        if not fmt:
            raise OSError("clipboard format")
        return fmt

    def copy(self, text):
        text = str(text)
        if not text:
            return self.clear()
        if "\x00" in text:
            # Clipboard text ends at the first NUL; the rest would be lost.
            raise ValueError("text cannot be copied")
        data = text.encode("utf-16-le", "surrogatepass") + b"\x00\x00"
        with self._open():
            if not self._user32.EmptyClipboard():
                raise OSError("clipboard could not be emptied")
            try:
                for name in self.MARKS:
                    self._put(self._mark_format(name), self.DWORD_ZERO)
                self._put(self.CF_UNICODETEXT, data)
            except BaseException:
                self._user32.EmptyClipboard()
                raise

    def paste(self):
        import ctypes
        with self._open():
            if not self._user32.IsClipboardFormatAvailable(self.CF_UNICODETEXT):
                return ""
            handle = self._user32.GetClipboardData(self.CF_UNICODETEXT)
            if not handle:
                raise OSError("clipboard could not be read")
            pointer = self._kernel32.GlobalLock(handle)
            if not pointer:
                raise OSError("clipboard could not be read")
            try:
                size = self._kernel32.GlobalSize(handle)
                raw = ctypes.string_at(pointer, size - size % 2)
            finally:
                self._kernel32.GlobalUnlock(handle)
        text = raw.decode("utf-16-le", "surrogatepass")
        end = text.find("\x00")
        return text if end < 0 else text[:end]

    def clear(self):
        with self._open():
            if not self._user32.EmptyClipboard():
                raise OSError("clipboard could not be emptied")

    def marks_present(self):
        """Names of the marks currently on the clipboard (used by tests)."""
        with self._open():
            return [name for name in self.MARKS
                    if self._user32.IsClipboardFormatAvailable(self._mark_format(name))]


class _MacClipboard:
    """macOS general pasteboard through AppKit, with the copy marked as a
    secret.

    * The pasteboard is prepared with ``NSPasteboardContentsCurrentHostOnly``
      (macOS 10.12+), which Apple documents as "available only on the
      current device", so Universal Clipboard does not hand the copy to the
      user's other devices
      (https://developer.apple.com/documentation/appkit/nspasteboard/contentsoptions).
    * The item carries ``org.nspasteboard.ConcealedType``, the marker
      clipboard managers agreed on for confidential content
      (https://nspasteboard.org/). It is a convention: a manager that does
      not follow it still records the copy.

    The marker is written before the text. If either write fails the
    pasteboard is cleared and the copy fails.

    ``send`` and ``get_class`` can be passed in for tests; by default the
    Objective-C runtime is loaded, which only works on macOS.
    """

    TEXT_TYPE = "public.utf8-plain-text"
    CONCEALED_TYPE = "org.nspasteboard.ConcealedType"
    CURRENT_HOST_ONLY = 1          # NSPasteboardContentsCurrentHostOnly
    UTF16_LE = 0x94000100          # NSUTF16LittleEndianStringEncoding

    def __init__(self, send=None, get_class=None):
        import ctypes
        if send is None or get_class is None:
            send, get_class = self._load()
        self._send = send
        self._get_class = get_class
        self._id = ctypes.c_void_p
        self._bool = ctypes.c_bool
        self._long = ctypes.c_long
        self._ulong = ctypes.c_ulong
        self._chars = ctypes.c_char_p
        for name in ("NSPasteboard", "NSString", "NSAutoreleasePool"):
            if not get_class(name):
                raise OSError("pasteboard unavailable")
        with self._pool():
            self._pasteboard()

    @staticmethod
    def _load():
        import ctypes
        import ctypes.util
        objc = ctypes.CDLL(ctypes.util.find_library("objc"))
        # Loading AppKit registers the NSPasteboard class with the runtime.
        ctypes.CDLL(ctypes.util.find_library("AppKit"))
        objc.objc_getClass.restype = ctypes.c_void_p
        objc.objc_getClass.argtypes = [ctypes.c_char_p]
        objc.sel_registerName.restype = ctypes.c_void_p
        objc.sel_registerName.argtypes = [ctypes.c_char_p]
        message = ctypes.cast(objc.objc_msgSend, ctypes.c_void_p).value

        def send(receiver, selector, *args, restype=ctypes.c_void_p, argtypes=()):
            # objc_msgSend must be called with the exact C signature of the
            # method, so build a typed function pointer for each call.
            prototype = ctypes.CFUNCTYPE(
                restype, ctypes.c_void_p, ctypes.c_void_p, *argtypes)
            return prototype(message)(
                receiver, objc.sel_registerName(selector.encode("ascii")), *args)

        def get_class(name):
            return objc.objc_getClass(name.encode("ascii"))

        return send, get_class

    @contextlib.contextmanager
    def _pool(self):
        pool = self._send(self._send(self._get_class("NSAutoreleasePool"), "alloc"), "init")
        try:
            yield
        finally:
            self._send(pool, "drain", restype=None)

    def _pasteboard(self):
        board = self._send(self._get_class("NSPasteboard"), "generalPasteboard")
        if not board:
            raise OSError("pasteboard unavailable")
        return board

    @contextlib.contextmanager
    def _string(self, text):
        data = text.encode("utf-16-le", "surrogatepass")
        string = self._send(
            self._send(self._get_class("NSString"), "alloc"),
            "initWithBytes:length:encoding:", data, len(data), self.UTF16_LE,
            argtypes=(self._chars, self._ulong, self._ulong))
        if not string:
            raise ValueError("text cannot be copied")
        try:
            yield string
        finally:
            self._send(string, "release", restype=None)

    def copy(self, text):
        text = str(text)
        if not text:
            return self.clear()
        with self._pool():
            board = self._pasteboard()
            with self._string(text) as secret, \
                    self._string(self.TEXT_TYPE) as text_type, \
                    self._string(self.CONCEALED_TYPE) as concealed, \
                    self._string("") as empty:
                self._send(board, "prepareForNewContentsWithOptions:",
                           self.CURRENT_HOST_ONLY,
                           restype=self._long, argtypes=(self._ulong,))
                try:
                    for value, kind in ((empty, concealed), (secret, text_type)):
                        if not self._send(board, "setString:forType:", value, kind,
                                          restype=self._bool,
                                          argtypes=(self._id, self._id)):
                            raise OSError("pasteboard refused the data")
                except BaseException:
                    self._send(board, "clearContents", restype=self._long)
                    raise

    def paste(self):
        with self._pool():
            board = self._pasteboard()
            with self._string(self.TEXT_TYPE) as text_type:
                string = self._send(board, "stringForType:", text_type,
                                    argtypes=(self._id,))
                if not string:
                    return ""
                raw = self._send(string, "UTF8String", restype=self._chars)
                if raw is None:
                    # Text is there but cannot be read: say so, so the
                    # caller clears it rather than taking it for empty.
                    raise OSError("pasteboard could not be read")
                return raw.decode("utf-8", "replace")

    def clear(self):
        with self._pool():
            self._send(self._pasteboard(), "clearContents", restype=self._long)

    def marks_present(self):
        """Marker types currently on the pasteboard (used by tests)."""
        with self._pool():
            board = self._pasteboard()
            types = self._send(board, "types")
            with self._string(self.CONCEALED_TYPE) as concealed:
                if types and self._send(types, "containsObject:", concealed,
                                        restype=self._bool, argtypes=(self._id,)):
                    return [self.CONCEALED_TYPE]
            return []


# Random key for this process only. The fingerprint is an HMAC under it, so
# it is useless outside this process (a leaked log, core dump fragment or
# swap page holding just the fingerprint cannot be used to test guesses).
# Someone who can read this process's whole memory has the key as well -
# and the clipboard itself - so this does not defend against that.
_FINGERPRINT_KEY = os.urandom(32)


def _digest(text):
    # Clipboard backends may rewrite line endings or trailing whitespace, so
    # compare a normalised form; otherwise a copied note might never match.
    norm = str(text).replace("\r\n", "\n").replace("\r", "\n").rstrip()
    return hmac.new(_FINGERPRINT_KEY, norm.encode("utf-8", "surrogatepass"),
                    hashlib.sha256).digest()


def _cancel_timer():
    global _timer
    if _timer is not None and _timer is not threading.current_thread():
        _timer.cancel()
    _timer = None


def copy_secret(value, timeout=CLIPBOARD_CLEAR_SECONDS):
    """Copy ``value`` to the clipboard and schedule it to be cleared.

    Returns True on success, False if the clipboard is unavailable. Never
    raises and never includes the value in any message.
    """
    global _timer, _fingerprint, _generation
    with _lock:
        previous = _fingerprint
        _cancel_timer()
        _generation += 1
        generation = _generation
        # Record the fingerprint before copying: if an exit handler runs in
        # between, it must already know this secret is ours to clear.
        _fingerprint = _digest(value)
        try:
            copy, _ = _clipboard()
            copy(str(value))
        except Exception:
            # The previous secret's timer is already cancelled; clear it now
            # rather than leave it on the clipboard with nothing tracking it.
            # If that clear fails too, the fingerprint stays so exit cleanup
            # tries again.
            _fingerprint = previous
            clear_clipboard_if_ours()
            return False
        timer = threading.Timer(timeout, _timer_fired, args=(generation,))
        timer.daemon = True
        _timer = timer
        timer.start()
        return True


def _timer_fired(generation):
    # A timer that fired while a newer copy was being made must not clear it.
    with _lock:
        if generation != _generation:
            return False
        return clear_clipboard_if_ours()


def clear_clipboard_if_ours():
    """Clear the clipboard if it still holds the last secret BUNKER copied.

    If the clipboard cannot be read, it is cleared anyway (fail closed).
    Returns True if the clipboard was cleared.
    """
    global _fingerprint
    with _lock:
        _cancel_timer()
        if _fingerprint is None:
            return False
        expected, _fingerprint = _fingerprint, None
        try:
            copy, paste = _clipboard()
        except Exception:
            # Keep tracking it so a later attempt (e.g. at exit) can retry.
            _fingerprint = expected
            return False
        try:
            current = paste()
            ours = current is not None and hmac.compare_digest(_digest(current), expected)
        except Exception:
            ours = True
        if not ours:
            return False
        try:
            copy("")
            return True
        except Exception:
            # Keep tracking it so a later attempt (e.g. at exit) can retry.
            _fingerprint = expected
            return False


def has_pending_secret():
    """True while a copied secret is waiting to be cleared."""
    with _lock:
        return _fingerprint is not None


def copy_notice(what="Password", timeout=CLIPBOARD_CLEAR_SECONDS):
    """User-facing text describing what happened to the clipboard."""
    return (f"{what} copied to clipboard. It will be cleared in {timeout} seconds "
            f"or when BUNKER closes.")


def reveal_secret(label, value, out=None):
    """Show a secret on screen. Call only after the user explicitly asked to see it.

    This is the single intended display path for secrets; it writes to the
    terminal only - never to a log or a file.
    """
    stream = out if out is not None else sys.stdout
    from main import TERMINAL
    if isinstance(stream, TERMINAL._EmojiFreeStream):
        # BUNKER_NO_EMOJI strips pictographs from BUNKER's own text. A secret
        # must be shown exactly as stored, so only the label is filtered.
        stream.write(label)
        stream._stream.write(f"{value}\n")
    else:
        stream.write(f"{label}{value}\n")
    stream.flush()


SHOW_KEY = "v"


def offer_secret(what, value, ask, timeout=CLIPBOARD_CLEAR_SECONDS, warning="",
                 required=False, stop=()):
    """Hand over a secret BUNKER has just generated: clipboard first, screen
    only if the user asks.

    ``what`` names it ("Generated password"). ``ask`` is the prompt function
    (``timeoutInput``); its last answer is returned so the caller can handle
    a timeout. The secret is copied with the usual auto-clear and is printed
    only when the user types ``v``. If the clipboard is unavailable the user
    is told plainly that nothing was copied. ``warning`` is one extra plain
    sentence shown before the prompt (for example what is lost without it).

    ``required`` is for a secret the user cannot get again (an export
    passphrase). If it could not be copied, the screen is the only way to
    hand it over, so the prompt repeats until the user types ``v``; it never
    lets them continue with nothing. ``stop`` lists answers that end the
    prompt anyway (the caller's timeout code).

    All text here is plain: no colour, emoji or box drawing, so it reads the
    same in a screen reader and with NO_COLOR.
    """
    copied = copy_secret(value, timeout)
    if copied:
        print(copy_notice(what, timeout))
    else:
        print(f"Could not access the clipboard. {what} was NOT copied.")
    if warning:
        print(warning)
    if copied:
        prompt = (f"Type '{SHOW_KEY}' then Enter to show it on screen, "
                  f"or press Enter to continue without showing it: ")
    elif required:
        prompt = f"Type '{SHOW_KEY}' then Enter to show it on screen: "
    else:
        prompt = (f"Type '{SHOW_KEY}' then Enter to show it on screen, "
                  f"or press Enter to continue without it: ")
    while True:
        answer = ask(prompt)
        if isinstance(answer, str) and answer.strip().lower() == SHOW_KEY:
            reveal_secret(f"{what}: ", value)
            return answer
        if copied or not required or not isinstance(answer, str) or answer in stop:
            return answer
        print(f"It was not copied, so it has to be shown. Type '{SHOW_KEY}' then Enter.")


def mask(value=None):
    """Fixed-width mask; deliberately does not reveal the secret's length."""
    return MASK


def safe_error(exc):
    """Describe an exception without its message.

    OS errors keep their (non-secret) reason, e.g. "PermissionError: Permission
    denied". Everything else is reduced to the exception class name, because
    messages from decoding/decryption/JSON errors can quote secret data.
    """
    name = type(exc).__name__
    if isinstance(exc, OSError) and getattr(exc, "strerror", None):
        return f"{name}: {exc.strerror}"
    return name


@contextlib.contextmanager
def _atomic_private(path, mode, encoding=None):
    """Yield a file that atomically replaces ``path`` on success (mode 0600).

    Data goes to a new temp file in the same folder (created exclusively,
    owner-only), is flushed to disk, then replaces ``path`` in one step. This
    never follows a symlink at ``path``, never changes another file's
    permissions, and on failure leaves the existing file untouched.
    """
    import os
    import tempfile
    folder = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".bunker-", suffix=".tmp", dir=folder)
    try:
        with os.fdopen(fd, mode, encoding=encoding) as f:
            yield f
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def open_private(path, encoding="utf-8"):
    """Text-mode private atomic write; used for exports."""
    return _atomic_private(path, "w", encoding)


def write_private_bytes(path, data):
    """Atomically write ``data`` to ``path`` with owner-only permissions.

    A crash or power loss leaves either the old file or the new one, never a
    truncated mix. On macOS/Linux the file is owner-only (0600) from the
    moment it is created; on Windows, permissions follow the folder.
    """
    with _atomic_private(path, "wb") as f:
        f.write(data)


def install_exit_signal_handlers():
    """Clear the clipboard when the terminal is closed or the process is told
    to stop (SIGHUP/SIGTERM), which otherwise kill BUNKER without cleanup.

    Only replaces handlers still at their default, and only from the main
    thread. Returns the list of signals handled.
    """
    import os
    import signal
    installed = []
    if threading.current_thread() is not threading.main_thread():
        return installed
    for name in ("SIGHUP", "SIGTERM"):
        signum = getattr(signal, name, None)
        if signum is None or signal.getsignal(signum) is not signal.SIG_DFL:
            continue

        def _handler(num, _frame):
            clear_clipboard_if_ours()
            signal.signal(num, signal.SIG_DFL)
            os.kill(os.getpid(), num)

        signal.signal(signum, _handler)
        installed.append(name)
    return installed


# Clear on a normal interpreter exit. Paths that leave via os._exit() skip
# atexit, so secure_cleanup_common() also calls clear_clipboard_if_ours().
atexit.register(clear_clipboard_if_ours)
