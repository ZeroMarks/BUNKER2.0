"""Child process for test_vault_concurrency: a second BUNKER working on the
vault in the current folder. ``argv[1]`` picks what it does:

* ``hold``: take the vault lock, print "locked", keep it until a line
  arrives on stdin (or the process is killed).
* ``add KEY PREFIX COUNT``: like the mobile interface, add COUNT entries one
  at a time with VAULT_STORE.modify.
* ``held KEY PREFIX COUNT``: like the desktop interface, load the vault
  once, then add COUNT entries to that in-memory copy, saving after each
  with VAULT_STORE.commit.

KEY is the base64 vault key (a random test key, never a real one).
"""
import sys

from main import VAULT_STORE as S

S.LOCK_TIMEOUT = 120  # slow CI machines: wait rather than fail


def entry(name):
    return {"title": name, "content": name}


def main(argv):
    mode = argv[1]
    if mode == "hold":
        with S.locked():
            sys.stdout.write("locked\n")
            sys.stdout.flush()
            sys.stdin.readline()
        return 0
    key, prefix, count = argv[2].encode(), argv[3], int(argv[4])
    if mode == "add":
        for i in range(count):
            name = f"{prefix}-{i}"
            S.modify(key, lambda db, name=name: db.__setitem__(name, entry(name)))
        return 0
    if mode == "held":
        db = S.load(key)
        for i in range(count):
            name = f"{prefix}-{i}"
            db[name] = entry(name)
            S.commit(db, key)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
