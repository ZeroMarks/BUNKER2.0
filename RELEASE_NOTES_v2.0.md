# BUNKER 2.0 — Release Notes

BUNKER is a free, source-available, offline password and notes manager that
runs in the terminal (Python 3). Your vault stays on your machine; BUNKER has
no account and no cloud sync.

These notes describe what the code in this release does. Where something is
a known limitation, it says so.

## What's in 2.0

- **Desktop and mobile interfaces.** On launch BUNKER guesses your device
  type, asks you to confirm it, and opens the desktop or the mobile-friendly
  interface.
- **Encrypted vault.** Passwords and notes are stored in `Bunker.mmf`,
  encrypted with AES-256-GCM. The key comes from your master password and a
  random 32-byte salt (`bunker.salt`) using Argon2id (time cost 3, 100 MiB
  memory, parallelism 8) followed by PBKDF2-HMAC-SHA3-256 (110,000
  iterations). The master password itself is not stored.
- **Password profiles and notes**: add, view, edit, delete, search, mark as
  favourites, tag notes and mark notes private (private notes are hidden in
  lists until you choose to view them).
- **Password generator** and a **password strength checker**.
- **Export and import** of profiles and notes as JSON, either encrypted with a
  passphrase (yours or a generated one) or as plain text.
- **Auto-logout** after a configurable period of inactivity.
- **Failed-login limit.** After the configured number of wrong master
  passwords, the vault files are overwritten and deleted. There is no recovery.
- **Optional public-IP display** and a network information screen.

## Security fixes in this release

- **Exit no longer deletes your vault.** The cleanup that runs on timeout,
  Ctrl+C, errors and normal exit was deleting `Bunker.mmf` and `bunker.salt`.
  Only real temporary files are removed now. A regression test covers this.
- **Copied secrets are cleared from the clipboard.** Every password or note
  you copy is cleared after 30 seconds and again when BUNKER exits, including
  timeout and Ctrl+C. If you have copied something else in the meantime,
  BUNKER leaves it alone. Before this fix, most desktop copy actions never
  cleared the clipboard, and the mobile one cleared it after half a second,
  too fast to paste.
- **Secrets are shown only when you ask.** Passwords and note contents are
  printed only after you choose to view them, all through one display function.
  Nothing writes them to a log file.
- **Error messages no longer include exception details.** Errors now name
  the type of problem (plus the system reason for file errors) and leave out
  the raw exception text, which could include decrypted data.
- **Leftover debug output removed.**
- **Vault files are git-ignored**, so a local vault, salt or backup can't be
  committed by accident.

## Requirements

Python 3 and these packages:

```bash
pip install inputimeout keyboard cryptography pyperclip psutil requests argon2-cffi
```

## Tests

This release adds the project's first automated tests (standard-library
`unittest`, no extra packages). From the repository folder:

```bash
python3 -m unittest discover -s tests -t .
```

The tests cover clipboard clearing, safe error text and the exit cleanup.
The interactive menus are not covered by automated tests.

## Known limitations

- **Plain-text export is available.** If you choose it, the exported JSON
  holds your passwords or notes unencrypted. Choose encrypted export unless
  you have a specific reason not to.
- **The failed-login limit and some error paths delete the vault on
  purpose.** Keep an encrypted export as a backup.
- **No demo vault ships with this release.** On first run, BUNKER walks you
  through creating your own vault.
- BUNKER is provided as-is, for educational purposes, with no warranty.
  See `Read Me/LICENSE.txt`.
