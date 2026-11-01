# BUNKER 2.0: Login & Setup Patch Documentation


## Overview
This document summarizes the critical changes made to the BUNKER 2.0 password vault setup and login flow, with a focus on secure key management, atomic file operations, and alignment with best practices and requirements. It also documents the structure and security properties of key vault files.


---


## 1. Patch Summary: Login & Setup Flow


### What Changed
- **UI_KEY Generation & Storage:**
 - The UI_KEY (user interface encryption key) is now generated and securely stored *before* any config or salt file operations.
 - All config and UI settings encryption uses the same UI_KEY instance.
 - If UI_KEY storage fails, setup aborts securely.


- **Atomic File Writes:**
 - `bunker.salt` and `config.cfg` are written atomically (to a temp file, then renamed) and only checked after creation.
 - File permissions are enforced (0600 on POSIX).


- **Consistent Key Usage:**
 - The same UI_KEY is used for all config encryption/decryption.
 - No config or salt file is created or accessed before the UI_KEY is confirmed to be set.


- **Error Handling:**
 - Clear error messages and aborts on any failure in key storage or file creation.
 - Debug/info logs are removed or replaced with user-facing errors only.


- **No Change to Feature Logic:**
 - Only the login/setup flow is updated. Features like change master password, settings, etc., are not yet updated to use the new key flow.


---


## 2. File Structure & Security Properties


| File           | Purpose                                 | Encrypted? | Format/Notes                |
|----------------|-----------------------------------------|------------|-----------------------------|
| `bunker.cfg`   | Main vault config (legacy/compat)       | Yes        | AES-GCM, full file          |
| `bunker.mmf`   | Encrypted password/notes database       | Yes        | AES-GCM, full file          |
| `bunker.salt`  | Per-user salt for key derivation        | No         | 32 bytes random, binary (strict permissions 0600) |
| `config.cfg`   | UI/UX settings (attempts, timeout, etc) | Yes        | AES-GCM, full file          |


- **Encrypted Files:** `bunker.cfg`, `bunker.mmf`, and `config.cfg` are fully encrypted using AES-GCM with keys derived from the master password and/or UI_KEY. No plaintext secrets are stored.
- **Salt File:** `bunker.salt` is a raw, random 32-byte file used for key derivation. It is not encrypted, but is required for decryption. As of this patch, it is written with strict permissions (0600) so only the file owner can access it.


---


## 3. Login/Setup Flow (as of Patch)


1. **User initiates setup.**
2. **UI_KEY is generated and stored securely.**
  - If storage fails, setup aborts.
3. **User sets and confirms master password.**
4. **bunker.salt is generated and written atomically.**
5. **Key is derived from password + salt.**
6. **UI config is saved, encrypted with UI_KEY.**
7. **Main config (`bunker.cfg`) is saved, encrypted with derived key.**
8. **Empty database (`bunker.mmf`) is initialized and encrypted.**
9. **Setup completes.**


- **On login:**
 - UI_KEY is loaded from secure storage.
 - Salt is loaded from `bunker.salt`.
 - User enters password; key is derived.
 - Config and database are decrypted using the derived key and UI_KEY.


---


## 4. Migration & Compatibility
- Migration from legacy config is supported (not covered in this patch).
- Only the login/setup flow is updated; other features (change password, settings, etc.) may still use legacy logic and should be updated in future patches.


---


## 5. Security Best Practices Followed
- All sensitive files are encrypted at rest (except salt).
- Atomic file writes and permission enforcement.
- Strict error handling and abort on failure.
- No debug/info logs with sensitive data.
- Clear separation of key management and config logic.


---


## 6. Next Steps
- Update all feature flows (change password, settings, etc.) to use the new UI_KEY and atomic file logic.
- Add/expand tests for new logic.
- Review and update documentation as features are migrated.


---


*This document should be updated as further changes are made to the vault’s security model or file structure.*



