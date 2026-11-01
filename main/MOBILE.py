import json, sys, time, os


from main.SHARED_RESOURCES_MOBILE import (L_CYAN, BUNKER, DBLUE,
FORANGE, FBLUE, FRED, GOLD, GREEN, RED, RESET, DPURPLE,
MUSTARD, VINTAGE, LPURPLE, PURPLE, CYAN)

from main.SHARED_RESOURCES_MOBILE import clear_screen
from main.SECURE_IO import copy_secret, copy_notice, reveal_secret, safe_error
from main import VAULT_STORE as store

from main.SHARED_RESOURCES_MOBILE import (
    vault, save_ui_config, load_ui_config, load_salt,
    timeoutInput, timeout_getpass, timeoutGlobalCode, timeoutCleanup,
    secure_cleanup_common, KEY_SIZE, SALT_SIZE,vaultSetup,
)

# The mobile UI works on the same Bunker.mmf as the desktop UI: one flat dict
# {entry_id: entry}, entries written by main.VAULT_STORE in the desktop
# encoding. Mapping of the mobile menus onto desktop entry kinds:
#   Notes             -> desktop notes (title/content/tags/favorite/private)
#   Accounts/Passwords-> desktop profiles (domain/username/email/password)
#   Profile           -> the same desktop profiles, identity details only
#                        (domain/username/email/favorite; never the password)
# There is no separate "account" or "personal profile" record on disk.


BUNKER_ASCII = """ test"""
def title_with_label(device_type='mobile'):
    # Just use the provided device type
    device_labels = {
        'mobile': 'Mobile Phone',
        'tablet': 'Tablet',
        'desktop': 'Desktop/Laptop',
        'other': 'Other Device'
    }
    display_type = device_labels.get(device_type, device_type)

    BUNKER_ASCII = rf"""
    {FBLUE}
                    )      )       (
    (          ( /(   ( /(       )\ )
    ( )\     (   )\())  )\()) (   (()/(
    )((_)    )\ ((_)\ |((_)\  )\   /(_))
    ((_)_  _ ((_) _((_)|_ ((_)((_) (_)){CYAN}
    | _ )| | | || \| || |/ / | __|| _ \
    | _ \| |_| || .` |  ' <  | _| |   /
    |___/ \___/ |_|\_| _|\_\ |___||_|_\
{RESET}                    {GOLD}« {display_type} UI »{RESET}
    """
    print(BUNKER_ASCII)

subwm_m = rf"""
             {CYAN}PROPERTY OF ZEROMARKSLLC{RESET}
{FBLUE}◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢{RESET}"""
divider_m = rf"""{FBLUE}◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢{RESET}"""
# Modern UI Elements for 2025
class ModernUI:
    @staticmethod
    def header(title):
        clear_screen()
        print(f"\n{CYAN}={'='*50}{RESET}")
        print(f"{PURPLE}{title:^50}{RESET}")
        print(f"{CYAN}={'='*50}{RESET}\n")

    @staticmethod
    def menu_item(key, description):
        print(f"{GOLD}[{key}]{RESET} {VINTAGE}{description}{RESET}")

    @staticmethod
    def input_prompt(prompt):
        return input(f"{L_CYAN}{prompt}: {RESET}")

    @staticmethod
    def success_message(msg):
        print(f"\n{GREEN}✓ {msg}{RESET}")
        time.sleep(1)

    @staticmethod
    def error_message(msg):
        print(f"\n{RED}✗ {msg}{RESET}")
        time.sleep(1)

    @staticmethod
    def confirmation_prompt(prompt):
        return input(f"{MUSTARD}{prompt} (y/n): {RESET}").lower() == 'y'


# UI Implementation for different views
class VaultUI:
    def __init__(self, device_type='mobile'):
        self.device_type = device_type
        self.ui = ModernUI()

    def main_menu(self):
        self.ui.header('BUNKER Vault')
        if self.device_type == 'mobile':
            self.ui.menu_item('1', '📝 Notes')
            self.ui.menu_item('2', '🔑 Accounts')
            self.ui.menu_item('3', '👤 Profile')
            self.ui.menu_item('4', '⚙️ Settings')
            self.ui.menu_item('0', '🚪 Exit')
        else:
            # Desktop-style menu
            self.ui.menu_item('1', 'Manage Notes')
            self.ui.menu_item('2', 'Manage Accounts')
            self.ui.menu_item('3', 'Profile Settings')
            self.ui.menu_item('4', 'System Settings')
            self.ui.menu_item('0', 'Exit')




def main(device_type='mobile'):
    # Initialize UI
    clear_screen()

    # Get UI configuration
    ui_config = load_ui_config()
    current_timeout = ui_config["current_timeout"]

    # First check if vault exists
    if not os.path.exists(store.DB_FILE):
        #check_terminal_size()
        clear_screen()
        title_with_label(device_type)
        print(subwm_m)
        print(f"{CYAN}\nBUNKER SETUP\n\nWelcome to Bunker!\n\n{GOLD}Detected device type: {device_type}{RESET}\n\n{RED}ALERT: Bunker.mmf was not found in local directory... SETUP A NEW PASSWORD!{RESET}")
        # Perform vault setup
        if not vaultSetup():
            return  # Return if setup was cancelled or failed
        if not os.path.exists(store.DB_FILE):
            print(f"{RED}Failed to create vault file. Cannot proceed.{RESET}")
            return
        ui_config = load_ui_config()
        current_timeout = ui_config["current_timeout"]

    # Initialize vault with user input
    clear_screen()
    salt = load_salt()
    if not salt:
        print(f"{RED}Failed to load salt. Cannot proceed.{RESET}")
        return

    # Handle login process (shared, persistent attempt counter)
    from main.INITIALIZE import vault as login_vault
    from main.VAULT_FILES import try_password
    vault_ui = VaultUI(device_type)
    ui_config = load_ui_config()
    attempts = ui_config.get("attempts", 0)
    max_attempts = ui_config.get("max_attempts", 3)
    vault_key = None

    while attempts < max_attempts:
        clear_screen()
        title_with_label(device_type)
        print(f"{CYAN}BUNKER ACCESS{RESET}")
        print(divider_m)
        print(PURPLE + f"Attempt {attempts} of {max_attempts}" + RESET)
        print(f"{GOLD}Security clearance required! {RESET}")

        user_cmd = input(f"{GOLD}Do you want to show your password? (y/n) or exit(e): {RESET}").lower()

        if user_cmd == timeoutGlobalCode:
            timeoutCleanup()
            return

        if user_cmd == "e":
            clear_screen()
            print(BUNKER_ASCII)
            print(subwm_m)
            print(f"{GREEN}Exiting...{RESET}")
            return

        if user_cmd not in ["y", "n"]:
            print(f"{RED} ** ALERT: Invalid input. Please enter y, n, or e. **{RESET}")
            continue

        try:
            # Get master password based on user preference
            if user_cmd == "y":
                master_pass = timeoutInput(f"{GOLD}Enter the bunker access code to proceed: {RESET}", timeout=current_timeout)
            else:  # user_cmd == "n"
                master_pass = timeout_getpass(f"{GOLD}Enter the bunker access code to proceed: {RESET}", current_timeout)
        except Exception as e:
            # EOF, timeout or input error: not a password attempt.
            vault_ui.ui.error_message(f"Login cancelled: {safe_error(e)}")
            return
        if not master_pass or master_pass == timeoutGlobalCode:
            return  # nothing entered: not an attempt

        # Same rules as the desktop login (VAULT_FILES.try_password): only a
        # wrong password counts, damaged files never do, and the counter is
        # the shared one, so switching interface does not reset it. Mobile
        # never destroys anything itself.
        try:
            status, key = try_password(master_pass, login_vault)
        except Exception as e:
            vault_ui.ui.error_message(f"Could not check the password: {safe_error(e)}")
            return
        if status == "ok":
            ui_config["attempts"] = 0
            save_ui_config(ui_config)
            vault_key = key
            break
        if status != "wrong":
            vault_ui.ui.error_message(
                "The vault files are missing, damaged or out of step. "
                "No login attempt was counted.")
            return
        ui_config["attempts"] = ui_config.get("attempts", 0) + 1
        save_ui_config(ui_config)
        attempts = ui_config["attempts"]
        vault_ui.ui.error_message("Incorrect access password.")

    if not vault_key:
        vault_ui.ui.error_message("Maximum login attempts exceeded")
        return

    # Main loop
    while True:
        vault_ui.main_menu()
        choice = vault_ui.ui.input_prompt("Select option")

        if choice == '0':
            vault_ui.ui.success_message("Thank you for using BUNKER!")
            break
        elif choice == '1':
            mobile_note_manager(vault_key, device_type)
        elif choice == '2':
            mobile_password_manager(vault_key, device_type)
        elif choice == '3':
            mobile_profile_manager(vault_key, device_type)
        elif choice == '4':
            # Settings menu
            vault_ui.ui.header("Settings")
            vault_ui.ui.menu_item('1', 'Change Device Type')
            vault_ui.ui.menu_item('2', 'Security Settings')
            vault_ui.ui.menu_item('0', 'Back')

            settings_choice = vault_ui.ui.input_prompt("Select a setting")
            if settings_choice == '1':
                # Let user select device type manually
                vault_ui.ui.header("Device Selection")
                vault_ui.ui.menu_item('1', '📱 Mobile Phone')
                vault_ui.ui.menu_item('2', '📱 Tablet')
                vault_ui.ui.menu_item('3', '💻 Desktop/Laptop')
                vault_ui.ui.menu_item('4', '🔧 Other')

                device_choice = vault_ui.ui.input_prompt("Select your device type")
                device_map = {
                    '1': 'mobile',
                    '2': 'tablet',
                    '3': 'desktop',
                    '4': 'other'
                }
                new_device_type = device_map.get(device_choice, 'mobile')
                if save_device_preference(new_device_type):
                    vault_ui.ui.success_message(f"Device type updated to {new_device_type}")
                    vault_ui.device_type = new_device_type
            elif settings_choice == '2':
                vault_ui.ui.header("Security Settings")
                vault_ui.ui.menu_item('1', 'Change Master Password')
                vault_ui.ui.menu_item('0', 'Back')
                security_choice = vault_ui.ui.input_prompt("Select option")
                if security_choice == '1':
                    # Same, tested implementation as desktop: re-encrypts
                    # every field and swaps the files together, keeping the
                    # old ones until all writes succeed. Logs out on success.
                    from main.INITIALIZE import changeMasterPassword, loadDatabase
                    changeMasterPassword(vault_key, loadDatabase(vault_key))
        else:
            vault_ui.ui.error_message("Invalid option")


# ---------------------------------------------------------------------------
# Shared helpers for the managers. Every change reloads Bunker.mmf, applies
# one edit and saves atomically (store.modify), so nothing is held in memory
# between actions and entries this UI does not understand are never touched.
# ---------------------------------------------------------------------------

UNREADABLE = "[unreadable]"
END_MARKER = ".done"


def _entries(hashed_pass, kind):
    """[(entry_id, entry)] of one kind, in file order."""
    test = store.is_note if kind == "note" else store.is_profile
    return [(i, e) for i, e in store.load(hashed_pass).items() if test(e)]


def _safe(fn, *args):
    try:
        return fn(*args)
    except Exception:
        return UNREADABLE


def _note_label(entry, hashed_pass):
    title = _safe(store.dec, entry, "title", hashed_pass)
    flags = ("★ " if entry.get("favorite") else "") + ("[private] " if entry.get("private") else "")
    return f"{flags}{title}"


def _profile_label(entry, hashed_pass):
    domain = _safe(store.dec, entry, "domain", hashed_pass)
    user = _safe(store.dec, entry, "username", hashed_pass)
    star = "★ " if entry.get("favorite") else ""
    return f"{star}{domain}  ({user})"


def _pick(ui, items, label_fn, prompt):
    """List ``items`` and return the chosen (id, entry), or None."""
    for n, (_, entry) in enumerate(items, 1):
        print(f"{GOLD}[{n}]{RESET} {label_fn(entry)}")
    raw = ui.input_prompt(prompt)
    try:
        idx = int(raw) - 1
    except ValueError:
        ui.error_message("Invalid input")
        return None
    if not 0 <= idx < len(items):
        ui.error_message("Invalid number")
        return None
    return items[idx]


def _read_multiline(ui):
    print(f"{L_CYAN}Enter text. Finish with a line containing only {END_MARKER} (or Ctrl+D / Ctrl+Z):{RESET}")
    lines = []
    try:
        while True:
            line = input()
            if line.strip() == END_MARKER:
                break
            lines.append(line)
    except EOFError:
        pass
    return "\n".join(lines)


def _yes_no(ui, prompt, default=None):
    """True/False for y/n; ``default`` for an empty answer (None = no default)."""
    while True:
        ans = input(f"{MUSTARD}{prompt}: {RESET}").strip().lower()
        if ans == "" and default is not None:
            return default
        if ans in ("y", "n"):
            return ans == "y"
        ui.error_message("Please enter y or n")


def _split_tags(raw):
    return [t.strip() for t in raw.split(",") if t.strip()]


def _run(ui, action, ok_message=None):
    """Run one action; report failure by class name only. Never deletes or
    wipes anything: a failed save leaves Bunker.mmf as it was."""
    try:
        result = action()
    except Exception as e:
        ui.error_message(f"Could not complete that: {safe_error(e)}")
        return False
    if ok_message:
        ui.success_message(ok_message)
    return True if result is None else result


def mobile_note_manager(hashed_pass, device_type='mobile'):
    """Mobile-friendly note management view (desktop notes)."""
    ui = ModernUI()
    emoji = device_type == 'mobile'

    def notes():
        return _entries(hashed_pass, "note")

    def pick_note(prompt):
        items = notes()
        if not items:
            ui.error_message("No notes found")
            return None
        ui.header("Your Notes")
        return _pick(ui, items, lambda e: _note_label(e, hashed_pass), prompt)

    def view_note():
        picked = pick_note("Enter note number to view")
        if not picked:
            return
        _, entry = picked
        data = store.read_note(entry, hashed_pass)
        if data["private"] and input(
                f"{GOLD}This is a private note. Type 'view' to show it: {RESET}").strip().lower() != "view":
            return
        ui.header(data["title"])
        print(f"{CYAN}Tags:{RESET} {', '.join(data['tags'])}")
        reveal_secret("", data["content"])
        input(f"\n{VINTAGE}Press Enter to continue...{RESET}")

    def add_note():
        ui.header("Add New Note")
        title = ui.input_prompt("Enter note title")
        if not title.strip():
            ui.error_message("A title is required")
            return
        content = _read_multiline(ui)
        private = _yes_no(ui, "Mark as private? (y/n)", default=False)
        tags = [] if private else _split_tags(ui.input_prompt("Tags, comma separated (or Enter for none)"))
        favorite = _yes_no(ui, "Add to favorites? (y/n)", default=False)
        entry = store.make_note(title, content, hashed_pass, tags=tags,
                                favorite=favorite, private=private)
        store.modify(hashed_pass, lambda db: db.__setitem__(store.new_id(), entry))
        ui.success_message("Note added successfully")

    def edit_note():
        picked = pick_note("Enter note number to edit")
        if not picked:
            return
        note_id, entry = picked
        cur = store.read_note(entry, hashed_pass)
        fields = {}
        title = ui.input_prompt("Enter new title (or Enter to keep current)")
        if title.strip():
            fields["title"] = title
        if _yes_no(ui, "Replace the content? (y/n, Enter = no)", default=False):
            fields["content"] = _read_multiline(ui)
        private = _yes_no(ui, f"Private? (y/n, Enter = keep {'y' if cur['private'] else 'n'})", default=cur["private"])
        fields["private"] = private
        if not private:
            raw = ui.input_prompt("New tags, comma separated (or Enter to keep current)")
            if raw.strip():
                fields["tags"] = _split_tags(raw)
            elif cur["private"]:
                fields["tags"] = []  # leaving private: PRIVATE tag no longer applies
            else:
                fields.pop("tags", None)
        fields["favorite"] = _yes_no(ui, f"Favorite? (y/n, Enter = keep {'y' if cur['favorite'] else 'n'})", default=cur["favorite"])

        def apply(db):
            if note_id not in db:
                raise KeyError(note_id)
            db[note_id] = store.update_note(db[note_id], hashed_pass, **fields)
        store.modify(hashed_pass, apply)
        ui.success_message("Note updated successfully")

    def delete_note():
        picked = pick_note("Enter note number to delete")
        if not picked:
            return
        note_id, _ = picked
        if not ui.confirmation_prompt("Are you sure you want to delete this note?"):
            return
        store.modify(hashed_pass, lambda db: db.pop(note_id, None))
        ui.success_message("Note deleted successfully")

    actions = {'1': view_note, '2': add_note, '3': edit_note, '4': delete_note}
    labels = [('1', '📄 View Notes' if emoji else 'View Notes'),
              ('2', '➕ Add Note' if emoji else 'Add Note'),
              ('3', '✏️ Edit Note' if emoji else 'Edit Note'),
              ('4', '🗑️ Delete Note' if emoji else 'Delete Note'),
              ('0', '↩️ Back' if emoji else 'Back')]
    while True:
        ui.header("Note Manager")
        for key, text in labels:
            ui.menu_item(key, text)
        choice = ui.input_prompt("Select option")
        if choice == '0':
            break
        if choice in actions:
            _run(ui, actions[choice])
        else:
            ui.error_message("Invalid option")


def mobile_password_manager(hashed_pass, device_type='mobile'):
    """Mobile-friendly password view. Operates on desktop profiles
    (domain, username, email, password, favorite)."""
    ui = ModernUI()
    emoji = device_type == 'mobile'

    def pick_profile(prompt, title="Your Passwords"):
        items = _entries(hashed_pass, "profile")
        if not items:
            ui.error_message("No passwords stored")
            return None
        ui.header(title)
        return _pick(ui, items, lambda e: _profile_label(e, hashed_pass), prompt)

    def view_passwords():
        picked = pick_profile("Enter number to view (details only)")
        if not picked:
            return
        data = store.read_profile(picked[1], hashed_pass)
        print(f"\n{CYAN}Site:{RESET} {data['domain']}")
        print(f"{CYAN}Username:{RESET} {data['username']}")
        print(f"{CYAN}Email:{RESET} {data['email']}")
        if ui.confirmation_prompt("Show the password on screen?"):
            reveal_secret(f"{CYAN}Password:{RESET} ", data["password"])
        input(f"\n{VINTAGE}Press Enter to continue...{RESET}")

    def add_password():
        ui.header("Add New Password")
        site = ui.input_prompt("Enter website/service name")
        if not site.strip():
            ui.error_message("A site name is required")
            return
        username = ui.input_prompt("Enter username (or Enter for none)")
        email = ui.input_prompt("Enter email (or Enter for none)")
        password = timeout_getpass(f"{L_CYAN}Enter password: {RESET}")
        if not password:
            ui.error_message("A password is required")
            return
        favorite = _yes_no(ui, "Add to favorites? (y/n)", default=False)
        entry = store.make_profile(site, username.strip(), email.strip(), password,
                                   hashed_pass, favorite=favorite)
        store.modify(hashed_pass, lambda db: db.__setitem__(store.new_id(), entry))
        ui.success_message("Password added successfully")

    def edit_password():
        picked = pick_profile("Enter password number to edit", "Edit Password")
        if not picked:
            return
        pid, _ = picked
        site = ui.input_prompt("Enter new site name (or Enter to keep current)")
        username = ui.input_prompt("Enter new username (or Enter to keep current)")
        email = ui.input_prompt("Enter new email (or Enter to keep current)")
        password = timeout_getpass(f"{L_CYAN}Enter new password (or Enter to keep current): {RESET}")
        fields = {k: v.strip() for k, v in
                  (("domain", site), ("username", username), ("email", email)) if v.strip()}
        if password:
            fields["password"] = password

        def apply(db):
            if pid not in db:
                raise KeyError(pid)
            db[pid] = store.update_profile(db[pid], hashed_pass, **fields)
        store.modify(hashed_pass, apply)
        ui.success_message("Password updated successfully")

    def delete_password():
        picked = pick_profile("Enter password number to delete", "Delete Password")
        if not picked:
            return
        pid, _ = picked
        if not ui.confirmation_prompt("Are you sure you want to delete this password?"):
            return
        store.modify(hashed_pass, lambda db: db.pop(pid, None))
        ui.success_message("Password deleted successfully")

    def copy_password():
        picked = pick_profile("Enter password number to copy", "Copy Password")
        if not picked:
            return
        password = store.dec(picked[1], "password", hashed_pass)
        # Cleared after 30 s or on exit, like the desktop UI.
        if copy_secret(password):
            ui.success_message(copy_notice("Password"))
        else:
            ui.error_message("Could not access the clipboard")

    actions = {'1': view_passwords, '2': add_password, '3': edit_password,
               '4': delete_password, '5': copy_password}
    labels = [('1', '🔑 View Passwords' if emoji else 'View Passwords'),
              ('2', '➕ Add Password' if emoji else 'Add Password'),
              ('3', '✏️ Edit Password' if emoji else 'Edit Password'),
              ('4', '🗑️ Delete Password' if emoji else 'Delete Password'),
              ('5', '📋 Copy Password' if emoji else 'Copy Password'),
              ('0', '↩️ Back' if emoji else 'Back')]
    while True:
        ui.header("Password Manager")
        for key, text in labels:
            ui.menu_item(key, text)
        choice = ui.input_prompt("Select option")
        if choice == '0':
            break
        if choice in actions:
            _run(ui, actions[choice])
        else:
            ui.error_message("Invalid option")


def mobile_profile_manager(hashed_pass, device_type='mobile'):
    """Profile view: the identity side (site, username, email, favorite) of
    the same desktop profiles the password manager edits. The password is
    never shown or changed here."""
    ui = ModernUI()
    emoji = device_type == 'mobile'

    def pick_profile(prompt, title="Your Profiles"):
        items = _entries(hashed_pass, "profile")
        if not items:
            ui.error_message("No profile found")
            return None
        ui.header(title)
        return _pick(ui, items, lambda e: _profile_label(e, hashed_pass), prompt)

    def view_profile():
        picked = pick_profile("Enter number to view")
        if not picked:
            return
        data = store.read_profile(picked[1], hashed_pass)
        print(f"\n{CYAN}Site:{RESET} {data['domain']}")
        print(f"{CYAN}Username:{RESET} {data['username']}")
        print(f"{CYAN}Email:{RESET} {data['email']}")
        print(f"{CYAN}Favorite:{RESET} {'yes' if data['favorite'] else 'no'}")
        input(f"\n{VINTAGE}Press Enter to continue...{RESET}")

    def add_profile():
        # Desktop profiles always carry a password, so adding one here asks for it.
        ui.header("Add Profile")
        site = ui.input_prompt("Enter site/service name")
        if not site.strip():
            ui.error_message("A site name is required")
            return
        username = ui.input_prompt("Enter your username (or Enter for none)")
        email = ui.input_prompt("Enter your email (or Enter for none)")
        password = timeout_getpass(f"{L_CYAN}Enter password: {RESET}")
        if not password:
            ui.error_message("A password is required")
            return
        entry = store.make_profile(site, username.strip(), email.strip(), password, hashed_pass)
        store.modify(hashed_pass, lambda db: db.__setitem__(store.new_id(), entry))
        ui.success_message("Profile added successfully")

    def edit_profile():
        picked = pick_profile("Enter profile number to edit", "Edit Profile")
        if not picked:
            return
        pid, _ = picked
        site = ui.input_prompt("Enter new site (or Enter to keep current)")
        username = ui.input_prompt("Enter new username (or Enter to keep current)")
        email = ui.input_prompt("Enter new email (or Enter to keep current)")
        fields = {k: v.strip() for k, v in
                  (("domain", site), ("username", username), ("email", email)) if v.strip()}

        def apply(db):
            if pid not in db:
                raise KeyError(pid)
            db[pid] = store.update_profile(db[pid], hashed_pass, **fields)
        store.modify(hashed_pass, apply)
        ui.success_message("Profile updated successfully")

    def toggle_favorite():
        picked = pick_profile("Enter profile number to star/unstar", "Favorites")
        if not picked:
            return
        pid, entry = picked
        now = not bool(entry.get("favorite", False))

        def apply(db):
            if pid not in db:
                raise KeyError(pid)
            db[pid] = store.update_profile(db[pid], hashed_pass, favorite=now)
        store.modify(hashed_pass, apply)
        ui.success_message("Added to favorites" if now else "Removed from favorites")

    actions = {'1': view_profile, '2': add_profile, '3': edit_profile, '4': toggle_favorite}
    labels = [('1', '👤 View Profile' if emoji else 'View Profile'),
              ('2', '➕ Add Profile' if emoji else 'Add Profile'),
              ('3', '✏️ Edit Profile' if emoji else 'Edit Profile'),
              ('4', '⭐ Favorite / Unfavorite' if emoji else 'Favorite / Unfavorite'),
              ('0', '↩️ Back' if emoji else 'Back')]
    while True:
        ui.header("Profile Management")
        for key, text in labels:
            ui.menu_item(key, text)
        choice = ui.input_prompt("Select option")
        if choice == '0':
            break
        if choice in actions:
            _run(ui, actions[choice])
        else:
            ui.error_message("Invalid option")


def save_device_preference(device_type):
    """Save device preference with enhanced error handling"""
    vault_ui = VaultUI(device_type)
    try:
        # Validate device type
        if device_type not in ['mobile', 'tablet', 'desktop', 'other']:
            raise ValueError(f"Invalid device type: {device_type}")

        # Load existing config or create new one
        try:
            ui_config = load_ui_config()
        except Exception:
            ui_config = {
                "device_type": device_type,
                "current_timeout": 60,
                "max_attempts": 3,
                "attempts": 0,
                "disable_ipv4": True
            }

        # Update device type
        ui_config['device_type'] = device_type
        save_ui_config(ui_config)

        return True

    except Exception as e:
        vault_ui.ui.error_message(f"Failed to save device preference: {safe_error(e)}")
        return False


def mobile_feature_select(hashed_pass, device_type='mobile'):
    """Mobile-friendly feature selection view"""
    vault_ui = VaultUI(device_type)
    try:
        while True:
            vault_ui.ui.header("Select Feature")
            if device_type == 'mobile':
                vault_ui.ui.menu_item('1', '🔐 Password Manager')
                vault_ui.ui.menu_item('2', '📝 Note Manager')
                vault_ui.ui.menu_item('3', '👤 Profile Settings')
                vault_ui.ui.menu_item('0', '🚪 Exit')
            else:
                vault_ui.ui.menu_item('1', 'Password Manager')
                vault_ui.ui.menu_item('2', 'Note Manager')
                vault_ui.ui.menu_item('3', 'Profile Settings')
                vault_ui.ui.menu_item('0', 'Exit')

            choice = vault_ui.ui.input_prompt("Select option")

            if choice == '1':
                mobile_password_manager(hashed_pass, device_type)
            elif choice == '2':
                mobile_note_manager(hashed_pass, device_type)
            elif choice == '3':
                mobile_profile_manager(hashed_pass, device_type)
            elif choice == '0':
                vault_ui.ui.success_message("Goodbye!")
                break
            else:
                vault_ui.ui.error_message("Invalid option")

    except Exception as e:
        vault_ui.ui.error_message(f"An error occurred: {safe_error(e)}")
        return False
    return True


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting safely...")
    finally:
        secure_cleanup_common()
