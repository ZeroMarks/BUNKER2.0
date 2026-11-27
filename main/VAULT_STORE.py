"""Shared vault storage: the one place that knows how Bunker.mmf is read,
written and laid out, so the desktop and mobile UIs stay interchangeable.

Format (unchanged from the desktop UI):

* ``Bunker.mmf`` is ``nonce(12) + AES-GCM ciphertext`` of the JSON text of ONE
  flat dict: ``{entry_id: entry_dict}``. Every value must be a dict - desktop
  code calls ``.get()`` on all of them.
* Profile entry: ``domain``, ``email``, ``username``, ``password`` (each
  base64 of the encrypted bytes) and ``favorite`` (plain bool).
* Note entry: ``title``, ``content`` (base64 of encrypted bytes), ``tags``
  (list of base64 of encrypted bytes; ``N/A`` when empty, ``PRIVATE`` for
  private notes), ``favorite`` and ``private`` (plain bools).

One writer at a time: two BUNKER windows (or the desktop and mobile
interfaces) may have the same vault open. Every change is made under an
exclusive lock on ``Bunker.mmf.lock`` (``locked``), and nothing is written
from a copy that is older than the file:

* ``modify`` loads, changes and saves while holding the lock.
* ``commit`` saves a vault that has been held in memory for a while (the
  desktop interface). If the file changed since that copy was loaded, the
  other window's changes are merged in first (``merge``); if the file can no
  longer be opened with this key, the save is refused.

This module has no interactive code and never deletes anything. Entries it
does not understand are passed through untouched.
"""
import base64
import contextlib
import errno
import hashlib
import json
import os
import threading
import time
import uuid

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

DB_FILE = "Bunker.mmf"
NA = "N/A"
PRIVATE_TAG = "PRIVATE"


# --- encryption primitives (byte-compatible with vault.encrypt_data/decrypt_data)

def encrypt_bytes(data, key):
    if isinstance(data, str):
        data = data.encode("utf-8")
    nonce = os.urandom(12)
    return nonce + AESGCM(base64.urlsafe_b64decode(key)).encrypt(nonce, data, None)


def decrypt_bytes(blob, key):
    return AESGCM(base64.urlsafe_b64decode(key)).decrypt(blob[:12], blob[12:], None)


def derive_key(password, salt):
    """The key the desktop login derives (Argon2id, then PBKDF2-SHA3-256,
    password also used as pepper). Delegates to INITIALIZE so there is one
    implementation; imported lazily because INITIALIZE imports this module."""
    from main.INITIALIZE import vault as login_vault
    return login_vault.derive_key_hybrid(password, salt, password)


# --- file I/O

def write_bytes_atomic(path, data):
    """Replace ``path`` with ``data`` atomically and owner-only (0600): it is
    either the old or the new content, never a truncated mix. Shared with
    the salt/config writers via SECURE_IO.write_private_bytes."""
    from main.SECURE_IO import write_private_bytes
    write_private_bytes(os.fspath(path), data)


# --- one writer at a time

LOCK_SUFFIX = ".lock"
LOCK_TIMEOUT = 10.0   # seconds to wait for another window to finish saving
_LOCK_POLL = 0.05


class VaultBusy(OSError):
    """Another BUNKER window held the vault lock for the whole wait."""

    def __init__(self):
        super().__init__(errno.EAGAIN, "another BUNKER window is saving this vault; "
                                       "nothing was changed, try again")


class VaultChangedElsewhere(OSError):
    """Bunker.mmf was replaced by something this key cannot open (for
    example the master password was changed in another window). Saving
    over it would destroy it, so the save is refused."""

    def __init__(self):
        super().__init__(errno.ESTALE, "the vault was replaced in another BUNKER window "
                                       "and no longer opens with this login; nothing was "
                                       "saved, close BUNKER and log in again")


class VaultGone(VaultChangedElsewhere):
    """Bunker.mmf was there when this window loaded it and is gone now (for
    example the failed-login limit destroyed the vault in another window).
    Writing the held copy would bring destroyed entries back, so the save is
    refused. A subclass, so code that handles VaultChangedElsewhere handles
    this too."""

    def __init__(self):
        OSError.__init__(self, errno.ENOENT, "the vault was removed in another BUNKER "
                                             "window; nothing was saved, close BUNKER")


# Errors that mean "this folder cannot lock files at all" (some network and
# removable-storage file systems). The lock is skipped there rather than
# making the vault read-only; commit() still checks for changes before it
# writes.
_NO_LOCKING = {getattr(errno, name) for name in
               ("ENOLCK", "ENOSYS", "EOPNOTSUPP", "ENOTSUP", "EINVAL")
               if hasattr(errno, name)}

_thread_lock = threading.RLock()   # one writer per process, re-entrant
_held = {}                         # lock path -> nesting depth in this process


def _try_lock(fd):
    """Take the exclusive lock without waiting. True if this process now
    holds it, False if another process does. Raises OSError with an errno
    from ``_NO_LOCKING`` where locking is not available."""
    if os.name == "nt":
        import msvcrt
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            return True
        except OSError as e:
            if e.errno in (errno.EACCES, errno.EDEADLK):
                return False
            raise
    try:
        import fcntl
    except ImportError:
        raise OSError(errno.ENOSYS, "file locking is not available") from None
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError as e:
        if e.errno in (errno.EWOULDBLOCK, errno.EAGAIN, errno.EACCES):
            return False
        raise


def _unlock(fd):
    try:
        if os.name == "nt":
            import msvcrt
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_UN)
    except (OSError, ImportError):
        pass  # closing the descriptor releases it as well


def lock_path(path=DB_FILE):
    return os.fspath(path) + LOCK_SUFFIX


@contextlib.contextmanager
def locked(path=DB_FILE, timeout=None):
    """Hold the vault's write lock for the duration of the block.

    The lock is on a separate, empty, owner-only file next to the vault
    (``Bunker.mmf.lock``), because every save replaces ``Bunker.mmf`` itself.
    It is released by the operating system if BUNKER dies, so a crash never
    leaves the vault locked. The lock file is left in place on purpose:
    deleting it would let two processes lock two different files.

    Waits up to ``timeout`` seconds (default ``LOCK_TIMEOUT``) and then
    raises ``VaultBusy``. Re-entrant within one process. Reading the vault
    needs no lock: a save swaps the whole file in one step.
    """
    if timeout is None:
        timeout = LOCK_TIMEOUT
    name = os.path.abspath(lock_path(path))
    with _thread_lock:
        if _held.get(name):
            _held[name] += 1
            try:
                yield
            finally:
                _held[name] -= 1
            return
        fd = os.open(name, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            got = False
            deadline = time.monotonic() + timeout
            while True:
                try:
                    got = _try_lock(fd)
                except OSError as e:
                    if e.errno not in _NO_LOCKING:
                        raise
                    break  # no locking on this file system: carry on without
                if got:
                    break
                if time.monotonic() >= deadline:
                    raise VaultBusy()
                time.sleep(_LOCK_POLL)
            _held[name] = 1
            try:
                yield
            finally:
                del _held[name]
                if got:
                    _unlock(fd)
        finally:
            os.close(fd)


# --- loading and saving

class VaultDict(dict):
    """The vault dict, plus what the file looked like when it was loaded:
    a plain copy of the entries (``_base``) and the SHA-256 of the file
    (``_digest``). ``commit`` uses them to notice, and merge in, changes
    another window made in the meantime. Behaves exactly like a dict."""
    __slots__ = ("_base", "_digest")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._base = None
        self._digest = None


def _digest_of(blob):
    return hashlib.sha256(blob).hexdigest()


def _snapshot(db):
    return json.loads(json.dumps(db))


def _mark_synced(db, blob):
    if isinstance(db, VaultDict):
        db._base = _snapshot(db)
        db._digest = _digest_of(blob)


def open_blob(blob, hashed_pass):
    """Decrypt the bytes of a vault file into a ``VaultDict`` that remembers
    them. Errors propagate."""
    data = json.loads(decrypt_bytes(blob, hashed_pass).decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("vault is not a dict")
    db = VaultDict(data)
    _mark_synced(db, blob)
    return db


def fork(db):
    """A copy of ``db`` to prepare a change on, which still remembers what
    the file looked like when ``db`` was loaded. Give it back with ``adopt``
    once it has been saved."""
    copy = VaultDict(db)
    copy._base = getattr(db, "_base", None)
    copy._digest = getattr(db, "_digest", None)
    return copy


def adopt(db, saved):
    """Make ``db`` (in place) the vault that was just saved as ``saved``."""
    if db is saved:
        return
    db.clear()
    db.update(saved)
    if isinstance(db, VaultDict):
        db._base = getattr(saved, "_base", None)
        db._digest = getattr(saved, "_digest", None)


def revert(db):
    """Take unsaved changes back out of ``db`` (in place): it becomes what
    the file held when it was loaded or last saved. No-op for a plain dict."""
    base = getattr(db, "_base", None)
    if base is not None:
        db.clear()
        db.update(_snapshot(base))


def load(hashed_pass, path=DB_FILE):
    """Decrypt and return the vault dict. Errors (missing file, wrong key,
    corrupt data) propagate; callers must not treat them as "empty vault"."""
    with open(path, "rb") as f:
        blob = f.read()
    return open_blob(blob, hashed_pass)


def save(db, hashed_pass, path=DB_FILE):
    """Encrypt ``db`` and write it atomically, replacing whatever is there.
    Refuses anything that is not a flat dict of dicts, because desktop
    breaks on other shapes. To change an existing vault use ``modify`` or
    ``commit``, which keep changes made by another window."""
    if not isinstance(db, dict) or not all(isinstance(v, dict) for v in db.values()):
        raise ValueError("vault must be a flat dict of entry dicts")
    blob = encrypt_bytes(json.dumps(db).encode("utf-8"), hashed_pass)
    with locked(path):
        write_bytes_atomic(path, blob)
    _mark_synced(db, blob)


LEGACY_EMPTY_KEYS = ("notes", "accounts", "profiles")


def modify(hashed_pass, mutate, path=DB_FILE):
    """Load the vault, let ``mutate(db)`` change it in place, save atomically.

    The whole load-change-save runs under the vault lock, so two windows
    changing the vault at the same moment take turns and both changes are
    kept. Reloading right before every change keeps edits made by another
    UI since this one started. Empty list values under the old mobile keys
    ("notes", "accounts", "profiles") are dropped first: they are the only
    non-dict values this project ever wrote, and desktop cannot read them.
    Any other non-dict value makes save() refuse, so nothing is overwritten.
    Returns whatever ``mutate`` returns. Raises ``VaultBusy`` if another
    window holds the lock for ``LOCK_TIMEOUT`` seconds.
    """
    with locked(path):
        try:
            db = load(hashed_pass, path)
        except InvalidTag:
            # The file no longer opens with this login's key: most likely the
            # master password was changed in another window. Say so plainly.
            raise VaultChangedElsewhere() from None
        for k in LEGACY_EMPTY_KEYS:
            if db.get(k) == []:
                del db[k]
        result = mutate(db)
        save(db, hashed_pass, path)
        return result


# --- saving a copy that was held in memory (desktop)

class MergeReport:
    """What ``commit`` had to do. ``merged`` is True when the file had been
    changed by another window and its changes were brought in."""

    def __init__(self):
        self.merged = False
        self.both_changed = 0   # fields changed in both; this window's value kept
        self.kept_edited = 0    # deleted here, edited elsewhere: kept
        self.kept_deleted = 0   # edited here, deleted elsewhere: kept
        self.kept_private = 0   # made private elsewhere: stays private

    def notice(self):
        """Plain-language lines for the user; empty when nothing was merged."""
        if not self.merged:
            return []
        lines = ["This vault was also changed in another BUNKER window. "
                 "Those changes were kept and are loaded here now."]
        if self.both_changed:
            lines.append(f"{self.both_changed} field(s) were changed in both windows: "
                         "this window's version was saved.")
        if self.kept_edited:
            lines.append(f"{self.kept_edited} entry(ies) deleted here had been edited in "
                         "the other window and were NOT deleted. Delete them again if "
                         "you still want them gone.")
        if self.kept_deleted:
            lines.append(f"{self.kept_deleted} entry(ies) edited here had been deleted in "
                         "the other window and were kept.")
        if self.kept_private:
            lines.append(f"{self.kept_private} note(s) were made private in the other "
                         "window and stay private: the tag or privacy change made here "
                         "to them was not saved.")
        return lines


_MISSING = object()
# Fields that only make sense together: a private note's tags are replaced
# by the PRIVATE marker, so one side's "private" must not be combined with
# the other side's "tags".
_COUPLED_FIELDS = (("private", "tags"),)
_PRIVACY_GROUP = ("private", "tags")


def _same(a, b, key):
    """True if two stored values mean the same. Encrypted fields get a fresh
    nonce every time they are written, so equal text can be stored as
    different strings; those are compared after decrypting."""
    if a is b:
        return True
    if a is _MISSING or b is _MISSING:
        return False
    if a == b:
        return True
    if isinstance(a, str) and isinstance(b, str):
        try:
            return dec_tag(a, key) == dec_tag(b, key)
        except Exception:
            return False
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_same(x, y, key) for x, y in zip(a, b))
    return False


def _entry_same(a, b, key):
    """True if two versions of an entry hold the same values. A desktop edit
    where every value was kept re-encrypts every field, so the stored
    strings differ although nothing changed; compare those field by field."""
    if a is b or a == b:
        return True
    if not (isinstance(a, dict) and isinstance(b, dict)):
        return False
    return all(_same(a.get(n, _MISSING), b.get(n, _MISSING), key)
               for n in set(a) | set(b))


def _merge_entry(base, ours, disk, key, report):
    """Field-by-field merge of one entry changed in both windows. A field
    only one side changed takes that side's value; a field both changed
    takes ours (this window is the one saving right now)."""
    names = list(disk) + [n for n in ours if n not in disk]
    we_changed = {n for n in names
                  if not _same(ours.get(n, _MISSING), base.get(n, _MISSING), key)}
    they_changed = {n for n in names
                    if not _same(disk.get(n, _MISSING), base.get(n, _MISSING), key)}
    for group in _COUPLED_FIELDS:
        if we_changed & set(group):
            we_changed |= {n for n in group if n in names}
        if they_changed & set(group):
            they_changed |= {n for n in group if n in names}
    # A merge never makes a note less private: when both windows changed
    # private/tags and only the other window's version is private, that
    # version wins this pair (this window's wins everything else).
    theirs_wins = set()
    if (we_changed & they_changed & set(_PRIVACY_GROUP)
            and disk.get("private") is True and ours.get("private") is not True):
        theirs_wins = {n for n in _PRIVACY_GROUP if n in names}
        report.kept_private += 1
    out = {}
    counted = set()
    for name in names:
        if name in theirs_wins:
            value = disk.get(name, _MISSING)
        elif name in we_changed:
            value = ours.get(name, _MISSING)
            if (name in they_changed
                    and not _same(value, disk.get(name, _MISSING), key)):
                group = next((g for g in _COUPLED_FIELDS if name in g), (name,))
                if group not in counted:
                    counted.add(group)
                    report.both_changed += 1
        else:
            value = disk.get(name, _MISSING)
        if value is not _MISSING:
            out[name] = value
    return out


def merge(base, ours, disk, key, report=None):
    """Three-way merge of the vault: ``base`` is what this window loaded,
    ``ours`` is that copy with this window's changes, ``disk`` is the file
    now. Returns the dict to save. Nothing either side added or edited is
    dropped:

    * changed on one side only: that side's version;
    * edited on one side and deleted on the other: the edited entry is kept;
    * edited on both sides: merged field by field (``_merge_entry``).
    """
    if report is None:
        report = MergeReport()
    out = {}
    for entry_id in list(disk) + [k for k in ours if k not in disk]:
        b = base.get(entry_id, _MISSING)
        o = ours.get(entry_id, _MISSING)
        d = disk.get(entry_id, _MISSING)
        if _entry_same(o, b, key):
            value = d                      # untouched here
        elif _entry_same(d, b, key):
            value = o                      # untouched there
        elif o is _MISSING:
            value = d                      # deleted here, edited there
            report.kept_edited += 1
        elif d is _MISSING:
            value = o                      # edited here, deleted there
            report.kept_deleted += 1
        elif isinstance(o, dict) and isinstance(d, dict):
            value = _merge_entry(b if isinstance(b, dict) else {}, o, d, key, report)
        else:
            value = o
            if o != d:
                report.both_changed += 1
        if value is not _MISSING:
            out[entry_id] = value
    return out


def commit(db, hashed_pass, path=DB_FILE, check=None):
    """Save ``db``, a copy of the vault that has been held in memory, without
    losing what another window saved in the meantime.

    Under the vault lock: if the file is still the one ``db`` was loaded
    from (same SHA-256), ``db`` is written as it is. If it changed, the file
    is decrypted and merged with this window's changes (``merge``), ``db``
    is updated in place to the merged result, and that is written. If the
    changed file does not open with this key, ``VaultChangedElsewhere`` is
    raised and nothing is written.

    If the file is gone although ``db`` was loaded from it, ``VaultGone``
    is raised and nothing is written.

    A plain dict (one that did not come from ``load``/``open_blob``) has no
    record of what it was loaded from and simply replaces (or creates) the
    file, as before. ``check(blob)`` may raise to veto the write. Returns a
    ``MergeReport``.
    """
    report = MergeReport()
    with locked(path):
        try:
            with open(path, "rb") as f:
                current = f.read()
        except FileNotFoundError:
            current = None
        digest = getattr(db, "_digest", None)
        if current is None and digest is not None:
            # It was there when db was loaded. Writing db would bring back a
            # vault that was deliberately destroyed (self-destruct).
            raise VaultGone()
        if current is not None and digest is not None and _digest_of(current) != digest:
            try:
                disk = json.loads(decrypt_bytes(current, hashed_pass).decode("utf-8"))
                if not isinstance(disk, dict):
                    raise ValueError("vault is not a dict")
            except Exception:
                raise VaultChangedElsewhere() from None
            merged = merge(db._base or {}, db, disk, hashed_pass, report)
            report.merged = True
            db.clear()
            db.update(merged)
        blob = encrypt_bytes(json.dumps(db).encode("utf-8"), hashed_pass)
        if check is not None:
            check(blob)
        write_bytes_atomic(path, blob)
        _mark_synced(db, blob)
    return report


# --- field encoding

def enc(value, key):
    """Encrypt one field the way desktop does: base64(encrypt_data(utf-8))."""
    return base64.b64encode(encrypt_bytes(str(value).encode("utf-8"), key)).decode("utf-8")


def dec(entry, field, key):
    """Mirror of desktop ``decode_and_decrypt``; ``N/A`` when absent."""
    val = entry.get(field, NA)
    if val == NA:
        return NA
    if isinstance(val, str):
        try:
            val = base64.b64decode(val)
        except Exception:
            val = val.encode()
    return decrypt_bytes(val, key).decode("utf-8")


def dec_tag(tag, key):
    """Mirror of desktop ``decode_and_decrypt_tag``."""
    if tag == NA:
        return NA
    if isinstance(tag, str):
        try:
            tag = base64.b64decode(tag)
        except Exception:
            tag = tag.encode()
    return decrypt_bytes(tag, key).decode("utf-8")


def new_id():
    return str(uuid.uuid4())


# --- entry kinds (same tests desktop uses)

def is_profile(entry):
    return isinstance(entry, dict) and "domain" in entry and "password" in entry


def is_note(entry):
    return (isinstance(entry, dict) and "title" in entry and "content" in entry
            and "password" not in entry)


# --- profiles

def make_profile(domain, username, email, password, key, favorite=False):
    return {
        "domain": enc(domain, key),
        "email": enc(email or NA, key),
        "username": enc(username or NA, key),
        "password": enc(password, key),
        "favorite": bool(favorite),
    }


def read_profile(entry, key):
    return {
        "domain": dec(entry, "domain", key),
        "username": dec(entry, "username", key),
        "email": dec(entry, "email", key),
        "password": dec(entry, "password", key),
        "favorite": bool(entry.get("favorite", False)),
    }


def update_profile(entry, key, domain=None, username=None, email=None,
                   password=None, favorite=None):
    """Copy of ``entry`` with only the given fields replaced (None = keep);
    fields this module does not know about are carried over."""
    out = dict(entry)
    for name, value in (("domain", domain), ("username", username),
                        ("email", email), ("password", password)):
        if value is not None:
            out[name] = enc(value, key)
    if favorite is not None:
        out["favorite"] = bool(favorite)
    return out


# --- notes

def encode_tags(tags, key, private=False):
    if private:
        tags = [PRIVATE_TAG]
    else:
        tags = [t.strip() for t in (tags or []) if t and t.strip()] or [NA]
    return [enc(t, key) for t in tags]


def make_note(title, content, key, tags=None, favorite=False, private=False):
    return {
        "title": enc(title, key),
        "content": enc(content, key),
        "tags": encode_tags(tags, key, private),
        "favorite": bool(favorite),
        "private": bool(private),
    }


def read_note(entry, key):
    return {
        "title": dec(entry, "title", key),
        "content": dec(entry, "content", key),
        "tags": [dec_tag(t, key) for t in entry.get("tags", [])],
        "favorite": bool(entry.get("favorite", False)),
        "private": bool(entry.get("private", False)),
    }


def update_note(entry, key, title=None, content=None, tags=None,
                favorite=None, private=None):
    """Copy of ``entry`` with only the given fields replaced (None = keep)."""
    out = dict(entry)
    was_private = bool(out.get("private", False))
    if title is not None:
        out["title"] = enc(title, key)
    if content is not None:
        out["content"] = enc(content, key)
    if favorite is not None:
        out["favorite"] = bool(favorite)
    if private is not None:
        out["private"] = bool(private)
    is_private = bool(out.get("private", False))
    if tags is not None or is_private != was_private:
        # re-encode only when asked to, or when privacy changed (PRIVATE tag)
        out["tags"] = encode_tags(tags, key, is_private)
    return out
