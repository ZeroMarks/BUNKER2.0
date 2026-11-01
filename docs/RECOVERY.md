# BUNKER — When the vault won't open

BUNKER never deletes your vault because of an error. If it refuses to open,
your files are still there. Find the message you saw below.

Before trying anything, **copy the whole BUNKER folder somewhere safe**, so
every step below can be undone.

## "The vault files are damaged or out of step with each other"

BUNKER keeps `bunker.chk`, a record of what `bunker.salt` and `bunker.cfg`
should look like. This message means one of them no longer matches. Common
causes: a sync tool or backup restored only some files, a disk problem, or
BUNKER was closed in the middle of changing the master password.

No login attempt was counted.

1. **If files ending in `.prev` exist** (`Bunker.mmf.prev`, `bunker.cfg.prev`,
   `bunker.salt.prev`), a master password change was interrupted. They are
   the complete previous set. Rename each back, removing `.prev`, so all
   three come from the same moment, and open BUNKER with your **old**
   password.
2. **If you restored from a backup**, restore `Bunker.mmf`, `bunker.salt`,
   `bunker.cfg` and `bunker.chk` together, from the same backup.
3. **If you are sure the three main files belong together** (for example
   you copied them yourself as a set) and only `bunker.chk` is wrong,
   delete `bunker.chk`. BUNKER then treats the vault as one from before the
   record existed, and creates a fresh record at your next successful
   login. Until then, wrong passwords are counted but never destroy
   anything.

## "bunker.salt or bunker.cfg is missing"

Both are needed to open the vault; without the salt the key cannot be
derived. Restore them from the same backup as `Bunker.mmf`. There is no
way to rebuild them.

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

- On a vault with a valid `bunker.chk`, three wrong master passwords
  destroy the vault by design. Only an exported backup can bring the data
  back (see below).
- On a vault without a valid record, BUNKER leaves the files untouched and
  exits.

## Restoring from an export

If you kept an export (main menu **(a) Manage accounts** or **(s) Manage
notes**, then **(c) Export/Import**), start
BUNKER in an empty folder to create a new vault, then import the file. For
an encrypted export you need its passphrase. Profiles and notes come back
exactly; this is covered by automated tests.
