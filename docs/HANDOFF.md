# BUNKER 2.0 — Maintainer handoff

Notes for whoever picks up the v2.0 hardening work next. Read this first;
you should not need anything else to start. Last updated 2026-10-31 (PT), import work 2026-10-31 night (PT).

**Next three moves:** (1) keep CI green on both PRs once the waiting
commits are pushed; (2) escape terminal control characters on every
screen that shows stored text, not just the import preview; (3) move
desktop saves to `VAULT_STORE.save` after #2 merges. Details in §7.

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

- **`hardening/v2.0` @ `8e3ff26`:** 80 tests pass locally (Python 3.13).
  - Local branch `claude/project-thread-evt0n6` (off `hardening/v2.0`, includes the two unpushed commits) adds the import work: 111 tests pass locally (Python 3.13). Reviewed by an independent agent (Opus, high effort); its findings are fixed in `13219f7`. Not pushed; waits on the maintainer's push OK.
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
- **Atomic, owner-only writes** (temp file with mode 0600, fsync, `os.replace`) for the salt, config, settings, key files, exports and, in #2, the vault. Multi-file changes such as a password change keep `*.prev` copies until every write has succeeded.
- **KDF unchanged** (Argon2id 100 MiB, t=3, p=8, then PBKDF2): it is above both the OWASP minimum and Bitwarden's default.
- **Clipboard default kept at 30 s,** as documented, and configurable from 5 to 300 s.
- **History never rewritten;** histories are joined with merges.

## 5. Open issues, risks, half-finished

- **Network use** is limited to the optional public-IP features (IP display, off by default; System info after an explicit yes). Never describe BUNKER as making "no network calls"; say it works with the network off and makes no request unless asked to show the public IP. See `docs/THREAT_MODEL.md` §5.
- **Multi-line note copies:** the clipboard fingerprint normalises line
  endings and trailing whitespace. A later copy by the user of the same
  text with different trailing whitespace would also be cleared. Low impact.
- **No hard limit on guessing.** Deleting `config.cfg` resets the attempt counter (documented). Offline guessing against copied files is limited only by the KDF.
- **Python can't wipe memory;** secrets may linger until the process exits.
- **Stored text is printed raw outside the import preview.** A title or domain holding escape sequences (typed, pasted or imported) still reaches the terminal on the view and list screens. `IMPORT_FILES.printable` is the helper to reuse.
- **Duplicate check is exact.** Entries are compared on every decrypted field; tag order and the favourite flag are ignored. A note that differs by one character is imported as new. Exports carry no timestamps, so a changed password can't be told apart from an older one.
- **Merging into `mobile/shared-vault` will conflict** at the old `importProfiles` write and at `saveDatabase`'s write (#2 uses `write_bytes_atomic`, this branch `write_private_bytes`; both are atomic). Keep the new `importProfiles`; either writer is fine in `saveDatabase`. The other desktop save sites on this branch still write in place until #2 lands.
- **Coverage gaps:** the interactive menus beyond add, view, copy, export and import are not covered by automated tests. Mobile was never walked by hand on a phone or in Termux.
- **Partial migration:** desktop save sites still encrypt locally and then call the atomic writer. Moving them to `VAULT_STORE.save` is unfinished cleanup (in #2).

## 6. Waiting on the maintainer

1. Dismiss the 9 CodeQL alerts as triaged (§3), and turn on private vulnerability reporting.
2. Keep plain-text export? It's documented and written with 0600 permissions.
3. Should `config.cfg` stay tracked in the repo?
4. Add a real pepper? `BUNKER_PEPPER` is defined but unused, and adding one would make existing vaults unreadable.
5. Where should the README live? `Read Me/README.md` isn't shown on the repo page, and `main/README.md` duplicates it. A README redesign draft exists outside the repo and has not been committed.
6. Review and merge #1, then #2. Then tag v2.0 and publish the release.
7. Community files (issue forms, `SUPPORT.md`, `SECURITY.md`, `CONTRIBUTING.md` under `.github/`) are prepared on local branch `community/issue-templates` (off `main`, new files only; merge after #1 so their doc links resolve). Recommendation: accept issues only, no outside code PRs while the licence forbids modification. When private vulnerability reporting is on, point `SECURITY.md` at GitHub's "Report a vulnerability" button.

## 7. Next, ranked (each with its first step)

1. **Keep CI green on both PRs** after each push, and merge `hardening/v2.0` into `mobile/shared-vault` once the waiting commits land (keep the new `importProfiles` on the conflict).
2. **Escape control characters on every screen that shows stored text.** First step: `grep -n "Domain: \|Title: \|Tags: " main/DESKTOP.py main/MOBILE.py`, wrap each value in `printable()` from `main/IMPORT_FILES.py`, and add a test that stores `"\x1b]52;c;..."` and views it.
3. **Move desktop saves to `VAULT_STORE.save`** (after #2 merges). First step: `grep -n "write_bytes_atomic(\"Bunker.mmf\"" main/DESKTOP.py` and replace one site at a time, running `tests/test_desktop_flows.py`.
4. **Walk mobile by hand** in Termux or a narrow terminal. First step: `stty cols 60; python3 BUNKER.py`, choose mobile, and run setup, then add, view, copy and change password.
5. **Accessibility follow-ups.** Make the desktop attempt display use `max_attempts` (it hardcodes "of 3"), and review the prompts with `NO_COLOR=1 BUNKER_NO_EMOJI=1`. First step: grep `"Attempt 1 of 3"` in `main/DESKTOP.py`.
6. **Optional: import merge choices.** If users ask, offer "replace the old profile" for same-login entries. First step: a test for the prompt in `tests/test_import_hardening.py`; never default to replacing.

Done: fuzz the import parser, and skip duplicates on re-import (`f40f529`, `13219f7`).

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
