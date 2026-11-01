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

This module has no interactive code and never deletes anything. Entries it
does not understand are passed through untouched.
"""
import base64
import json
import os
import uuid

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


def load(hashed_pass, path=DB_FILE):
    """Decrypt and return the vault dict. Errors (missing file, wrong key,
    corrupt data) propagate; callers must not treat them as "empty vault"."""
    with open(path, "rb") as f:
        blob = f.read()
    db = json.loads(decrypt_bytes(blob, hashed_pass).decode("utf-8"))
    if not isinstance(db, dict):
        raise ValueError("vault is not a dict")
    return db


def save(db, hashed_pass, path=DB_FILE):
    """Encrypt ``db`` and write it atomically. Refuses anything that is not a
    flat dict of dicts, because desktop breaks on other shapes."""
    if not isinstance(db, dict) or not all(isinstance(v, dict) for v in db.values()):
        raise ValueError("vault must be a flat dict of entry dicts")
    write_bytes_atomic(path, encrypt_bytes(json.dumps(db).encode("utf-8"), hashed_pass))


LEGACY_EMPTY_KEYS = ("notes", "accounts", "profiles")


def modify(hashed_pass, mutate, path=DB_FILE):
    """Load the vault, let ``mutate(db)`` change it in place, save atomically.

    Reloading right before every change keeps edits made by another UI
    since this one started. Empty list values under the old mobile keys
    ("notes", "accounts", "profiles") are dropped first: they are the only
    non-dict values this project ever wrote, and desktop cannot read them.
    Any other non-dict value makes save() refuse, so nothing is overwritten.
    Returns whatever ``mutate`` returns.
    """
    db = load(hashed_pass, path)
    for k in LEGACY_EMPTY_KEYS:
        if db.get(k) == []:
            del db[k]
    result = mutate(db)
    save(db, hashed_pass, path)
    return result


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
