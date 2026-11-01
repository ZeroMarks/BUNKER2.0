"""
VAULT_FILES - consistency of the files that unlock the vault.

AES-GCM reports a wrong password and a damaged file the same way (InvalidTag),
so on its own BUNKER cannot tell "wrong password" from "bunker.cfg was cut
short". Counting the second as a failed login would let ordinary file damage
destroy a vault the user can still open. This module keeps a small plaintext
record, ``bunker.chk``, with SHA-256 hashes of ``bunker.salt`` and
``bunker.cfg``. It is rewritten whenever either changes.

* ``integrity_status()`` -> "ok", "mismatch", "unknown" (no record yet: a vault
  from before this change) or "missing" (salt or config absent).
* Login counts a failed attempt only when the status is "ok" or "unknown",
  and self-destruct may only run when it is "ok".

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


def integrity_status():
    if not (os.path.exists(SALT_FILE) and os.path.exists(CONFIG_FILE)):
        return "missing"
    if not os.path.exists(CHECK_FILE):
        return "unknown"
    try:
        with open(CHECK_FILE, "rb") as f:
            record = json.loads(f.read().decode("utf-8"))
        ok = (record.get("salt_sha256") == _sha256_file(SALT_FILE)
              and record.get("config_sha256") == _sha256_file(CONFIG_FILE))
    except Exception:
        return "mismatch"
    return "ok" if ok else "mismatch"


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


# --- replacing all three files (master password change) --------------------

BACKUP_SUFFIX = ".prev"


def replace_vault(salt, encrypted_config, encrypted_db, after_salt=None):
    """Replace salt, config and database together.

    The current files are first copied to ``*.prev`` (owner-only). The new
    database, config and salt are then swapped in and the integrity record
    updated; only then are the copies removed. If anything fails, the old
    files are restored. If the process dies part-way, the ``.prev`` copies
    remain for manual recovery and the integrity record no longer matches,
    so login refuses without counting attempts and nothing is destroyed.
    """
    paths = (DB_FILE, CONFIG_FILE, SALT_FILE)
    for p in paths:
        with open(p, "rb") as f:
            write_private_bytes(p + BACKUP_SUFFIX, f.read())
    try:
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
    * "missing" / "mismatch" / "inconsistent": files absent, damaged or out of
      step; never count these as attempts
    """
    import base64
    from cryptography.exceptions import InvalidTag
    status = integrity_status()
    if status in ("missing", "mismatch"):
        return status, None
    with open(SALT_FILE, "rb") as f:
        salt = f.read()
    with open(CONFIG_FILE, "rb") as f:
        encrypted_config = f.read()
    key = vault.derive_key_hybrid(password, salt, password)
    try:
        config = json.loads(vault.decrypt_data(encrypted_config, key).decode())
    except InvalidTag:
        return "wrong", None
    if not vault.verify_password_enhanced(password, base64.b64decode(config["salt"]),
                                          base64.b64decode(config["verifier"])):
        return "inconsistent", None
    if status == "unknown":
        record_integrity()
    return "ok", key
