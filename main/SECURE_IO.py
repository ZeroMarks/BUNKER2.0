"""
SECURE_IO - the one place where BUNKER lets a secret leave the vault.

Rules this module enforces for the rest of the code base:

* Clipboard: every password or note copied to the clipboard goes through
  ``copy_secret``. The clipboard is cleared after ``CLIPBOARD_CLEAR_SECONDS``
  and again when BUNKER exits - but only if it still holds that secret, so
  something the user copied afterwards is left alone.
* Screen: a secret is only shown when the user explicitly asked to see it,
  and only through ``reveal_secret``. Nothing else prints secrets.
* Errors: exception text can contain decrypted data (for example a
  ``UnicodeDecodeError`` quotes the bytes it failed on). Error messages shown
  to the user are built with ``safe_error``, which never includes the
  exception's message for non-OS errors.

Nothing in this module writes to disk or to a log, and it never keeps the
secret itself after copying - only a SHA-256 fingerprint used to recognise
it on the clipboard later.
"""

import atexit
import hashlib
import hmac
import sys
import threading

CLIPBOARD_CLEAR_SECONDS = 30
MASK = "********"

# BUNKER imports modules both as ``main.X`` and as ``X`` (BUNKER.py puts the
# main/ folder on sys.path). Register this module under both names so there
# is exactly one clipboard timer and one fingerprint for the whole process.
_this = sys.modules[__name__]
for _alias in ("SECURE_IO", "main.SECURE_IO"):
    sys.modules.setdefault(_alias, _this)

_lock = threading.RLock()
_timer = None
_fingerprint = None
_backend = None  # (copy, paste) callables; None means "use pyperclip"


def set_clipboard_backend(copy, paste):
    """Replace the clipboard backend (used by tests). Pass None, None to reset."""
    global _backend
    _backend = None if copy is None else (copy, paste)


def _clipboard():
    if _backend is not None:
        return _backend
    import pyperclip
    return pyperclip.copy, pyperclip.paste


def _digest(text):
    return hashlib.sha256(str(text).encode("utf-8", "surrogatepass")).digest()


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
    global _timer, _fingerprint
    with _lock:
        _cancel_timer()
        try:
            copy, _ = _clipboard()
            copy(str(value))
        except Exception:
            _fingerprint = None
            return False
        _fingerprint = _digest(value)
        timer = threading.Timer(timeout, clear_clipboard_if_ours)
        timer.daemon = True
        _timer = timer
        timer.start()
        return True


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
    stream.write(f"{label}{value}\n")
    stream.flush()


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


# Clear on a normal interpreter exit. Paths that leave via os._exit() skip
# atexit, so secure_cleanup_common() also calls clear_clipboard_if_ours().
atexit.register(clear_clipboard_if_ours)
