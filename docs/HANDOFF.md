# BUNKER 2.0 — Maintainer handoff

Notes for whoever picks up the v2.0 hardening work next. Read this first;
you should not need anything else to start. Last updated 2026-11-27 (PT): IP display stop and setup warning (§14); generated secrets are copied, not printed (§13); judge pass (§12).

**Next three moves:** (1) once the waiting commits are pushed, keep CI
green on both PRs and merge `hardening/v2.0` into `mobile/shared-vault`
(conflicts listed in §5); (2) ask for a re-check of the review fixes in
§11; (3) work the before-tag list at the top of §7.

## 0. Vision and mandate

**Vision.** BUNKER is a privacy-first password and notes vault that lives
entirely on the user's own device: no cloud, no account, no tracking (see the
README). It is free and source-available, so anyone can read exactly how
their secrets are protected. That matters because a password manager is
only as trustworthy as its worst failure. For BUNKER that means it must never
leak a secret and never lose the user's data.

**North star.** BUNKER should be the offline terminal vault a security team
would recommend without caveats. Concretely, best in the world means:
- strong, standard cryptography (it already has this);
- exactly one, audited way for a secret to leave the vault;
- no path where an error, crash or damaged file destroys or locks a vault;
- every user flow tested end to end with real encryption, on Linux, macOS
  and Windows;
- an honest threat model, with documentation that claims only what the code
  does;
- usable with a screen reader and in plain terminals.

**Next milestone: v2.0 release.** Done when:
1. PRs #1 and #2 are reviewed and merged;
2. CI is green on every OS and Python job;
3. the CodeQL alerts are triaged and dismissed;
4. the release notes match `main`;
5. the maintainer has tagged v2.0 and published the release. That is the
   maintainer's call, never an agent's.

**Standing mandate for the next agent.** Work as a full top-tier security
studio team:
1. **Research first.** Learn how the best products and standards solve the
   problem, and cite them.
2. **Look through several lenses:** security, first-time user, returning
   user, accessibility, reliability, long-term maintenance.
3. **Walk the real user flows end to end** and fix every break and dead end.
4. **Choose one strong concept** grounded in BUNKER's own docs and
   decisions.
5. **Build it to the detail.**
6. **Verify like a strict critic:** tests, real runs, and an independent
   reviewer on the final diff.

Choose the model and effort for each agent, and record them. Changes go
through pull requests only: never merge, tag, release, force-push or
rewrite history. Defensive security only, and the repo is public.

**How to resume (5 minutes):**
1. Read this file.
2. Check PRs #1 and #2: CI status, review comments, and whether either has
   been merged.
3. Check out the branch and run
   `python3 -m unittest discover -s tests -t .` (and compile; see §3).
4. Take the top item in §7 that is still open. Do it, push, and update the
   PR table.

## 1. Goal and context

BUNKER is a free, source-available, offline terminal password and notes
manager (Python 3.10+). The v2.0 work:
1. **Security hardening.** Secrets never logged, printed, or written to
   disk by accident. Copied secrets are cleared from the clipboard. CodeQL
   flagged about 15 clear-text logging alerts. Fixing these uncovered
   several bugs that destroyed or locked vaults.
2. **Honest v2.0 release notes** (`RELEASE_NOTES_v2.0.md`).
3. **README fixes.** The dead Gumroad link is gone and the claims now match
   the code.

The work started from branch `desktop-latest`, which had never been merged
into `main`.

## 2. Branches and PRs

| Branch | PR | Base | What |
|---|---|---|---|
| `hardening/v2.0` | [#1](https://github.com/ZeroMarks/BUNKER2.0/pull/1) (draft) | `main` | All hardening, docs, CI. It also carries `desktop-latest`. `main`'s 9 extra commits are joined by a keep-ours merge, `2bf452f`. |
| `mobile/shared-vault` | [#2](https://github.com/ZeroMarks/BUNKER2.0/pull/2) (draft) | `hardening/v2.0` | Mobile UI on the shared vault format, plus atomic `Bunker.mmf` writes everywhere. |

Merge order: #1, then #2. Both are drafts for the maintainer's review.
`hardening/v2.0` is merged into `mobile/shared-vault` regularly; the last
merge is `e53dde9`.

### Key commits on `hardening/v2.0`

**Vault-loss fixes:**
- `e97a581` Exit cleanup no longer deletes `Bunker.mmf` and `bunker.salt`.
- `6ee4d40` First run: setup creates a vault the login can open (`bunker.cfg`, same KDF as login).
- `9f42b80`, `6c19339` Self-destruct only on the failed-login limit.
- `2fbe2c2` Login: damaged or mismatched files are never counted as wrong passwords (`bunker.chk`).
- `90bee87` Setup never overwrites an existing vault.
- `7e7d538` Master password change re-encrypts every field and swaps the files together.

**Secrets:**
- `a719187`…`c2a30cd` `main/SECURE_IO.py`: `copy_secret`, `reveal_secret`, `safe_error`.
- `2fcfa97`, `1561c40` Clipboard timer race, outage handling, symlink-safe exports.
- `f00b095` Keyed (HMAC) clipboard fingerprint.
- §13 (2026-11-20): `SECURE_IO.offer_secret` hands generated passwords and export passphrases to the clipboard instead of printing them; Klipper refused; revealed secrets bypass the emoji filter.

**Platform:**
- `540ff7b` Python 3.10/3.11 support.
- `9c883d1` CI.
- `cec1d22` Unused `keyboard`/`inputimeout` removed.
- `0b88ea0`, `c5db28f`, `869508b` Hash-pinned `requirements.lock`.

**UX and accessibility:**
- `578cb83` `NO_COLOR`.
- `28c5326` `BUNKER_NO_EMOJI`, and no crash on terminals that can't encode a character.
- `70a5806` `BUNKER_CLIPBOARD_SECONDS`.

**Privacy:**
- `8e3ff26` System info screen: public IP looked up only after an explicit yes; local IP from the interface table, no request. `tests/test_system_info_network.py`.

**Imports:**
- `f40f529` `main/IMPORT_FILES.py`: every export file is size-, type- and field-checked before import; exact duplicates (of the vault or within the file) are skipped, nothing is overwritten; same site and login with a new password is added alongside and reported; preview text shown with control characters escaped. Fixed: importing notes while the vault wasn't loaded replaced the vault; timeout at "display passwords?" looped forever; missing sections and decrypt failures crashed. `tests/test_import_hardening.py` (seeded fuzz with a control round).
- `13219f7` Review follow-ups: `saveDatabase` writes `Bunker.mmf` atomically (`write_private_bytes`); favourite-only differences reported; invisible format characters escaped; tests fail on any unexpected exception inside an import.

**Review fixes (2026-11-01, unpushed; see §11):**
- `8f030f7` Every `Bunker.mmf` save is atomic (`write_private_bytes`), desktop and INITIALIZE.
- `2345aaa` An interrupted master password change can never self-destruct (`bunker.chk` "changing" state, `integrity_status() == "interrupted"`, `self_destruct` re-checks); shared attempt notice with a typed `LAST` confirmation before the destroying attempt; mobile allows one try per start at the limit.
- `bac9160` Auto-logout off (0) no longer exits before the user can type.
- `2e898b5` `config.example` documents the untracked `config.cfg`.

**Docs:**
- `d72e0e4` `docs/THREAT_MODEL.md`.
- `df1e805` `docs/RECOVERY.md`.
- `137b1a2` Release notes.

### Key commits on `mobile/shared-vault`

- `877cb25` `main/VAULT_STORE.py`: the single module that knows the `Bunker.mmf` layout.
- `a8d08c4` Every `Bunker.mmf` write is atomic.
- `b05de30` Mobile reads and saves the desktop format.
- `c798877` Mobile Change Master Password uses the shared implementation.
- `a696718` POSIX-only permission assertions, which fixed the Windows CI jobs.

## 3. Current state

```bash
pip install --require-hashes -r requirements.lock   # or: pip install -r requirements.txt
python3 -m compileall -q BUNKER.py main tests
python3 -m unittest discover -s tests -t .
python3 BUNKER.py   # interactive; needs a real terminal
```

- **`hardening/v2.0` @ `1bf3591`** on GitHub. The commits after it on the local branch are unpushed (the maintainer's push OK is needed): System info IP consent, import hardening, the release-readiness walk (`config.cfg` untracked, recovery docs, release checklist) and the four review fixes. Local branch `claude/project-thread-oyvq2a`; **142 tests pass on Python 3.10 and 3.13** (2026-11-01 PT).
  - CI at `1bf3591` is green on all 12 jobs (Linux, macOS, Windows × Python 3.10–3.13) plus the dependency audit. Re-check after the next push.
- **`mobile/shared-vault` @ `e53dde9`:** 124 tests pass locally.
  - The last confirmed CI result was before the Windows fix `a696718`. Re-check the PR.
- **CodeQL:** run locally with the 2.27.3 bundle, using the same suite as GitHub. 15 alerts on `desktop-latest`, 9 now, all triaged:
  - 7 false positives in `main/DESKTOP.py`: prints of the `MIN/MAX/RECOMMENDED_PASSWORD_LENGTH` constants, and fixed strength-checker tip text.
  - 1 intended sink: `SECURE_IO.reveal_secret`, which shows a secret only after the user explicitly asks.
  - 1 heuristic flag: `SECURE_IO._digest`, an HMAC fingerprint, not password storage.

  GitHub's CodeQL check stays red until these are dismissed in the UI.

## 4. Decisions and why

- **Self-destruct (maintainer ruling).** It fires only when the user
  deliberately triggers it: the failed-login limit, never a crash, error,
  Ctrl+C, timeout or EOF.
  - Code: one call site in `DESKTOP.main`, guarded by `attempts >= max_attempts` **and** `files_state == "ok"`. `tests/test_self_destruct_policy.py` enforces both with an AST check.
  - Reason for the second guard: AES-GCM raises the same `InvalidTag` for a wrong key and for damaged data. So `main/VAULT_FILES.py` keeps `bunker.chk` (SHA-256 of salt and config), and only failures on verified files count.
  - Vaults without a record ("unknown") count attempts but are never destroyed. They get a record at their next successful login.
- **Mobile saves (maintainer ruling).** Mobile uses the same `Bunker.mmf`.
  - `Mobile.mmf` was not a deliberate separate vault: it appeared only in one dead function, and mobile's real save called a method that didn't exist.
  - Mobile now uses desktop's flat `{id: entry}` format through `VAULT_STORE`, because desktop calls `.get()` on every value.
- **One exit path for secrets.** All display, copy and error text goes
  through `SECURE_IO`. Nothing is hidden from the scanner; the intended sink
  is left visible and triaged.
- **Atomic, owner-only writes** (temp file with mode 0600, fsync, `os.replace`) for the vault, salt, config, settings, key files and exports. `tests/test_atomic_vault_writes.py` fails if anything opens `Bunker.mmf` for writing directly.
- **Interrupted password change.** `replace_vault` keeps `*.prev` copies and marks `bunker.chk` as `"changing"` before its first write. While either is present, `integrity_status()` is `"interrupted"`: no attempt is counted (the user may be trying the other password), nothing is destroyed, and `self_destruct()` refuses on its own check too. A password that opens both `bunker.cfg` and `Bunker.mmf` finishes the change (`finish_interrupted_change`). No automatic restore from `.prev`: the user follows `docs/RECOVERY.md`, which keeps the code path small. `tests/test_interrupted_password_change.py` kills a real change after each of its 12 steps.
- **Last attempt.** Both interfaces print `VAULT_FILES.attempts_notice` before every password prompt (`Failed attempts: N of MAX`, using the configured limit). On the desktop, when the next wrong password would destroy the vault, the user must type `LAST`; Enter exits without using it. Mobile never destroys and always allows one try per start, so the right password works at the limit; wrong ones still count.
- **Auto-logout 0 means off** in every prompt helper.
- **`config.cfg` untracked** (maintainer ruling, 2026-11-01): it is tied to the machine and salt. `config.example` documents its keys and defaults; `tests/test_config_example.py` keeps the two in step.
- **KDF unchanged** (Argon2id 100 MiB, t=3, p=8, then PBKDF2): it is above both the OWASP minimum and Bitwarden's default.
- **Clipboard default kept at 30 s,** as documented, and configurable from 5 to 300 s.
- **History never rewritten;** histories are joined with merges.

## 5. Open issues, risks, half-finished

- **Network use** is limited to the optional public-IP features (IP display, off by default; System info after an explicit yes). Never describe BUNKER as making "no network calls"; say it works with the network off and makes no network connection unless you ask it to show your public IP (true and tested once §14 is merged). See `docs/THREAT_MODEL.md` §5.
- **Multi-line note copies:** the clipboard fingerprint normalises line
  endings and trailing whitespace. A later copy by the user of the same
  text with different trailing whitespace would also be cleared. Low impact.
- **No hard limit on guessing.** Deleting `config.cfg` resets the attempt counter (documented). Offline guessing against copied files is limited only by the KDF.
- **Python can't wipe memory;** secrets may linger until the process exits.
- **Stored text is printed raw outside the import preview.** A title or domain holding escape sequences (typed, pasted or imported) still reaches the terminal on the view and list screens. `IMPORT_FILES.printable` is the helper to reuse.
- **Duplicate check is exact.** Entries are compared on every decrypted field; tag order and the favourite flag are ignored. A note that differs by one character is imported as new. Exports carry no timestamps, so a changed password can't be told apart from an older one.
- **Merging into `mobile/shared-vault` will conflict** at every desktop and INITIALIZE `Bunker.mmf` save (#2 uses `VAULT_STORE.write_bytes_atomic`, this branch `write_private_bytes`; both are atomic and #2's wraps the same writer), at the old `importProfiles` write, and in the login blocks of `DESKTOP.main` and `MOBILE.main`. Keep the new `importProfiles` and this branch's login code (interrupted state, attempt notice, `LAST` confirmation); either writer is fine at the save sites. Run `tests/test_atomic_vault_writes.py` after: its source scan reads every file in `main/`.
- **Partly restored folders.** `bunker.chk` does not cover `Bunker.mmf`. An older salt + config + record restored next to a newer database still looks consistent, and three confirmed wrong passwords destroy it (`docs/THREAT_MODEL.md` §6.10). The fix is a generation id shared by the record and a `Bunker.mmf` header: a format change, so it is planned, not done.
- **Coverage gaps:** the interactive menus beyond add, view, copy, export and import are not covered by automated tests. Mobile was never walked by hand on a phone or in Termux.
- **Partial migration:** desktop save sites still encrypt locally and then call the atomic writer. Moving them to `VAULT_STORE.save` is unfinished cleanup (in #2).

## 6. Waiting on the maintainer

1. Dismiss the 9 CodeQL alerts as triaged (§3), and turn on private vulnerability reporting.
2. Keep plain-text export? It's documented and written with 0600 permissions.
3. ~~Should `config.cfg` stay tracked?~~ Decided 2026-11-01: untracked, documented by `config.example`.
4. Add a real pepper? `BUNKER_PEPPER` is defined but unused, and adding one would make existing vaults unreadable.
5. Where should the README live? `Read Me/README.md` isn't shown on the repo page, and `main/README.md` duplicates it. A README redesign draft exists outside the repo and has not been committed.
6. Review and merge #1, then #2. Then tag v2.0 and publish the release.
8. Should copy become the default at the view prompts (§13, recommendation: yes)?
7. Community files (issue forms, `SUPPORT.md`, `SECURITY.md`, `CONTRIBUTING.md` under `.github/`) are prepared on local branch `community/issue-templates` (off `main`, new files only; merge after #1 so their doc links resolve). Recommendation: accept issues only, no outside code PRs while the licence forbids modification. When private vulnerability reporting is on, point `SECURITY.md` at GitHub's "Report a vulnerability" button.

## 7. Next, ranked (each with its first step)

**Before tagging v2.0** (from the independent review of #1; each is hours, not days):
- Restore a root `README.md` and `LICENSE.txt`: the diff moves them, so the repo page would show neither. First step: decide with the maintainer which README goes at the root (§6.5).
- Done (§14): turning the IP display off stops the background lookup thread.
- `docs/THREAT_MODEL.md` A3: most post-login prompts use a fixed 60 s auto-logout, not the configured value; say so (or pass the setting through).
- `SECURITY.md` (prepared on `community/issue-templates`), private vulnerability reporting, SHA-256 checksums and a signed tag (`docs/RELEASE_CHECKLIST.md`).
- Maintainer-only check of the demo data in early history (details kept privately).

**Then:**

1. **Keep CI green on both PRs** after each push, and merge `hardening/v2.0` into `mobile/shared-vault` once the waiting commits land (keep the new `importProfiles` on the conflict).
2. **Escape control characters on every screen that shows stored text.** First step: `grep -n "Domain: \|Title: \|Tags: " main/DESKTOP.py main/MOBILE.py`, wrap each value in `printable()` from `main/IMPORT_FILES.py`, and add a test that stores `"\x1b]52;c;..."` and views it.
3. **Move desktop saves to `VAULT_STORE.save`** (after #2 merges). First step: `grep -n "write_bytes_atomic(\"Bunker.mmf\"" main/DESKTOP.py` and replace one site at a time, running `tests/test_desktop_flows.py`.
4. **Walk mobile by hand** in Termux or a narrow terminal. First step: `stty cols 60; python3 BUNKER.py`, choose mobile, and run setup, then add, view, copy and change password.
5. **Accessibility follow-ups.** Review the prompts with `NO_COLOR=1 BUNKER_NO_EMOJI=1` (the attempt display now uses `max_attempts`). First step: run setup and a wrong-password login with both set.
6. **Optional: import merge choices.** If users ask, offer "replace the old profile" for same-login entries. First step: a test for the prompt in `tests/test_import_hardening.py`; never default to replacing.

7. **Later (low impact):** the timeout message claims "All submitted data has been securely saved" (`INITIALIZE.timeoutCleanup`; nothing is saved, so drop the sentence); plain-text export needs a warning step; the encrypted export format has no version field and reuses one key for two algorithms; `max_attempts` is read from the editable `config.cfg`; a stale setup marker could let setup overwrite a real vault's salt; no directory fsync after rename; login derives the key twice; `self_destruct` still globs `*.bak.*`.

Done: fuzz the import parser, and skip duplicates on re-import (`f40f529`, `13219f7`); the four review must-fix items (§11); Klipper refusal and exact reveal under `BUNKER_NO_EMOJI` (§13).

## 8. Gotchas

- **Imports.** The app is launched as `python3 BUNKER.py`. Modules import each other as `main.X`, and `SHARED_RESOURCES_MOBILE` is also imported top-level by `BUNKER.py`. Always import `main.SECURE_IO`, `main.VAULT_FILES` and so on. `INITIALIZE` imports `SHARED_RESOURCES_MOBILE`, so imports in the other direction must be lazy, inside functions.
- **Two vault classes.** `INITIALIZE.vault` is the login vault (Argon2id + PBKDF2). `SHARED_RESOURCES_MOBILE.vault` derives keys with PBKDF2 only. Always use the INITIALIZE one for keys.
- **`config.cfg`'s key includes `bunker.salt`** (`derive_system_key`). Save the UI settings only *after* the salt exists or has changed; `write_new_vault` and `replace_vault` take an `after_salt` hook for this.
- **Field-level encryption.** Every field (domain, email, username, password, title, content, each tag) is encrypted on its own, and `N/A` is a plain sentinel. Re-keying must touch every field (`VAULT_FILES.rekey_database`).
- **The timeout prompt.** `timeoutInput` returns a special code (`timeoutGlobalCode`) on timeout; handle it wherever you add a prompt.
- **Lock file.** `pip-compile` resolves for the Python it runs on. Dependencies that apply only to older Pythons must be listed in `requirements.txt` explicitly.
- **Test conventions.** Real-crypto tests take about 0.3 s per key derivation. Keep fuzz rounds small, and include a control round that shows the harness reaches success. Permission (0600) checks are POSIX-only; skip them on Windows.
- **Logging in.** `DESKTOP.main` reads `bunker.cfg` before asking for the password, and decides with `VAULT_FILES.integrity_status()` first.
- **CodeQL locally.** Download the CodeQL bundle (`github/codeql-action` release `codeql-bundle-linux64.tar.gz`), then run `codeql database create --language=python` followed by `database analyze ... codeql/python-queries:codeql-suites/python-code-scanning.qls`. This gives the alert list when the code-scanning API isn't available.

## 9. Working rules

- Change code only through pull requests. **Never merge, tag, publish a
  release, force-push or rewrite history;** the maintainer reviews first.
- Small, logical commits, each passing compile and tests on its own. Push
  after every finished item. Keep the PR descriptions' tables current.
- **Public repo:** no secrets, personal details, or internal business notes in
  files, commits or PRs. Commits use a no-reply author address. Security
  reports go to support@zeromarks.net.
- **Defensive security only.** State limits honestly, and never hide code
  from scanners to make warnings go away.
- **Agents:** pick the model and effort for each job (cheap and low for
  sweeps, mid for building and tests, strongest and high for security
  review), and record them. Use an independent reviewer on the final diff.
- **Quality bar:** best in the world. Research what the leading tools and
  standards do, walk every user flow end to end, verify with tests and real
  runs, and only claim what has been verified.

## 10. Release-readiness walk (2026-11-01, Pacific time)

Walked a fresh copy in a real terminal (pty) on Linux: first run, add, read,
copy and auto-clear (checked with xclip), encrypted export, delete, import,
notes, change master password, wrong password, damaged and missing files,
System info. All worked. On `mobile/shared-vault` the mobile first run was
also walked. Not walked: a real phone or Termux, macOS, Windows by hand.

Found and fixed (commits on top of `hardening/v2.0`, unpushed):
- `config.cfg` was tracked. Fresh clone + mobile (the suggestion at 80
  columns) stopped at "UI config file missing or corrupted" before setup.
  Now untracked and ignored with `bunker.chk` and `*.prev`.
- `docs/RECOVERY.md` now quotes the messages BUNKER actually prints.
- Release notes: new known limitations (Linux clipboard tool, interface
  guess by terminal width).
- `docs/RELEASE_CHECKLIST.md` lists the steps to tag v2.0.

Open gaps (not fixed, in rough order):
1. A damaged `bunker.salt` shows "UI config file ... InvalidTag" with no
   pointer to RECOVERY.md (`main/SHARED_RESOURCES_MOBILE.py` `load_ui_config`).
2. First run on a fresh folder prints "Bunker.mmf was DESTROYED or not
   found", which alarms new users (`main/DESKTOP.py`, `main/MOBILE.py`).
3. Menus say "Version: BETA" (`main/DESKTOP.py:371,1157,2577`).
4. Terminals up to 120 columns are guessed to be mobile or tablet.
5. Deleting profiles has no confirmation after choosing "delete all".
6. Changing the master password does not ask for the current one while
   logged in (design choice to confirm).

## 11. Review fixes (2026-11-01 evening, Pacific time)

An independent review of #1 at `1bf3591` asked for four fixes before
merge. All four are local commits on top of the earlier unpushed work
(§3), with tests; 142 tests pass on Python 3.10 and 3.13.

| Fix | Commit | Tests |
|---|---|---|
| A master password change killed after the database swap left files that checked as intact; three tries of the new password then self-destructed, `.prev` copies included. Now an unfinished change is "interrupted": nothing counted or destroyed, `self_destruct` refuses, RECOVERY.md has the steps. | `2345aaa` | `test_interrupted_password_change.py` (child process killed after each of 12 steps; real crypto) |
| Desktop and INITIALIZE `Bunker.mmf` saves truncated before writing (disk full left a 0-byte vault). | `8f030f7` | `test_atomic_vault_writes.py` (source scan, disk-full runs) |
| No warning before the destroying attempt; mobile failures made one desktop typo destructive; mobile refused the right password at the limit. | `2345aaa` | `test_login_attempts.py` |
| Auto-logout "off" (0) exited before the user could type. | `bac9160` | `test_autologout_off.py` |

The reviewer's own reproduction scripts were re-run against these commits:
the crash case no longer destroys, and the timeout-0 case waits for input.
Design choices made here (maintainer may revisit): wrong passwords are not
counted while a change is interrupted; the destroying attempt needs a typed
`LAST`; mobile allows one try per start at the limit.

Not done: pushing (waits on the maintainer), the re-check by the reviewer,
and the before-tag list in §7.

## 12. Judge pass (2026-11-20, Pacific time)

The 14 waiting commits apply cleanly on `hardening/v2.0` and 142 tests pass (Linux, Python 3.13). PR #2's head passes 124. No crypto defects found.

**Before merging #2:**
- Two processes saving one vault lose edits: `VAULT_STORE.modify` has no lock, and desktop saves the `db` it loaded at login. First step: a lock file around load, change and save, and a test with two interleaved `modify` calls. The note manager's "reload latest" opens `Bunker.mmf` in text mode (`DESKTOP.py`, `open("Bunker.mmf", "r")`), so it always falls back to the stale copy; change it to `"rb"`.
- When merging, keep the interrupted-password-change handling in the mobile login (`finish_interrupted_change()` after a correct password), and keep #2's folder fsync in `SECURE_IO`.

**Before tagging:**
- Done (§14): `stop_ip_fetch_thread()` did not stop the thread, and the next "on" started a second one.
- Windows clipboard history and cloud clipboard keep copied secrets. First step: in `SECURE_IO`, set the registered formats `ExcludeClipboardContentFromMonitorProcessing`, `CanIncludeInClipboardHistory` = 0 and `CanUploadToCloudClipboard` = 0 alongside the text (as KeePassXC does).

- Done (§14): setup never warned that wrong passwords destroy the vault, and its `.g` guide said "not implemented".

**Later:** mobile errors disappear after one second (wait for Enter instead); mobile edit or delete of an entry changed elsewhere gives a bare `KeyError` or a false "deleted"; a future format should store KDF parameters in a header and bind fields to their record with GCM associated data.

## 13. Generated secrets are copied, not printed (2026-11-20, Pacific time)

Branch `claude/project-thread-rbp9mm`, a draft PR into `hardening/v2.0`. It
is built on the review-fix commits of §11, so it carries them too.

**Question.** Where does BUNKER still put a secret on screen without being
asked? **Found:** three places. The password generator printed the new
password and copied it; both encrypted exports printed a generated
passphrase in the summary box. Everything else already asked first
(`v` to view, `c` to copy).

**What the best tools do.** `pass -c` and `gopass show -c` copy and clear
after 45 s without printing; KeePassXC's `clip` command does the same with
a timeout; 1Password's CLI conceals fields unless `--reveal` is given.
Copy first, show only on request, is the common rule.

**Ruling and build.**
- `SECURE_IO.offer_secret(what, value, ask, warning="")`: copies with the
  usual auto-clear, prints a plain-text notice, and shows the secret only
  if the user types `v`. If the clipboard fails it says "NOT copied"
  before the user chooses. The text has no colour, emoji or box drawing.
- The generator and both exports show a mask and call `offer_secret`. The
  export adds: "without it this export cannot be opened".
- The Klipper fallback of `pyperclip` is refused (it passes the text on a
  command line); `copy_secret` returns False as for a missing tool.
- `reveal_secret` writes the value past the `BUNKER_NO_EMOJI` filter, so a
  viewed password keeps every character.
- An export passphrase is `required=True`: if it could not be copied, the
  prompt repeats until the user types `v`, because the export is already
  written and nothing else can open it.
- Tests: `tests/test_offer_secret.py` (the helper, the generator screen, a
  real encrypted export opened in a new vault with the copied passphrase
  and with no clipboard, Klipper, emoji). 163 tests pass on Python 3.13; CI
  was green on all 12 OS and Python jobs before the review follow-ups.
- An independent review of the diff found the unopenable-export case above
  and two weak tests; all three are fixed.

**Not done, in order:**
1. The existing view prompts still treat `v` and `c` as equals. Making
   Enter mean copy needs the near-identical blocks (8 for passwords, more for notes) in `main/DESKTOP.py`
   (search `Type 'v' to view`) moved to one helper first. Maintainer call
   (§6.8).
2. The import preview's "display passwords?" still prints every password
   when answered yes. It is asked for, but there is no copy alternative.
3. A viewed secret stays in terminal scrollback (`docs/THREAT_MODEL.md`
   §6.11). An alternate-screen reveal would fix that on most terminals.
4. Mobile has no generator or export, so nothing changed there.
5. Not walked by hand in a real terminal with a real clipboard tool.
6. A generated passphrase pasted after the 30 s clear, or left at the
   prompt until auto-logout, is gone. The export must then be made again.
   Offering the passphrase before the file is written would close this.

## 14. IP display stop and setup warning (2026-11-27, Pacific time)

Two of the three before-tag items from §12. An independent review of the diff found a test that could not fail and imprecise mobile wording; both are fixed. 210 tests pass on Python 3.13.

**IP display (`main/SHARED_RESOURCES.py`).**
- The lookup thread waits on a `threading.Event` (`stop_event.wait(IP_REFRESH_SECONDS)`) instead of `time.sleep(30)`. `stop_ip_fetch_thread()` sets the event, so the thread wakes and exits; it re-checks the event between the connectivity check and the lookup, and before it stores a result.
- `start_ip_fetch_thread()` holds a lock and treats a thread that was told to stop as not running, so off/on never leaves more than one thread looking up (a stopped thread may still be finishing its last call, and discards it).
- The network calls now run outside `cache_lock`. Before, drawing the banner could wait up to about 15 seconds for a lookup.
- Stop forgets the cached address; the banner shows "(checking...)" until the first answer instead of "None".
- Limit: a lookup already under way when the display is turned off is not cancelled (the 8.8.8.8 check has a 5 s timeout, `curl` 10 s). Its result is discarded. Cancelling it would mean running `curl` with `Popen` and killing it on stop.
- Tests: `tests/test_ip_display_thread.py` (counters stand in for the network), `tests/test_offline_by_default.py` (setup and desktop login with every network call blocked, real banner).

**Setup warning (`vaultSetup` in `main/SHARED_RESOURCES_MOBILE.py`).**
- After "y" at the first prompt and before the show-password question, setup prints `VAULT_FILES.self_destruct_warning()` and waits: Enter continues, `.c` cancels with nothing written, anything else asks again.
- `vaultSetup(setup_guide=None, destroys=True)`: the desktop passes `display_setup_guide`; a phone or tablet gets `setup_guide_short()` and the mobile sentence (that interface never deletes; the desktop does).
- The number comes from `VAULT_FILES.DEFAULT_MAX_ATTEMPTS`, the same constant setup writes to `config.cfg`. The in-app user guide reads `max_attempts` from `config.cfg`. `attempt_limit()` falls back to the default for anything that is not a whole number of at least 1.
- Tests: `tests/test_setup_warning.py`, including a scan that no module in `main/` hard-codes "three incorrect" again.
- Walked by hand in a pseudo-terminal with `NO_COLOR=1 BUNKER_NO_EMOJI=1`: desktop (`.g`, a section, `.c`, the warning, cancel) and mobile (warning, a refused answer, full setup to the login screen).

**Not done:**
1. `max_attempts` cannot be changed from inside BUNKER, and the other places that create a default `config.cfg` (`load_ui_config`, `MOBILE.py`) still write a literal 3. First step: use `DEFAULT_MAX_ATTEMPTS` there too.
2. Login now reads the limit through `attempt_limit()` too, so a broken `max_attempts` in `config.cfg` cannot make the guides and the login disagree.
3. The mobile sentence is long for a narrow screen. Shorten it only with wording that stays true for attempts made on both interfaces.
4. Windows clipboard history (§12) is the remaining before-tag item.
