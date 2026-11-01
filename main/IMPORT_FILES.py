"""Reading, checking and de-duplicating BUNKER export files before import.

Everything here is pure: no prompts, no printing, no vault writes. The
import screens in DESKTOP.py call these helpers, so a damaged or hostile
file is rejected the same way every time, and the rules can be tested
without a terminal.

Rules:
- A file is read only if it is at most MAX_IMPORT_BYTES, is UTF-8 and is a
  JSON object. Anything else is refused with ImportRejected, whose message
  is safe to show (it never quotes the file's contents).
- Each entry is checked field by field. An entry with a missing or
  wrong-typed field is skipped and counted, never half-imported.
- An entry that is exactly the same as one already in the vault, or as an
  earlier entry in the same file, is skipped. Nothing in the vault is ever
  overwritten. A profile with the same site and login as an existing one
  but a different password is imported alongside it and reported, because
  the export has no timestamps to say which one is newer.
- Text from the file is shown through printable(), so terminal control
  sequences inside an imported entry are displayed, not executed.
"""
import base64
import binascii
import json
import os
import unicodedata

MAX_IMPORT_BYTES = 32 * 1024 * 1024
WATERMARK = "### Property of ZEROMARKSLLC - EXPORTED with BUNKER ###"

# Bidirectional formatting characters can make text display in a different
# order than it is stored (Trojan Source, CVE-2021-42574).
_BIDI_CONTROLS = {chr(c) for c in (*range(0x202A, 0x202F), *range(0x2066, 0x206A), 0x200E, 0x200F, 0x061C)}


class ImportRejected(Exception):
    """The file can't be imported. str(exc) is safe to show the user."""


# ---------------------------------------------------------------- reading
def _parse_json(raw):
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise ImportRejected("The file is not UTF-8 text.") from None
    try:
        data = json.loads(text)
    except RecursionError:
        raise ImportRejected("The file is nested too deeply to be a BUNKER export.") from None
    except ValueError:
        raise ImportRejected("The file is not valid JSON.") from None
    if not isinstance(data, dict):
        raise ImportRejected("The file is not a BUNKER export (expected a JSON object).")
    return data


def read_import_file(path, limit=MAX_IMPORT_BYTES):
    """Read and parse an export file, refusing anything that isn't a JSON object."""
    try:
        if os.path.getsize(path) > limit:
            raise ImportRejected(f"The file is larger than {limit // (1024 * 1024)} MiB, too large for a BUNKER export.")
        with open(path, "rb") as f:
            raw = f.read(limit + 1)
    except OSError as e:
        raise ImportRejected(f"The file could not be read ({type(e).__name__}).") from None
    if len(raw) > limit:  # grew while we were reading
        raise ImportRejected(f"The file is larger than {limit // (1024 * 1024)} MiB, too large for a BUNKER export.")
    return _parse_json(raw)


def is_encrypted_export(data):
    return (isinstance(data, dict) and data.get("watermark") == WATERMARK
            and all(k in data for k in ("salt", "verifier", "data")))


def _b64(value, what):
    if not isinstance(value, str):
        raise ImportRejected(f"The encrypted file is damaged ({what} is not text).")
    try:
        out = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError):
        raise ImportRejected(f"The encrypted file is damaged ({what} is not valid base64).") from None
    if not out:
        raise ImportRejected(f"The encrypted file is damaged ({what} is empty).")
    return out


def unwrap_encrypted(data):
    """Return (salt, verifier, ciphertext) from an encrypted export."""
    return _b64(data["salt"], "salt"), _b64(data["verifier"], "verifier"), _b64(data["data"], "data")


def parse_payload(decrypted_bytes):
    """Parse the decrypted body of an encrypted export."""
    return _parse_json(decrypted_bytes)


# ---------------------------------------------------------------- checking
def _section(structure, name):
    if not isinstance(structure, dict) or name not in structure:
        raise ImportRejected(f"The file has no '{name}' section. Is it a {name} export?")
    section = structure[name]
    if not isinstance(section, dict):
        raise ImportRejected(f"The '{name}' section is damaged (expected a JSON object).")
    return section


def _flag(entry, name):
    value = entry.get(name, False)
    if not isinstance(value, bool):
        raise ValueError(f"'{name}' must be true or false")
    return value


def _text(entry, name, required=True, nonblank=False):
    if name not in entry or entry[name] is None:
        if required:
            raise ValueError(f"'{name}' is missing")
        return "N/A"
    value = entry[name]
    if not isinstance(value, str):
        raise ValueError(f"'{name}' must be text")
    if nonblank and not value.strip():
        raise ValueError(f"'{name}' is empty")
    if not required and not value.strip():
        return "N/A"
    return value


def _clean_tags(tags, private):
    if private:
        return ["PRIVATE"]
    cleaned = [t.strip() for t in tags if t.strip()]
    return cleaned or ["N/A"]


def validate_notes(structure):
    """Return (notes, problems). Each note is a normalised dict; each problem
    is (entry number, reason). Raises ImportRejected if there is no notes section."""
    notes, problems = [], []
    for number, entry in enumerate(_section(structure, "notes").values(), start=1):
        try:
            if not isinstance(entry, dict):
                raise ValueError("not a note")
            title = _text(entry, "title")
            content = _text(entry, "content")
            private = _flag(entry, "private")
            favorite = _flag(entry, "favorite")
            tags = entry.get("tags", ["N/A"])
            if tags is None:
                tags = ["N/A"]
            if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
                raise ValueError("'tags' must be a list of text")
        except ValueError as e:
            problems.append((number, str(e)))
            continue
        notes.append({"title": title, "content": content, "private": private,
                      "favorite": favorite, "tags": _clean_tags(tags, private)})
    return notes, problems


def validate_profiles(structure):
    """Return (profiles, problems), like validate_notes."""
    profiles, problems = [], []
    for number, entry in enumerate(_section(structure, "profiles").values(), start=1):
        try:
            if not isinstance(entry, dict):
                raise ValueError("not a profile")
            profile = {
                "domain": _text(entry, "domain", nonblank=True),
                "password": _text(entry, "password", nonblank=True),
                "email": _text(entry, "email", required=False),
                "username": _text(entry, "username", required=False),
                "favorite": _flag(entry, "favorite"),
            }
        except ValueError as e:
            problems.append((number, str(e)))
            continue
        profiles.append(profile)
    return profiles, problems


# ---------------------------------------------------------------- duplicates
def note_key(note):
    return (note["title"], note["content"], bool(note["private"]), tuple(sorted(note["tags"])))


def profile_key(profile):
    return (profile["domain"], profile["email"], profile["username"], profile["password"])


def login_key(profile):
    """Same site and same login, ignoring case and the password."""
    return (profile["domain"].strip().casefold(), profile["email"].strip().casefold(),
            profile["username"].strip().casefold())


def is_note(entry):
    return isinstance(entry, dict) and "title" in entry and "password" not in entry


def is_profile(entry):
    return isinstance(entry, dict) and "password" in entry and "domain" in entry


def existing_notes(db, decrypt_field, decrypt_tag):
    """Decrypt the notes already in the vault into normalised dicts.
    Entries that can't be decrypted are left out (they can't be compared)."""
    out = []
    for entry in db.values():
        if not is_note(entry):
            continue
        try:
            private = bool(entry.get("private", False))
            tags = [decrypt_tag(t) for t in entry.get("tags", []) or []]
            out.append({"title": decrypt_field("title", entry), "content": decrypt_field("content", entry),
                        "private": private, "tags": _clean_tags(tags, private)})
        except Exception:
            continue
    return out


def existing_profiles(db, decrypt_field):
    out = []
    for entry in db.values():
        if not is_profile(entry):
            continue
        try:
            fields = {f: decrypt_field(f, entry) for f in ("domain", "password", "email", "username")}
        except Exception:
            continue
        for f in ("email", "username"):
            if not fields[f].strip():
                fields[f] = "N/A"
        out.append(fields)
    return out


def plan_notes(candidates, existing):
    """Return (new notes, number skipped as exact duplicates)."""
    seen = {note_key(n) for n in existing}
    new, duplicates = [], 0
    for note in candidates:
        key = note_key(note)
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        new.append(note)
    return new, duplicates


def plan_profiles(candidates, existing):
    """Return (new profiles, exact duplicates skipped, how many of the new
    ones share a site and login with an existing profile)."""
    seen = {profile_key(p) for p in existing}
    logins = {login_key(p) for p in existing}
    new, duplicates, same_login = [], 0, 0
    for profile in candidates:
        key = profile_key(profile)
        if key in seen:
            duplicates += 1
            continue
        if login_key(profile) in logins:
            same_login += 1
        seen.add(key)
        logins.add(login_key(profile))
        new.append(profile)
    return new, duplicates, same_login


# ---------------------------------------------------------------- display
def has_controls(text):
    return any(_is_control(ch) for ch in text)


def _is_control(ch):
    return ch in _BIDI_CONTROLS or unicodedata.category(ch) == "Cc"


def printable(text, limit=None):
    """Make untrusted text safe to print on one line.

    Control characters (C0, DEL, C1, including ESC and CSI) and bidirectional
    overrides are shown as visible escapes such as \\x1b instead of being sent
    to the terminal, so they can't move the cursor, hide text, or set the
    clipboard. Newlines and tabs become spaces.
    """
    out = []
    for ch in str(text):
        if ch in "\n\t\r":
            out.append(" ")
        elif _is_control(ch):
            code = ord(ch)
            out.append(f"\\x{code:02x}" if code < 0x100 else f"\\u{code:04x}")
        else:
            out.append(ch)
    result = "".join(out)
    if limit is not None and len(result) > limit:
        result = result[:limit] + "..."
    return result
