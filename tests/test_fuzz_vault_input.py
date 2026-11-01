"""Fuzz the vault read path with corrupted and hostile files.

Property: decrypting or loading a damaged vault either returns the exact
original data or raises an exception. It never returns altered data, never
hangs, and never deletes or rewrites any file.
"""
import base64
import contextlib
import io
import json
import os
import random
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import main.INITIALIZE as I

SEED = 20261101
ROUNDS = 300


def mutate(rng, blob):
    data = bytearray(blob)
    choice = rng.randrange(6)
    if choice == 0 and data:                       # flip bits
        for _ in range(rng.randint(1, 8)):
            data[rng.randrange(len(data))] ^= 1 << rng.randrange(8)
    elif choice == 1:                              # truncate
        del data[rng.randrange(len(data) + 1):]
    elif choice == 2:                              # append junk
        data += os.urandom(rng.randint(1, 64))
    elif choice == 3:                              # random bytes, random size
        data = bytearray(os.urandom(rng.randint(0, 200)))
    elif choice == 4 and len(data) > 12:           # swap nonce
        data[:12] = os.urandom(12)
    else:                                          # empty / tiny
        data = bytearray(os.urandom(rng.randint(0, 12)))
    return bytes(data)


class FuzzVaultInput(unittest.TestCase):
    def setUp(self):
        self.key = base64.urlsafe_b64encode(os.urandom(32))
        self.db = {"id-1": {"domain": "x", "password": "y", "favorite": False}}
        self.good = I.vault.encrypt_data(json.dumps(self.db).encode(), self.key)

    def test_decrypt_never_returns_altered_plaintext(self):
        rng = random.Random(SEED)
        original = json.dumps(self.db).encode()
        for _ in range(ROUNDS):
            bad = mutate(rng, self.good)
            try:
                out = I.vault.decrypt_data(bad, self.key)
            except Exception:
                continue
            self.assertEqual(out, original, "corrupted input decrypted to different data")

    def test_load_database_rejects_damage_and_touches_nothing(self):
        rng = random.Random(SEED + 1)
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                Path("bunker.salt").write_bytes(b"s" * 32)
                Path("bunker.cfg").write_bytes(b"cfg")
                with mock.patch.object(I, "self_destruct") as wipe, \
                     contextlib.redirect_stdout(io.StringIO()):
                    for _ in range(ROUNDS):
                        bad = mutate(rng, self.good)
                        Path("Bunker.mmf").write_bytes(bad)
                        try:
                            result = I.loadDatabase(self.key)
                        except Exception:
                            pass
                        else:
                            self.assertEqual(result, self.db)
                        self.assertEqual(Path("Bunker.mmf").read_bytes(), bad)
                wipe.assert_not_called()
                self.assertEqual(Path("bunker.salt").read_bytes(), b"s" * 32)
                self.assertEqual(Path("bunker.cfg").read_bytes(), b"cfg")
                self.assertEqual(sorted(os.listdir(".")), ["Bunker.mmf", "bunker.cfg", "bunker.salt"])
            finally:
                os.chdir(cwd)

    def test_wrong_key_never_decrypts(self):
        for _ in range(50):
            other = base64.urlsafe_b64encode(os.urandom(32))
            with self.assertRaises(Exception):
                I.vault.decrypt_data(self.good, other)


if __name__ == "__main__":
    unittest.main()
