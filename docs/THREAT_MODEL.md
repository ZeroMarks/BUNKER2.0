# BUNKER 2.0 — Threat Model

This document states what BUNKER protects, against whom, how, and where the
protection stops. It describes the code as it is in this release; it is not a
promise of future features. Report security problems to
**support@zeromarks.net** (please don't open a public issue).

## 1. What BUNKER is

A single-user, offline password and notes manager that runs in a terminal.
There is no server, account or sync. All data lives in the folder BUNKER is
run from.

## 2. Assets

| Asset | Where it lives | Protection |
|---|---|---|
| Passwords, usernames, emails, notes | `Bunker.mmf` | AES-256-GCM, each field encrypted separately, the whole database encrypted again |
| Master password | Never stored | Only a key derived from it is kept in memory while the vault is open |
| Vault salt | `bunker.salt` (32 random bytes) | Not secret, but required; written atomically, mode 0600 |
| Password verifier and config | `bunker.cfg` | AES-256-GCM under the derived key |
| UI settings (timeout, attempt counter, IP display) | `config.cfg` | AES-256-GCM under a key derived from machine details (see §6) |
| Exports | user-chosen `.json` | Encrypted with a passphrase, or plain text if the user chooses; mode 0600 |

## 3. Key derivation

`key = PBKDF2-HMAC-SHA3-256(Argon2id(password, salt; t=3, m=100 MiB, p=8), salt, 110,000 iterations)`

For comparison, the [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
sets a minimum of Argon2id with m=19 MiB, t=2, p=1, and
[Bitwarden's default](https://bitwarden.com/help/kdf-algorithms/) is
m=32 MiB, t=6, p=4. BUNKER's memory cost is well above both. The PBKDF2 step
adds little on top of Argon2id but does no harm.

Every encryption uses a fresh random 96-bit nonce. A vault holds a few
thousand fields at most, far below the point where random nonces become a
concern for AES-GCM.

## 4. Adversaries and what BUNKER does about them

| # | Adversary | In scope? | What protects you |
|---|---|---|---|
| A1 | Someone who **copies your vault files** (stolen laptop, backup, cloud folder) | Yes | Encryption + Argon2id. They can guess passwords **offline at their own speed**; the failed-login limit does not apply to a copy. **Your master password's strength is the real defence.** |
| A2 | Someone **at your keyboard** while BUNKER is locked | Partly | Master password. After 3 wrong passwords (counted the same way in the desktop and mobile interfaces) the vault is overwritten and deleted. Someone who can also change files in the BUNKER folder can reset the counter by deleting `config.cfg` (see §6). |
| A3 | Someone at your keyboard **after you walk away unlocked** | Partly | Auto-logout (10–3600 s, or off). Passwords and notes are shown only when you ask; copied secrets leave the clipboard after 30 s and when BUNKER exits or the terminal closes. |
| A4 | Other **apps reading the clipboard** | Partly | Clipboard clearing (above). Clipboard managers and history tools can still keep a copy; see §6. |
| A5 | Other **local user accounts** on the same machine | Yes | Vault, salt, settings and export files are written owner-only (0600) on macOS/Linux. |
| A6 | **Shoulder surfing / screen recording** | Partly | Password input is hidden unless you choose to show it; secrets are revealed only on request. The password-strength checker shows what you type. |
| A7 | **Malware running as you**, or root/admin | No | It can read memory, log keystrokes and read your files. No local password manager can defend against this. |
| A8 | **Crashes, power loss, damaged files, bugs** | Yes | The vault database, salt, config, settings, key and export files are written atomically. `bunker.chk` records hashes of the salt and config, so damaged or mismatched files are reported instead of being counted as wrong passwords. Errors, Ctrl+C, EOF and timeouts never delete the vault; only 3 wrong passwords on verified files do. Real-crypto tests cover these cases. |

## 5. Design rules the code enforces

- **One exit point for secrets.** `main/SECURE_IO.py` is the only code that
  puts a secret on screen (`reveal_secret`) or the clipboard (`copy_secret`).
  Errors are shown with `safe_error`, which never includes exception text.
- **Deliberate destruction only.** `self_destruct()` has exactly one call
  site, guarded by `attempts >= max_attempts` and by the files being
  verified intact (`bunker.chk`). A test fails if a second call site
  appears or a guard is removed.
- **Damage is not a wrong password.** AES-GCM reports a wrong key and a
  damaged file the same way, so login first checks `bunker.chk`. Only a
  failure on verified files counts as an attempt. A vault from before this
  record existed gets one at its next successful login and is never
  destroyed until then.
- **Never overwrite a vault.** Setup only runs where no vault files exist
  (or an earlier setup was interrupted), and asks every question before
  writing. Changing the master password re-encrypts every field and swaps
  all files together, keeping the old ones until every write succeeded.
- **Atomic, private writes** (0600 temp file, fsync, rename, directory
  fsync) for the vault database, salt, config, settings, key and export files.
- **Vault data never leaves the machine.** BUNKER's only network use is
  looking up your public IP: with the IP display turned on (ipify, and a
  connectivity check to 8.8.8.8), and on the System info screen (ipify,
  ifconfig.me, icanhazip.com). Those services see your IP address and when
  BUNKER runs; turn the IP display off if that matters to you.

## 6. Known limits (residual risk)

1. **Offline guessing (A1).** If someone copies your files, only the master
   password and Argon2id stand in the way. Use a long passphrase.
2. **Settings are only obfuscated, not secret.** This includes the
   failed-attempt counter: deleting `config.cfg` resets it. `config.cfg`, and on Linux
   without a Secret Service the `~/.bunker_ui_key` fallback, are keyed from
   machine details (machine ID, hostname, OS, home path). Anyone who can read
   your files on that machine can rewrite them, including the failed-attempt
   counter. This affects the in-app limit (A2), not the vault's encryption.
3. **Python can't reliably wipe memory.** Strings are immutable and may stay
   in memory until reused. Treat a machine as compromised if someone can read
   BUNKER's memory (A7).
4. **Clipboard history.** Clipboard managers, OS history (for example
   Windows Win+V or KDE Klipper) and remote-desktop tools may keep a copy
   after BUNKER clears the clipboard.
5. **Forced kill.** `kill -9` or a crash of Python itself skips all cleanup,
   so a secret copied less than 30 seconds earlier stays on the clipboard.
6. **Plain-text export** writes your data unencrypted, by design, when you
   choose it.
7. **No pepper.** The code defines a `BUNKER_PEPPER` setting but never uses
   it; setting it has no effect. (The "pepper" argument passed to the key
   derivation is the password itself.) Adding a real pepper would make
   existing vaults unreadable, so it is left as a decision for later.
8. **Dependencies.** BUNKER relies on `cryptography`, `argon2-cffi`,
   `pyperclip`, `psutil` and `requests` (see `requirements.txt`); a flaw in
   one of them affects BUNKER. CI runs `pip-audit` against known advisories.

9. **Deletion is best effort.** Self-destruct overwrites and deletes the
   files, but on SSDs and copy-on-write file systems (APFS, Btrfs, ZFS) old
   blocks may survive, and backups made by other tools are out of reach.
   Treat the vault as gone for BUNKER, not as forensically erased.

## 7. Verifying these claims

```bash
python3 -m unittest discover -s tests -t .
```

The tests cover clipboard clearing (timer, outages, races, SIGTERM), error
text, export and file permissions, atomic writes, and the self-destruct
policy (errors, EOF, Ctrl+C and timeouts keep the vault; the failed-login
limit still destroys it).
