
# BUNKER 2.0: Your Digital Fortress (Terminal Edition)

**Free and source-available.** See [`LICENSE.txt`](/Read%20Me/LICENSE.txt) for what the license allows.

> **Tip:** run BUNKER in a full-screen terminal window.
<img width="1005" height="632" alt="och9kko23oufm3ny21w8hakint5x" src="https://github.com/user-attachments/assets/a64ccb84-0806-4e09-9270-c1bfc997a17b" />

---

## 🛡️ About BUNKER 2.0
*Offline, Encrypted Local Vault*

BUNKER 2.0 is a locally-stored, offline password and notes manager built with privacy-first principles. Your vault is encrypted with **AES-256-GCM** and never leaves your device.

**Demo video:** https://youtu.be/DxMICmnFs_Y

**Key Features:**
- **AES-256-GCM encryption** - key derived from your master password with Argon2id + PBKDF2
- **100% Local Storage** - No cloud, no tracking, no data mining
- **Desktop and mobile interfaces** - BUNKER picks the interface for your device and asks you to confirm
- **Auto-Logout Timer** - Configurable inactivity protection
- **Password Generator** - Create strong random passwords instantly
- **Encrypted Notes** - Secure storage for sensitive information
- **Encrypted Export/Import** - Back up profiles and notes with a passphrase
- **Clipboard Auto-Clear** - Copied passwords and notes are cleared after 30 seconds and when BUNKER closes
- **IP Display Toggle** - Optionally show your public IP
- **Failed-Login Limit** - Too many wrong master passwords wipes the vault

<img width="1005" height="648" alt="jl4s88eza1rti5bd10d4504bqk7n" src="https://github.com/user-attachments/assets/37696825-96c5-47f4-9b94-0b7baf19578f" />

---

## 🐍 Installing Python 3

To run this project, you need Python 3 installed on your system:

### 1. Visit Python.org
Go to the Python download page: https://www.python.org/downloads/

### 2. Select the Version
Download the latest stable version of Python 3 (recommended). BUNKER needs **Python 3.10 or newer**.

### 3. Choose Your Installer
- **Windows:** Download the executable installer (`.exe`)
- **macOS:** Download the macOS installer (`.pkg`) 
- **Linux:** Use your package manager (`apt`, `yum`, `dnf`) or download source files

### 4. Run the Installer
Execute the downloaded installer and follow the setup instructions.

---

## 🚀 BUNKER 2.0 Setup Instructions

### Step 1: Navigate to BUNKER2.0 Folder

Open a terminal and go to the BUNKER2.0 folder (adjust the path to wherever you saved it):

```bash
cd ~/Desktop/BUNKER2.0
```

### Step 2: Install Required Packages

**Required Dependencies:**
- `cryptography` - **AES-256 encryption library**
- `pyperclip` - Secure clipboard management
- `psutil` - System information monitoring
- `requests` - Network utilities
- `argon2-cffi` - **Argon2 key derivation library** NEW

**Installation Command** (run it inside the `BUNKER2.0` folder):
```bash
pip install -r requirements.txt
```

---

## 🔧 Troubleshooting

**Import Errors:**
If you encounter import errors on first run, install missing packages:
```bash
pip install [missing_package_name]
```


### Step 3: Launch BUNKER 2.0

```bash
python3 BUNKER.py
```

On first run BUNKER walks you through creating a new vault and master password (at least 8 characters). After that you'll reach the BUNKER ACCESS page each time you launch.

**Your vault files** live in the folder you run BUNKER from: `Bunker.mmf` (encrypted vault), `bunker.salt` and `bunker.cfg`. You need all of them to open the vault. They are git-ignored so you can't commit them by accident.

### Plain output (no colours)

BUNKER follows the [NO_COLOR](https://no-color.org) convention. To turn
colours off, for example for a screen reader or a log, set `NO_COLOR`:

```bash
NO_COLOR=1 python3 BUNKER.py
```

### Running the tests

```bash
python3 -m unittest discover -s tests -t .
```

---

## 💻 Security Features

**Encryption:**
- Passwords and notes are encrypted with AES-256-GCM
- The key is derived from your master password and a random 32-byte salt using Argon2id, then PBKDF2-HMAC-SHA3-256
- The master password is never stored; it is checked by decrypting a verifier

**Self-Destruct:**
- The vault is overwritten and deleted after the maximum number of failed logins
- No recovery possible - intentional "burner vault" design. Keep an encrypted export as a backup.

**Auto-Protection:**
- Configurable auto-logout (10-3600 seconds, or off)
- Clipboard auto-clear after 30 seconds and on exit (only if it still holds what BUNKER copied)
- Passwords and notes are shown only when you ask to view them

---

**What BUNKER protects against, and what it doesn't:** see the
[threat model](/docs/THREAT_MODEL.md). In short, the failed-login limit stops
casual guessing at your keyboard, but a copy of your vault files can be
attacked offline, so use a long master password.

---

## 📚 User Guide

Access the complete User Guide from the 🏚️ **MAIN MENU** 🏚️ for detailed information on all features and security settings.

---

## ⚠️ Important Disclaimer

This application is built for **educational purposes**. Use BUNKER 2.0 at your own risk. It is provided as-is, and neither the creator nor contributors take responsibility for any damage or loss incurred through its use.

**Security Note:** Plain-text export writes your data unencrypted - prefer encrypted export, and keep backups of critical data.



**Other Issues:**
If you run into other errors, email **support@zeromarks.net**. To report a security issue, use the same address and please do not open a public issue.

---

## 🌐 Connect with ZeroMarks LLC

**Official Channels:**
- **Website:** [zeromarks.net](http://www.zeromarks.net)
- **YouTube:** [@ZEROMARKSLLC](https://www.youtube.com/@ZEROMARKSLLC)
- **GitHub:** [github.com/ZeroMarks](https://github.com/ZeroMarks)
- **Reddit:** [r/zeromarksllc](https://www.reddit.com/r/zeromarksllc)

**Social Media:**
- **Twitter/X:** [@zeromarksvpn](https://x.com/zeromarksvpn)
- **TikTok:** [@zeromarksllc](https://www.tiktok.com/@zeromarksllc)
- **Instagram:** [@zeromarksllc](https://www.instagram.com/zeromarksllc)
- **Facebook:** [ZeroMarks LLC](https://www.facebook.com/zeromarksllc)

---

## 📅 Project Timeline

**Development Started:** May 10, 2024  
**Version 2.0 Completed:** June 20, 2024  
**Latest Update:** v2.0 security hardening - see [RELEASE_NOTES_v2.0.md](/RELEASE_NOTES_v2.0.md)

**Created by:** @RIX (ZeroMarks LLC Founder)

---

## 🚀 Coming Soon

- **ZeroMarks VPN** - No-logs VPN service
- **Crypto Wallet Manager** - Secure cryptocurrency key storage
- **Enhanced Brute-Force Protection** - Advanced security improvements

---

*Support privacy-first technology. Support ZeroMarks LLC.*
