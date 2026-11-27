# BUNKER — When the vault won't open

BUNKER never deletes your vault because of an error. If it refuses to open,
your files are still there. Find the message you saw below.

Before trying anything, **copy the whole BUNKER folder somewhere safe**, so
every step below can be undone.

## "A master password change did not finish"

BUNKER was closed (terminal closed, shutdown, power cut) while it was
changing the master password. BUNKER saw files ending in `.prev`
(`Bunker.mmf.prev`, `bunker.cfg.prev`, `bunker.salt.prev`) or a
`bunker.chk` that says the change was still running.

While this message is shown, **wrong passwords are not counted and nothing
is ever deleted**, so you can safely try both passwords.

1. Try your **new** password, then your **old** one. If either opens the
   vault, BUNKER finishes the job by itself: it records the files as a
   complete set and removes the `.prev` copies. Nothing else to do.
2. If you see **"this password opens only part of the vault"** or neither
   password works, the change stopped half-way. The `.prev` files are the
   complete set from before the change. Rename each back over the file of
   the same name (`Bunker.mmf.prev` → `Bunker.mmf`, `bunker.cfg.prev` →
   `bunker.cfg`, `bunker.salt.prev` → `bunker.salt`) and open BUNKER with
   your **old** password.
3. If BUNKER then stops at "UI config file missing or corrupted", delete
   `config.cfg` (see that section below) and try again with your old
   password.

## "Failed to open the vault after login"

The password was right for `bunker.cfg`, but `Bunker.mmf` would not open
with it, so the two files come from different moments. No login attempt
was counted and nothing was deleted.

- If `.prev` files exist, follow step 2 of the section above.
- Otherwise restore `Bunker.mmf`, `bunker.salt`, `bunker.cfg` and
  `bunker.chk` together, from the same backup.

## "The vault files are damaged or out of step with each other"

BUNKER keeps `bunker.chk`, a record of what `bunker.salt` and `bunker.cfg`
should look like. This message means one of them no longer matches. Common
causes: a sync tool or backup restored only some files, or a disk problem.

No login attempt was counted.

1. **If files ending in `.prev` exist**, see "A master password change did
   not finish" above.
2. **If you restored from a backup**, restore `Bunker.mmf`, `bunker.salt`,
   `bunker.cfg` and `bunker.chk` together, from the same backup.
3. **If you are sure the three main files belong together** (for example
   you copied them yourself as a set) and only `bunker.chk` is wrong,
   delete `bunker.chk`. BUNKER then treats the vault as one from before the
   record existed, and creates a fresh record at your next successful
   login. Until then, wrong passwords are counted but never destroy
   anything.

## "Unexpected error (FileNotFoundError ...)" followed by "What to do next: docs/RECOVERY.md"

This is what BUNKER shows when `bunker.salt` or `bunker.cfg` is missing.
Both are needed to open the vault; without the salt the key cannot be
derived. Restore them from the same backup as `Bunker.mmf`. There is no
way to rebuild them.

## "UI config file missing or corrupted. Error: InvalidTag"

`config.cfg` (your settings and the failed-attempt counter) could not be
read. It is locked with a key that depends on `bunker.salt`, so this appears
if `config.cfg` is damaged **or if `bunker.salt` was changed or damaged**.
Nothing is deleted when you see it.

1. Put back the `bunker.salt` and `config.cfg` that belong to your vault
   (the same backup as `Bunker.mmf`), then try again.
2. If `bunker.salt` is intact and only `config.cfg` is damaged, delete
   `config.cfg`. BUNKER creates a new one with the default settings. The
   failed-attempt counter and auto-logout timer go back to their defaults;
   the vault itself is unaffected.
3. If `bunker.salt` itself is damaged and you have no copy, the vault cannot
   be opened, because without the salt there is no key. Restore from an
   encrypted export (see the last section).

## "The password is correct but the vault files are inconsistent"

`bunker.cfg` opened with your password, but it describes a different salt
than `bunker.salt`. Restore `bunker.salt` and `bunker.cfg` from the same
backup or the same `.prev` set (see above).

## "Bunker.mmf exists but cannot be opened"

Another program (antivirus, cloud sync, backup) may have the file locked,
or its permissions changed. Close that program or fix the permissions and
try again. BUNKER does not start a new setup in this case, so your vault is
safe.

## "Vault files already exist in this folder, but Bunker.mmf could not be found"

Setup refuses to create a new vault over existing ones, because that would
make the old vault impossible to open. Put `Bunker.mmf` back. If you really
want a new, empty vault, move the old `bunker.salt`, `bunker.cfg` and
`bunker.chk` to another folder first.

## "Maximum attempts reached"

- On a vault with a valid `bunker.chk`, three wrong master passwords in a row
  (the default limit) destroy the vault by design, in the desktop and the
  mobile interface alike. Setup says so before the vault is created. Before
  the last one, BUNKER shows "LAST ATTEMPT" and asks you to type `LAST`;
  pressing Enter instead exits without using the attempt. Only an exported
  backup can bring the data back after a self-destruct (see below).
- The counter is shared by both interfaces and kept between starts, so
  switching interface or restarting BUNKER gives no extra attempts. If the
  counter is already at the limit, the right password still works once you
  type `LAST`.
- On a vault without a valid record, or while a password change is
  unfinished, BUNKER leaves the files untouched and exits.

## Restoring from an export

If you kept an export (main menu **(a) Manage accounts** or **(s) Manage
notes**, then **(c) Export/Import**), start
BUNKER in an empty folder to create a new vault, then import the file. For
an encrypted export you need its passphrase. Profiles and notes come back
exactly; this is covered by automated tests.
