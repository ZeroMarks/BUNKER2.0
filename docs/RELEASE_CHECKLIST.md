# BUNKER 2.0 — Release checklist

For the maintainer. Each step says how to check it. Nothing here is done
for you: merging, tagging and publishing are the maintainer's call.

## Before merging

- [ ] PR #1 (`hardening/v2.0` → `main`): all checks green (12 test jobs: Linux, macOS, Windows × Python 3.10–3.13, plus the dependency audit).
- [ ] CodeQL alerts triaged and dismissed (see HANDOFF §3 and §6).
- [ ] PR #2 (`mobile/shared-vault` → `hardening/v2.0`) green, merged after #1. Release both together: on #1 alone the mobile interface cannot save, and the release notes say otherwise once #2 is in.
- [ ] README PR merged or consciously deferred; its claims match `RELEASE_NOTES_v2.0.md` (no "never touches the network": the optional public-IP features exist).

## Verify on a fresh download (not your working folder)

Download the branch as a ZIP (or `git clone`) into an empty folder, then:

- [ ] `pip install --require-hashes -r requirements.lock` succeeds on Python 3.10 and on the newest version you ship for.
- [ ] `python3 -m unittest discover -s tests -t .` passes.
- [ ] `python3 BUNKER.py` in an 80-column terminal: it suggests *mobile*; answer **y** and confirm first-run setup works (no "UI config file" error). Then answer **n**, pick Desktop, and confirm the same.
- [ ] Add a profile and a note; copy a password; the clipboard is empty after the timeout (on Linux you need `xclip`, `xsel` or `wl-clipboard`).
- [ ] Encrypted export, delete the profile, import: the profile is back.
- [ ] Change the master password, log out, log in with the new one; a wrong password shows the attempt counter and leaves the files alone.
- [ ] System info: "Look up your public IP online?" appears, and answering **n** makes no request.
- [ ] Rename `bunker.salt` and start BUNKER: the message points to `docs/RECOVERY.md`, and no file is deleted.

## Tag and publish

- [ ] `RELEASE_NOTES_v2.0.md` matches what is on `main` (read the "Known limitations" list against the final merge).
- [ ] Menu headers still say "Version: BETA"; change them or accept that wording on purpose.
- [ ] Tag `v2.0` on the merge commit, publish the release with the notes, and attach nothing that the repo does not build (there are no installers).
