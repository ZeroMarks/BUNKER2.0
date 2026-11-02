"""Child process for test_interrupted_password_change.

Runs a real master password change in the current folder and kills the
process with os._exit() right after step number ``argv[1]``, where a step is
one file write or one removal of a ``*.prev`` copy. os._exit skips every
``except``/``finally`` block, like closing the terminal, a shutdown or a
power cut. Exit code 0 means the kill point was reached, 3 means the change
finished first. Prints the step names to stdout.
"""
import contextlib
import io
import os
import sys
from unittest import mock

import main.INITIALIZE as I
import main.SHARED_RESOURCES_MOBILE as M
import main.VAULT_FILES as VF
from main import SECURE_IO

OLD_PASSWORD, NEW_PASSWORD = sys.argv[2], sys.argv[3]
KILL_AFTER = int(sys.argv[1])
steps = []


def step(name):
    steps.append(name)
    if len(steps) == KILL_AFTER:
        sys.__stdout__.write("\nSTEPS: " + " ".join(steps) + "\n")
        sys.__stdout__.flush()
        os._exit(0)


real_write = SECURE_IO.write_private_bytes
real_remove = os.remove


def counting_write(path, data):
    real_write(path, data)
    step(f"write:{path}")


def counting_remove(path, *a, **k):
    real_remove(path, *a, **k)
    if str(path).endswith(VF.BACKUP_SUFFIX):
        step(f"remove:{path}")


key = I.vault.derive_key_hybrid(OLD_PASSWORD, open("bunker.salt", "rb").read(), OLD_PASSWORD)
with mock.patch.object(VF, "write_private_bytes", counting_write), \
     mock.patch.object(M, "write_private_bytes", counting_write), \
     mock.patch.object(VF.os, "remove", counting_remove), \
     mock.patch("builtins.input", lambda *a, **k: "n"), \
     mock.patch.object(I, "timeout_getpass", lambda *a, **k: NEW_PASSWORD), \
     mock.patch.object(I, "timeoutInput", lambda *a, **k: ""), \
     mock.patch.object(I, "clear_screen", lambda *a, **k: None), \
     contextlib.redirect_stdout(io.StringIO()):
    try:
        I.changeMasterPassword(key, I.loadDatabase(key))
    except SystemExit:
        pass
sys.__stdout__.write("\nSTEPS: " + " ".join(steps) + "\n")
sys.exit(3)
