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
  passwords, the vault files are overwritten and deleted, and BUNKER cannot
  recover them. (On SSDs and copy-on-write file systems old blocks may
  survive; see the threat model.)
- **Emoji-free output option.** `BUNKER_NO_EMOJI=1` removes emoji, which
  screen readers otherwise read aloud by name. BUNKER also no longer
  crashes when the terminal cannot display a character (for example emoji
  on a legacy Windows code page); it shows a replacement instead.
- **Configurable clipboard timeout.** `BUNKER_CLIPBOARD_SECONDS` (5-300,
  default 30) sets how long copied secrets stay on the clipboard.
- **Plain output option.** Set `NO_COLOR=1` to run without colours
  ([NO_COLOR](https://no-color.org) convention), useful with screen readers
  and when logging.
- **Optional public-IP display** (off by default) and a network information
  screen. BUNKER makes no network connection unless you ask it to show your
  public IP in one of these two places.
- **Setup guide.** Type `.g` at the first setup prompt. On the desktop it
  opens the setup guide; on a phone or tablet it prints a short one.

## Security fixes in this release

- **Exit no longer deletes your vault.** The cleanup that runs on timeout,
  Ctrl+C, errors and normal exit was deleting `Bunker.mmf` and `bunker.salt`.
  Only real temporary files are removed now. A regression test covers this.
- **Copied secrets are cleared from the clipboard.** Every password or note
  you copy is cleared after 30 seconds and again when BUNKER exits, including
  timeout, Ctrl+C and closing the terminal window (on macOS and Linux). If you have copied something else in the meantime,
  BUNKER leaves it alone. Before this fix, most desktop copy actions never
  cleared the clipboard, and the mobile one cleared it after half a second,
  too fast to paste.
- **Secrets are shown only when you ask.** Passwords and note contents are
  printed only after you choose to view them, all through one display function.
  Nothing writes them to a log file.
- **Generated passwords and passphrases are copied, not printed.** The
  password generator and the encrypted export's generated passphrase used to
  appear on screen straight away. They are now copied to the clipboard (and
  cleared like any other copy) and shown masked; type `v` at the prompt to
  see one on screen. If the clipboard is unavailable, BUNKER says that
  nothing was copied before you decide, and an export passphrase is then
  always shown, because there is no other way to give it to you.
- **A password you view is no longer filtered.** With `BUNKER_NO_EMOJI`
  set, emoji and symbol characters inside a viewed password or note were
  dropped from the display. Only BUNKER's own text is filtered now. (A
  terminal that cannot encode a character still shows `?` for it.)
- **The KDE Klipper clipboard fallback is not used.** That tool receives the
  copied text as a command-line argument, which other users on the same
  computer can read. BUNKER treats it as "no clipboard"; see Known
  limitations.
- **The System info screen asks before going online.** It used to look up
  your public IP from three web services every time you opened it, even if
  you declined to see network details. It now does so only after you answer
  yes to "Look up your public IP online?"; the local IP is read from your
  network interfaces without any request.
- **Turning the IP display off stops the lookups.** With the public IP
  display on, BUNKER checks connectivity and asks api64.ipify.org for your
  address every 30 seconds. Turning it off used to change only what was
  shown: the lookups went on until you closed BUNKER, and each time you
  turned the display back on another set started beside the old one. Off
  now ends them. A lookup already under way (about 15 seconds at most) is
  allowed to finish and its answer is thrown away.
- **Setup warns you about self-destruct.** Until now a new user first
  learned that wrong master passwords delete the vault at the login screen,
  after the vault existed. Setup now says it before it asks for a password
  ("After 3 wrong master passwords in a row, this vault is permanently
  deleted. Keep an encrypted export as a backup.") and waits for Enter;
  `.c` cancels. The number in that sentence and in the guides comes from
  the vault's attempt limit.
- **Imports check the file first.** Importing notes while the vault was
  not loaded used to replace the whole vault with just the imported notes;
  it now refuses. Every export file is checked before anything is saved:
  damaged, oversized or wrong-format files are refused with a plain reason,
  and entries with missing or wrong-typed fields are skipped and listed.
  If saving fails, nothing changes. A timeout during an import now logs you
  out instead of looping.
- **Re-importing doesn't create duplicates.** Entries already in your vault
  are skipped, and nothing is ever overwritten. A profile with the same site
  and login but a different password is added next to the old one, and the
  import tells you so.
- **The import preview shows hidden terminal codes.** Escape sequences in
  an export file are shown as visible codes in the import preview instead of
  being sent to your terminal, and the import tells you which entries have
  them. (The other screens do not escape them yet.)
- **Error messages no longer include exception details.** Errors now name
  the type of problem (plus the system reason for file errors) and leave out
  the raw exception text, which could include decrypted data.
- **New vaults can be opened.** Since the desktop/mobile split, setup did not
  write `bunker.cfg` and used a different key derivation than login, so a
  newly created vault could not be opened (and the resulting error deleted
  it). Setup now creates everything login needs.
- **Only the failed-login limit deletes the vault.** Errors, crashes, Ctrl+C,
  Ctrl+D and timeouts used to trigger self-destruct in several places; they
  now close BUNKER and leave your files untouched.
- **Damaged files are not wrong passwords.** A damaged or mismatched
  `bunker.cfg`/`bunker.salt` used to make even the correct password count
  as a failed attempt, so three correct logins could destroy the vault. A
  new integrity record (`bunker.chk`) lets BUNKER tell the two apart; only
  wrong passwords on verified files count. Real-crypto tests cover this.
- **Changing the master password no longer makes every entry unreadable.**
  Only the outer file used to be re-encrypted; every password and note
  stayed under the old key. All fields are now re-encrypted, and the files
  are swapped together with the old ones kept until everything succeeded.
- **Setup never overwrites an existing vault.** It used to start whenever
  `Bunker.mmf` could not be opened (e.g. locked by another program) and
  replaced the salt before its last question.
- **Mobile login checks passwords like desktop** and shares the same
  attempt counter and limit: the same "LAST ATTEMPT" confirmation, and
  the same self-destruct after 3 wrong passwords on verified files.
  Restarting or switching interface gives no extra attempts.
- **A vault without an integrity record** gets one only after a login that
  opens the database itself, not just `bunker.cfg`, so files from different
  backups are never recorded as one set.
- **Safer file writes.** The salt, config, settings and key files are
  written atomically and owner-only, so a crash mid-write can't leave a
  truncated file that would lock you out. (Atomic writes for the vault
  database itself are in a follow-up change.)
- **Export files are readable only by you** (permissions 0600 on macOS and
  Linux), for both encrypted and plain-text exports. The file is written in
  full and then moved into place, so a failed export leaves an existing file
  untouched, and an export never writes through a symlink.
- **Runs on Python 3.10 and newer.** A Python 3.12-only construct stopped
  BUNKER from starting on 3.11 and older.
- **Fixed in-app links.** The User Guide's support pages pointed to
  placeholder and dead addresses.
- **Leftover debug output removed.**
- **Unused dependencies removed.** `keyboard` (a global keyboard hook) and
  `inputimeout` were imported but never used.
- **Vault files are git-ignored**, so a local vault, salt, backup, settings
  file or integrity record can't be committed by accident. A copy of
  `config.cfg` that had been committed made the mobile interface stop at
  "UI config file missing or corrupted" on a fresh download, before it could
  offer first-run setup; the file is no longer part of the repository.
  BUNKER creates it on first run. `config.example` documents what it holds
  and its defaults.

## Requirements

Python 3 and the packages in `requirements.txt`:

```bash
pip install -r requirements.txt
```

The unused `keyboard` and `inputimeout` packages are no longer needed. On
Linux, `keyboard` could require root.

## Tests

This release adds the project's first automated tests (standard-library
`unittest`, no extra packages). From the repository folder:

```bash
python3 -m unittest discover -s tests -t .
```

The tests cover the first-run flow end to end with real encryption, the
self-destruct policy, clipboard clearing (timer, outages, terminal close),
generated secrets being copied instead of printed,
safe error text, atomic and owner-only file writes, plain output, that the
System info screen stays offline unless you ask for your public IP, that a
new vault is created and opened with every network call blocked, that
turning the IP display off ends the lookups, the setup warning, and a
fuzz test of damaged vault files. CI runs them on Linux, macOS and Windows
with Python 3.10-3.13, plus a dependency audit. Most interactive menus are
not covered by automated tests.

See `docs/THREAT_MODEL.md` for what BUNKER protects against and where that
protection stops.

## Known limitations

- **Plain-text export is available.** If you choose it, the exported JSON
  holds your passwords or notes unencrypted. Choose encrypted export unless
  you have a specific reason not to.
- **The failed-login limit deletes the vault on purpose.** BUNKER cannot
  recover it. Keep an encrypted export as a backup.
- **The mobile interface can view but not yet save changes** in this
  release; that is fixed in a follow-up change.
- **Deleting `config.cfg` resets the failed-attempt counter.** Someone who
  can change files in the BUNKER folder can do that (they could also just
  delete the vault).
- **The limit protects the app, not a copy of your files.** Someone who
  copies the vault files can guess passwords offline; a long master password
  is the real protection.
- **No demo vault ships with this release.** On first run, BUNKER walks you
  through creating your own vault.
- **Killing BUNKER with `kill -9`** (or a crash of Python itself) skips all
  cleanup, so a password copied less than 30 seconds earlier stays on the
  clipboard.
- **Copying to the clipboard on Linux needs a clipboard tool.** Install
  `xclip`, `xsel` or `wl-clipboard` (Wayland). Without one, BUNKER says
  "Could not access the clipboard" and nothing is copied or shown; you can
  still view a password on screen when you choose to.
  On KDE, the built-in Klipper fallback is refused on purpose, so install
  one of those tools there too.
- **A generated export passphrase is on the clipboard for 30 seconds.**
  Paste it somewhere safe, or type `v` to see it, before you move on. If you
  lose it, that export cannot be opened; export again to get a new one.
- **Terminal width decides the suggested interface.** BUNKER guesses
  mobile for terminals up to 80 columns and tablet up to 120, and asks you
  to confirm. Answer **n** and choose Desktop/Laptop if the guess is wrong.
- **Security reports:** email support@zeromarks.net instead of opening a
  public issue.
- BUNKER is provided as-is, for educational purposes, with no warranty.
  See `Read Me/LICENSE.txt`.
