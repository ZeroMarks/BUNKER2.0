"""
VAULT_FILES - consistency of the files that unlock the vault.

AES-GCM reports a wrong password and a damaged file the same way (InvalidTag),
so on its own BUNKER cannot tell "wrong password" from "bunker.cfg was cut
short". Counting the second as a failed login would let ordinary file damage
destroy a vault the user can still open. This module keeps a small plaintext
record, ``bunker.chk``, with SHA-256 hashes of ``bunker.salt`` and
``bunker.cfg``. It is rewritten whenever either changes.

* ``integrity_status()`` -> "ok", "mismatch", "unknown" (no record yet: a vault
  from before this change), "interrupted" (a master password change did not
  finish: the record says so, or ``*.prev`` copies are still present) or
  "missing" (salt or config absent).
* Login counts a failed attempt only when the status is "ok" or "unknown",
  and self-destruct may only run when it is "ok".
* While a change is "interrupted" the user may not know which password is
  current, so nothing is counted or destroyed. A correct password that also
  opens the database finishes the change (``finish_interrupted_change``).

The record protects against accidental damage and out-of-step files, not
against someone who can write to the folder; they could delete the vault
anyway (see docs/THREAT_MODEL.md).

It also guards setup: a new vault is only created where none exists, or
where an earlier setup was interrupted (``SETUP_MARKER`` still present).
"""

import hashlib
import json
import os

from main.SECURE_IO import write_private_bytes

SALT_FILE = "bunker.salt"
CONFIG_FILE = "bunker.cfg"
DB_FILE = "Bunker.mmf"
CHECK_FILE = "bunker.chk"
SETUP_MARKER = ".bunker-setup-in-progress"
_VERSION = 1


VAULT_FILES_SET = (DB_FILE, CONFIG_FILE, SALT_FILE)
BACKUP_SUFFIX = ".prev"
_STATE_CHANGING = "changing"


def recovery_copies():
    """The ``*.prev`` copies of the vault files that exist right now. They
    are only present while a master password change is running, or after
    one was interrupted."""
    return [p + BACKUP_SUFFIX for p in VAULT_FILES_SET
            if os.path.exists(p + BACKUP_SUFFIX)]


def _sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def record_integrity():
    """Write bunker.chk for the current salt and config. Call after every
    change to either file."""
    record = {
        "version": _VERSION,
        "salt_sha256": _sha256_file(SALT_FILE),
        "config_sha256": _sha256_file(CONFIG_FILE),
    }
    write_private_bytes(CHECK_FILE, json.dumps(record, sort_keys=True).encode("utf-8"))


def _begin_change():
    """Mark the files as being replaced, before the first one is written.
    From here until the final record, login treats the vault as
    "interrupted": nothing is counted and nothing is destroyed."""
    record = {"version": _VERSION, "state": _STATE_CHANGING}
    write_private_bytes(CHECK_FILE, json.dumps(record, sort_keys=True).encode("utf-8"))


def integrity_status():
    if not (os.path.exists(SALT_FILE) and os.path.exists(CONFIG_FILE)):
        return "missing"
    record = None
    if os.path.exists(CHECK_FILE):
        try:
            with open(CHECK_FILE, "rb") as f:
                record = json.loads(f.read().decode("utf-8"))
            if not isinstance(record, dict):
                raise ValueError("record is not an object")
        except Exception:
            return "mismatch"
    # A password change that did not finish: the record was invalidated
    # before the first write, or the recovery copies were never removed.
    # The salt and config may well match an old record here while the
    # database is already the new one, so this check comes first.
    if (record is not None and record.get("state") == _STATE_CHANGING) or recovery_copies():
        return "interrupted"
    if record is None:
        return "unknown"
    try:
        ok = (record.get("salt_sha256") == _sha256_file(SALT_FILE)
              and record.get("config_sha256") == _sha256_file(CONFIG_FILE))
    except Exception:
        return "mismatch"
    return "ok" if ok else "mismatch"


def destroy_allowed():
    """Self-destruct may only run on files known to be one consistent set:
    the record matches and no password change is part-way through."""
    return integrity_status() == "ok"


def finish_interrupted_change():
    """Call after a login whose key opened both bunker.cfg and Bunker.mmf
    while the status was "interrupted". The current files are then a
    complete, working set: record them and drop the recovery copies."""
    record_integrity()
    for p in recovery_copies():
        try:
            os.remove(p)
        except OSError:
            pass


def write_config(encrypted_config):
    """Atomically replace bunker.cfg and update the integrity record."""
    write_private_bytes(CONFIG_FILE, encrypted_config)
    record_integrity()


# --- setup guard -----------------------------------------------------------

def setup_allowed():
    """True if creating a new vault here cannot overwrite an existing one.

    Allowed when no vault file exists, or when an earlier setup was
    interrupted (the marker is still present and Bunker.mmf was never
    written). config.cfg alone does not count: it only holds UI settings
    and ships with the repository.
    """
    if os.path.exists(DB_FILE):
        return False
    if os.path.exists(SETUP_MARKER):
        return True
    return not any(os.path.exists(p) for p in (SALT_FILE, CONFIG_FILE, CHECK_FILE))


def begin_setup():
    write_private_bytes(SETUP_MARKER, b"setup started\n")


def finish_setup():
    try:
        os.remove(SETUP_MARKER)
    except FileNotFoundError:
        pass


def write_new_vault(salt, encrypted_config, encrypted_db, after_salt=None):
    """Create a vault's files. The database is written last and the marker
    removed only after everything is on disk, so an interrupted setup is
    recognised and can safely be redone. ``after_salt`` runs once the salt
    exists (the UI settings key depends on it)."""
    if not setup_allowed():
        raise FileExistsError("a vault already exists here")
    begin_setup()
    write_private_bytes(SALT_FILE, salt)
    if after_salt is not None:
        after_salt()
    write_private_bytes(CONFIG_FILE, encrypted_config)
    record_integrity()
    write_private_bytes(DB_FILE, encrypted_db)
    finish_setup()


# --- what the login screen says about attempts ------------------------------

def attempts_notice(attempts, max_attempts, files_state, destroys):
    """Lines to show above the password prompt, shared by both interfaces so
    they count and warn the same way. ``destroys`` is True for the desktop
    interface, the only one that self-destructs. Returns a list of
    ``(kind, text)`` with kind "info", "warn" or "alert"."""
    if files_state == "interrupted":
        return [("warn", "A master password change did not finish. Try your new "
                         "password, then your old one. Wrong passwords are not counted "
                         "and nothing is deleted. Your previous files are kept as "
                         "*.prev (see docs/RECOVERY.md).")]
    lines = [("info", f"Failed attempts: {attempts} of {max_attempts}")]
    if files_state == "unknown":
        lines.append(("info", "Self-destruct is off until the next successful login "
                              "(this vault has no integrity record yet)."))
        return lines
    if files_state != "ok" or attempts < max_attempts - 1:
        return lines
    if destroys:
        lines.append(("alert", "LAST ATTEMPT: one more wrong password permanently destroys "
                               "this vault. If you are not sure of the password, exit now (e)."))
    elif attempts >= max_attempts:
        lines.append(("alert", "The failed-attempt limit is reached. This interface never "
                               "deletes the vault, but on the desktop interface the next "
                               "wrong password destroys it."))
    else:
        lines.append(("alert", "LAST ATTEMPT: after one more wrong password, the desktop "
                               "interface destroys this vault on the next wrong password. "
                               "If you are not sure of the password, exit now (e)."))
    return lines


# --- replacing all three files (master password change) --------------------

def replace_vault(salt, encrypted_config, encrypted_db, after_salt=None):
    """Replace salt, config and database together.

    The current files are first copied to ``*.prev`` (owner-only) and the
    integrity record is set to "changing" before anything is replaced. The
    new database, config and salt are then swapped in and the final record
    written; only then are the copies removed. If anything fails, the old
    files are restored. If the process dies part-way (terminal closed,
    shutdown, power loss), the record still says "changing" and the copies
    remain, so login reports an interrupted change: no attempt is counted,
    nothing is destroyed, and the ``.prev`` copies are kept for recovery
    (docs/RECOVERY.md).
    """
    paths = VAULT_FILES_SET
    for p in paths:
        with open(p, "rb") as f:
            write_private_bytes(p + BACKUP_SUFFIX, f.read())
    try:
        _begin_change()
        write_private_bytes(DB_FILE, encrypted_db)
        write_private_bytes(CONFIG_FILE, encrypted_config)
        write_private_bytes(SALT_FILE, salt)
        if after_salt is not None:
            after_salt()
        record_integrity()
    except BaseException:
        # Put the old files back, then drop the copies.
        for p in paths:
            with open(p + BACKUP_SUFFIX, "rb") as f:
                write_private_bytes(p, f.read())
        if after_salt is not None:
            after_salt()  # settings key depends on the (restored) salt
        record_integrity()
        for p in paths:
            try:
                os.remove(p + BACKUP_SUFFIX)
            except OSError:
                pass
        raise
    for p in paths:
        try:
            os.remove(p + BACKUP_SUFFIX)
        except OSError:
            pass


# --- re-encrypting every field for a new master password -------------------

ENCRYPTED_FIELDS = ("domain", "email", "username", "password", "title", "content")
NA = "N/A"


def _rekey_value(value, old_key, new_key, vault):
    import base64
    if value == NA:
        return value
    raw = base64.b64decode(value) if isinstance(value, str) else value
    plain = vault.decrypt_data(raw, old_key)   # raises on any problem
    return base64.b64encode(vault.encrypt_data(plain, new_key)).decode("utf-8")


def rekey_database(db, old_key, new_key, vault):
    """Return a copy of ``db`` with every encrypted field re-encrypted under
    ``new_key``. Fields are encrypted individually, so changing the master
    password must re-encrypt each one; re-encrypting only the outer file
    leaves every entry unreadable. Raises if any field cannot be decrypted,
    so a partial result is never saved."""
    out = {}
    for entry_id, entry in db.items():
        if not isinstance(entry, dict):
            raise ValueError("unexpected vault entry")
        new = dict(entry)
        for field in ENCRYPTED_FIELDS:
            if field in new:
                new[field] = _rekey_value(new[field], old_key, new_key, vault)
        if isinstance(new.get("tags"), list):
            new["tags"] = [_rekey_value(t, old_key, new_key, vault) for t in new["tags"]]
        out[entry_id] = new
    return out


# --- shared password check -------------------------------------------------

def try_password(password, vault):
    """Check ``password`` against the vault files, following the same rules
    as the desktop login. Returns ``(status, key)`` where status is:

    * "ok": correct password (key returned)
    * "wrong": wrong password - the only result that may count as an attempt
    * "interrupted": a master password change did not finish and this
      password did not open bunker.cfg; never count it (the user may be
      trying the other of their two passwords)
    * "missing" / "mismatch" / "inconsistent": files absent, damaged or out of
      step; never count these as attempts

    A correct password during an interrupted change returns "ok". The caller
    then calls finish_interrupted_change() once Bunker.mmf has opened too.
    """
    import base64
    from cryptography.exceptions import InvalidTag
    status = integrity_status()
    if status in ("missing", "mismatch"):
        return status, None
    # "interrupted": the password is checked, but a wrong one is reported as
    # "interrupted" so callers never count it. A right one is returned as
    # "ok"; the caller finishes the change once the database opens too.
    with open(SALT_FILE, "rb") as f:
        salt = f.read()
    with open(CONFIG_FILE, "rb") as f:
        encrypted_config = f.read()
    key = vault.derive_key_hybrid(password, salt, password)
    try:
        config = json.loads(vault.decrypt_data(encrypted_config, key).decode())
    except InvalidTag:
        return ("interrupted" if status == "interrupted" else "wrong"), None
    if not vault.verify_password_enhanced(password, base64.b64decode(config["salt"]),
                                          base64.b64decode(config["verifier"])):
        return "inconsistent", None
    if status == "unknown":
        record_integrity()
    return "ok", key
