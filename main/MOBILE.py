
import base64, json, secrets, sys, uuid, pyperclip, os, time, getpass
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from main.SHARED_RESOURCES_MOBILE import (L_CYAN, BUNKER, DBLUE, 
FORANGE, FBLUE, FRED, GOLD, GREEN, RED, RESET, DPURPLE,
MUSTARD, VINTAGE, LPURPLE, PURPLE, CYAN)

from main.SHARED_RESOURCES_MOBILE import clear_screen, ModernUI
from main.SECURE_IO import copy_secret, copy_notice, reveal_secret, safe_error

from main.SHARED_RESOURCES_MOBILE import (
    vault, save_ui_config, load_ui_config, load_salt,
    timeoutInput, timeout_getpass, timeoutGlobalCode, timeoutCleanup,
    secure_cleanup_common, KEY_SIZE, SALT_SIZE,vaultSetup,
)


BUNKER_ASCII = """ test"""
def title_with_label(device_type='mobile'):
    # Just use the provided device type, no detection needed
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

def mobile_setup_view():
    """Mobile-friendly vault setup view"""
    try:
        clear_screen()
        print(BUNKER_ASCII)
        print(f"{CYAN}Welcome to BUNKER Mobile Setup{RESET}\n")
        
        # Check if vault exists
        try:
            with open("bunker.mmf", "rb"):
                print(f"{GREEN}✓ Existing vault detected{RESET}")
                return load_salt()
        except FileNotFoundError:
            print(f"{MUSTARD}⚠ No vault found - Let's set up a new one{RESET}")
            return vaultSetup()
            
    except Exception as e:
        print(f"{RED}✗ Setup failed: {safe_error(e)}{RESET}")
        return None



def main(device_type='mobile'):
    # Initialize UI
    clear_screen()

    # Get UI configuration
    ui_config = load_ui_config()
    attempts = ui_config["attempts"]
    max_attempts = ui_config["max_attempts"]
    disable_ipv4 = ui_config["disable_ipv4"]
    current_timeout = ui_config["current_timeout"]
    
    # First check if vault exists
    try:
        with open("Bunker.mmf", "rb") as f:
            encrypted_contents = f.read()
    except FileNotFoundError:
        #check_terminal_size()
        clear_screen()
        title_with_label(device_type)
        print(subwm_m)
        print(f"{CYAN}\nBUNKER SETUP\n\nWelcome to Bunker!\n\n{GOLD}Detected device type: {device_type}{RESET}\n\n{RED}ALERT: Bunker.mmf was DESTROYED or not found in local directory... SETUP A NEW PASSWORD!{RESET}")
        # Perform vault setup
        if not vaultSetup():
            return  # Return if setup was cancelled or failed
            
        # Try to read the newly created vault
        try:
            with open("Bunker.mmf", "rb") as f:
                encrypted_contents = f.read()
        except FileNotFoundError:
            print(f"{RED}Failed to create vault file. Cannot proceed.{RESET}")
            return
    
    # Get current timeout value
        ui_config = load_ui_config()
        attempts = ui_config["attempts"]
        max_attempts = ui_config["max_attempts"]
        disable_ipv4 = ui_config["disable_ipv4"]
        current_timeout = ui_config["current_timeout"]

    # First check if vault exists
    try:
        with open("Bunker.mmf", "rb"):
            pass
    except FileNotFoundError:
        #check_terminal_size()
        clear_screen()
        #print(title_art)
        #print(subwm)
        #print(divider)
        print(f"{CYAN}\nBUNKER SETUP\n\nWelcome to Bunker!\n\n{RED}ALERT: Bunker.mmf was DESTROYED or not found in local directory... SETUP A NEW PASSWORD!{RESET}")
        # Perform vault setup
        if not vaultSetup():
            return  # Return if setup was cancelled or failed
    
    # Initialize vault with user input
    clear_screen()
    salt = load_salt()
    if not salt:
        print(f"{RED}Failed to load salt. Cannot proceed.{RESET}")
        return

    # Handle login process
    vault_ui = VaultUI(device_type)
    attempts = 0
    max_attempts = 3
    vault_key = None

    while attempts < max_attempts:
        clear_screen()
        title_with_label(device_type)
        print(f"{CYAN}BUNKER ACCESS{RESET}")
        print(divider_m)
        
        if attempts < 3:
            if attempts == 0:
                print(PURPLE + "Attempt 0 of 3" + RESET)
            elif attempts == 1:
                print(PURPLE + "Attempt 1 of 3" + RESET)
            elif attempts == 2:
                print(
                    PURPLE
                    + f"Attempt 2 of 3 {RED}"
                    + RESET
                )
            elif attempts == 3:
                print(
                    PURPLE
                    + f"Attempt 3 of 3 {RED} ** ALERT: Self-destructing after this attempt... **"
                    + RESET
                )
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
                
            if not master_pass:
                attempts += 1
                continue
                
            # Use shared key derivation method
            vault_key = vault.derive_key_hybrid(master_pass, salt, master_pass)  # Using password as pepper like desktop
            break
            
        except Exception as e:
            vault_ui.ui.error_message(f"Login failed: {safe_error(e)}")
            attempts += 1
    
    if not vault_key:
        vault_ui.ui.error_message("Maximum login attempts exceeded")
        return

    # Load initial vault contents
    try:
        with open("Bunker.mmf", "rb") as f:
            encrypted_contents = f.read()
        contents = json.loads(
            vault.decrypt_data(encrypted_contents, vault_key).decode()
        )
    except FileNotFoundError:
        contents = {"profiles": [], "notes": [], "accounts": []}

    # Initialize the UI with detected device type
    vault_ui = VaultUI(device_type)
    
    # Main loop
    while True:
        vault_ui.main_menu()
        choice = vault_ui.ui.input_prompt("Select option")
        
        if choice == '0':
            vault_ui.ui.success_message("Thank you for using BUNKER!")
            break
        elif choice == '1':
            mobile_note_manager(vault_key, contents, device_type)
        elif choice == '2':
            mobile_password_manager(vault_key, contents, device_type)
        elif choice == '3':
            mobile_profile_manager(vault_key, contents, device_type)
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
                    vault_ui.ui.success_message("Master password change not implemented yet")
                    time.sleep(1)
        else:
            vault_ui.ui.error_message("Invalid option")


def mobile_note_manager(hashed_pass, contents, device_type='mobile'):
    """Mobile-friendly note management view"""
    class NotesUI:
        def __init__(self):
            self.ui = ModernUI()
            self.notes = contents.get("notes", [])
            self.device_type = device_type
            
        def display_menu(self):
            self.ui.header("Note Manager")
            if self.device_type == 'mobile':
                self.ui.menu_item('1', '📄 View Notes')
                self.ui.menu_item('2', '➕ Add Note')
                self.ui.menu_item('3', '✏️ Edit Note')
                self.ui.menu_item('4', '🗑️ Delete Note')
                self.ui.menu_item('0', '↩️ Back')
            else:
                self.ui.menu_item('1', 'View Notes')
                self.ui.menu_item('2', 'Add Note')
                self.ui.menu_item('3', 'Edit Note')
                self.ui.menu_item('4', 'Delete Note')
                self.ui.menu_item('0', 'Back')
        
        def show_notes(self):
            if not self.notes:
                self.ui.error_message("No notes found")
                return False
                
            self.ui.header("Your Notes")
            for i, note in enumerate(self.notes, 1):
                title = decode_and_decrypt_secure('title', note, hashed_pass)
                print(f"{GOLD}[{i}]{RESET} {title}")
            return True
        
        def add_note(self):
            self.ui.header("Add New Note")
            title = self.ui.input_prompt("Enter note title")
            print(f"{L_CYAN}Enter note content (press Ctrl+D or Ctrl+Z when done):{RESET}")
            content_lines = []
            
            try:
                while True:
                    line = input()
                    content_lines.append(line)
            except EOFError:
                content = '\n'.join(content_lines)
                
            new_note = {
                "title": encrypt_and_encode_secure(title, hashed_pass),
                "content": encrypt_and_encode_secure(content, hashed_pass),
                "created": time.time()
            }
            
            self.notes.append(new_note)
            contents["notes"] = self.notes
            if vault.save_vault_contents(contents, hashed_pass):
                self.ui.success_message("Note added successfully")
                return True
            return False
        
        def edit_note(self):
            if not self.show_notes():
                return False
            
            idx = int(self.ui.input_prompt("Enter note number to edit")) - 1
            if 0 <= idx < len(self.notes):
                note = self.notes[idx]
                
                title = self.ui.input_prompt("Enter new title (or Enter to keep current)")
                if title:
                    note["title"] = encrypt_and_encode_secure(title, hashed_pass)
                
                print(f"{L_CYAN}Enter new content (press Ctrl+D or Ctrl+Z when done):{RESET}")
                content_lines = []
                try:
                    while True:
                        line = input()
                        content_lines.append(line)
                except EOFError:
                    if content_lines:
                        content = '\n'.join(content_lines)
                        note["content"] = encrypt_and_encode_secure(content, hashed_pass)
                
                contents["notes"] = self.notes
                if vault.save_vault_contents(contents, hashed_pass):
                    self.ui.success_message("Note updated successfully")
                    return True
            return False
        
        def delete_note(self):
            if not self.show_notes():
                return False
                
            idx = int(self.ui.input_prompt("Enter note number to delete")) - 1
            if 0 <= idx < len(self.notes):
                if self.ui.confirmation_prompt("Are you sure you want to delete this note?"):
                    self.notes.pop(idx)
                    contents["notes"] = self.notes
                    if vault.save_vault_contents(contents, hashed_pass):
                        self.ui.success_message("Note deleted successfully")
                        return True
            return False
        
        def view_note(self):
            if not self.show_notes():
                return
                
            note_idx = self.ui.input_prompt("Enter note number to view (or Enter to go back)")
            if note_idx:
                try:
                    idx = int(note_idx) - 1
                    if 0 <= idx < len(self.notes):
                        note = self.notes[idx]
                        self.ui.header(decode_and_decrypt_secure('title', note, hashed_pass))
                        reveal_secret("", decode_and_decrypt_secure('content', note, hashed_pass))
                        input(f"\n{VINTAGE}Press Enter to continue...{RESET}")
                    else:
                        self.ui.error_message("Invalid note number")
                except ValueError:
                    self.ui.error_message("Invalid input")
    
    # Initialize UI controller
    notes_ui = NotesUI()
    
    while True:
        notes_ui.display_menu()
        choice = notes_ui.ui.input_prompt("Select option")
        
        if choice == '1':
            notes_ui.view_note()
        elif choice == '2':
            notes_ui.add_note()
        elif choice == '3':
            notes_ui.edit_note()
        elif choice == '4':
            notes_ui.delete_note()
        elif choice == '0':
            break
        else:
            notes_ui.ui.error_message("Invalid option")

def mobile_password_manager(hashed_pass, contents, device_type='mobile'):
    """Mobile-friendly password management view"""
    vault_ui = VaultUI(device_type)
    
    while True:
        vault_ui.ui.header("Password Manager")
        accounts = contents.get("accounts", [])
        
        if device_type == 'mobile':
            vault_ui.ui.menu_item('1', '🔑 View Passwords')
            vault_ui.ui.menu_item('2', '➕ Add Password')
            vault_ui.ui.menu_item('3', '✏️ Edit Password')
            vault_ui.ui.menu_item('4', '🗑️ Delete Password')
            vault_ui.ui.menu_item('5', '📋 Copy Password')
            vault_ui.ui.menu_item('0', '↩️ Back')
        else:
            vault_ui.ui.menu_item('1', 'View Passwords')
            vault_ui.ui.menu_item('2', 'Add Password')
            vault_ui.ui.menu_item('3', 'Edit Password')
            vault_ui.ui.menu_item('4', 'Delete Password')
            vault_ui.ui.menu_item('5', 'Copy Password')
            vault_ui.ui.menu_item('0', 'Back')
        
        choice = vault_ui.ui.input_prompt("Select option")
        
        if choice == '1':
            if not accounts:
                vault_ui.ui.error_message("No passwords stored")
                continue
                
            vault_ui.ui.header("Your Passwords")
            for i, account in enumerate(accounts, 1):
                print(f"{GOLD}[{i}]{RESET} {decode_and_decrypt_secure('site', account, hashed_pass)}")
                print(f"   Username: {decode_and_decrypt_secure('username', account, hashed_pass)}")
            input(f"\n{VINTAGE}Press Enter to continue...{RESET}")
            
        elif choice == '2':
            vault_ui.ui.header("Add New Password")
            site = vault_ui.ui.input_prompt("Enter website/service name")
            username = vault_ui.ui.input_prompt("Enter username/email")
            password = timeout_getpass(f"{L_CYAN}Enter password: {RESET}")
            
            new_account = {
                "site": encrypt_and_encode_secure(site, hashed_pass),
                "username": encrypt_and_encode_secure(username, hashed_pass),
                "password": encrypt_and_encode_secure(password, hashed_pass)
            }
            
            accounts.append(new_account)
            contents["accounts"] = accounts
            vault.save_vault_contents(contents, hashed_pass)
            vault_ui.ui.success_message("Password added successfully")
            
        elif choice == '3':
            if not accounts:
                vault_ui.ui.error_message("No passwords to edit")
                continue
                
            vault_ui.ui.header("Edit Password")
            for i, account in enumerate(accounts, 1):
                print(f"{GOLD}[{i}]{RESET} {decode_and_decrypt_secure('site', account, hashed_pass)}")
                
            idx = vault_ui.ui.input_prompt("Enter password number to edit")
            try:
                idx = int(idx) - 1
                if 0 <= idx < len(accounts):
                    account = accounts[idx]
                    site = vault_ui.ui.input_prompt("Enter new site name (or Enter to keep current)")
                    username = vault_ui.ui.input_prompt("Enter new username (or Enter to keep current)")
                    password = timeout_getpass(f"{L_CYAN}Enter new password (or Enter to keep current): {RESET}")
                    
                    if site:
                        account["site"] = encrypt_and_encode_secure(site, hashed_pass)
                    if username:
                        account["username"] = encrypt_and_encode_secure(username, hashed_pass)
                    if password:
                        account["password"] = encrypt_and_encode_secure(password, hashed_pass)
                    
                    vault.save_vault_contents(contents, hashed_pass)
                    vault_ui.ui.success_message("Password updated successfully")
                else:
                    vault_ui.ui.error_message("Invalid password number")
            except ValueError:
                vault_ui.ui.error_message("Invalid input")
                
        elif choice == '4':
            if not accounts:
                vault_ui.ui.error_message("No passwords to delete")
                continue
                
            vault_ui.ui.header("Delete Password")
            for i, account in enumerate(accounts, 1):
                print(f"{GOLD}[{i}]{RESET} {decode_and_decrypt_secure('site', account, hashed_pass)}")
                
            idx = vault_ui.ui.input_prompt("Enter password number to delete")
            try:
                idx = int(idx) - 1
                if 0 <= idx < len(accounts):
                    if vault_ui.ui.confirmation_prompt("Are you sure you want to delete this password?"):
                        accounts.pop(idx)
                        contents["accounts"] = accounts
                        vault.save_vault_contents(contents, hashed_pass)
                        vault_ui.ui.success_message("Password deleted successfully")
                else:
                    vault_ui.ui.error_message("Invalid password number")
            except ValueError:
                vault_ui.ui.error_message("Invalid input")
                
        elif choice == '5':
            if not accounts:
                vault_ui.ui.error_message("No passwords to copy")
                continue
                
            vault_ui.ui.header("Copy Password")
            for i, account in enumerate(accounts, 1):
                print(f"{GOLD}[{i}]{RESET} {decode_and_decrypt_secure('site', account, hashed_pass)}")
                
            idx = vault_ui.ui.input_prompt("Enter password number to copy")
            try:
                idx = int(idx) - 1
                if 0 <= idx < len(accounts):
                    password = decode_and_decrypt_secure('password', accounts[idx], hashed_pass)
                    # Previously cleared after 0.5 s, too soon to paste. Now
                    # cleared after 30 s or on exit, like the desktop UI.
                    if copy_secret(password):
                        vault_ui.ui.success_message(copy_notice("Password"))
                    else:
                        vault_ui.ui.error_message("Could not access the clipboard")
                else:
                    vault_ui.ui.error_message("Invalid password number")
            except ValueError:
                vault_ui.ui.error_message("Invalid input")
                
        elif choice == '0':
            break
        else:
            vault_ui.ui.error_message("Invalid option")


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





if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting safely...")
    finally:
        secure_cleanup_common()


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
    
    def notes_menu(self):
        self.ui.header('Notes Management')
        if self.device_type == 'mobile':
            self.ui.menu_item('1', '📄 View Notes')
            self.ui.menu_item('2', '➕ Add Note')
            self.ui.menu_item('3', '✏️ Edit Note')
            self.ui.menu_item('4', '🗑️ Delete Note')
            self.ui.menu_item('0', '↩️ Back')
        else:
            self.ui.menu_item('1', 'View All Notes')
            self.ui.menu_item('2', 'Add New Note')
            self.ui.menu_item('3', 'Edit Note')
            self.ui.menu_item('4', 'Delete Note')
            self.ui.menu_item('0', 'Back to Main Menu')
    
    def accounts_menu(self):
        self.ui.header('Accounts Management')
        if self.device_type == 'mobile':
            self.ui.menu_item('1', '🔍 View Accounts')
            self.ui.menu_item('2', '➕ Add Account')
            self.ui.menu_item('3', '✏️ Edit Account')
            self.ui.menu_item('4', '🗑️ Delete Account')
            self.ui.menu_item('0', '↩️ Back')
        else:
            self.ui.menu_item('1', 'View All Accounts')
            self.ui.menu_item('2', 'Add New Account')
            self.ui.menu_item('3', 'Edit Account')
            self.ui.menu_item('4', 'Delete Account')
            self.ui.menu_item('0', 'Back to Main Menu')
    
    def profile_menu(self):
        self.ui.header('Profile Settings')
        if self.device_type == 'mobile':
            self.ui.menu_item('1', '👤 View Profile')
            self.ui.menu_item('2', '✏️ Edit Profile')
            self.ui.menu_item('3', '🔄 Change Password')
            self.ui.menu_item('0', '↩️ Back')
        else:
            self.ui.menu_item('1', 'View Profile Details')
            self.ui.menu_item('2', 'Edit Profile Information')
            self.ui.menu_item('3', 'Change Master Password')
            self.ui.menu_item('0', 'Back to Main Menu')



def initialize_vault(device_type='mobile'):
    try:
        vault_ui = VaultUI(device_type)
        # Check if vault exists and initialize if needed
        try:
            with open("Bunker.mmf", "rb"):
                pass
        except FileNotFoundError:
            clear_screen()
            print(BUNKER_ASCII)
            vault_ui.ui.error_message("Vault not found... Setting up new vault")
            return vaultSetup()

        # Load salt for key derivation
        salt = load_salt()
        return salt
    except Exception as e:
        print(f"{RED}Failed to load vault: {safe_error(e)}{RESET}")
        return None

def save_mobile_vault(db, hashed_pass, device_type='mobile'):
    try:
        vault_ui = VaultUI(device_type)
        encrypted_db = vault.encrypt_data(json.dumps(db).encode(), hashed_pass)
        with open("Mobile.mmf", "wb") as f:
            f.write(encrypted_db)
        vault_ui.ui.success_message("Vault saved successfully")
        return True
    except Exception as e:
        vault_ui.ui.error_message(f"Failed to save mobile vault: {safe_error(e)}")
        return False

def mobile_profile_manager(hashed_pass, contents, device_type='mobile'):
    """Mobile-friendly profile management view"""
    vault_ui = VaultUI(device_type)
    
    while True:
        vault_ui.ui.header("Profile Management")
        profiles = contents.get("profiles", [])
        
        if device_type == 'mobile':
            vault_ui.ui.menu_item('1', '👤 View Profile')
            vault_ui.ui.menu_item('2', '➕ Add Profile')
            vault_ui.ui.menu_item('3', '✏️ Edit Profile')
            vault_ui.ui.menu_item('0', '↩️ Back')
        else:
            vault_ui.ui.menu_item('1', 'View Profile')
            vault_ui.ui.menu_item('2', 'Add Profile')
            vault_ui.ui.menu_item('3', 'Edit Profile')
            vault_ui.ui.menu_item('0', 'Back')
        
        choice = vault_ui.ui.input_prompt("Select option")
        
        if choice == '1':
            if not profiles:
                vault_ui.ui.error_message("No profile found")
                continue
                
            vault_ui.ui.header("Your Profile")
            profile = profiles[0] if profiles else None
            if profile:
                print(f"{CYAN}Name:{RESET} {decode_and_decrypt_secure('name', profile, hashed_pass)}")
                print(f"{CYAN}Email:{RESET} {decode_and_decrypt_secure('email', profile, hashed_pass)}")
                print(f"{CYAN}Username:{RESET} {decode_and_decrypt_secure('username', profile, hashed_pass)}")
            input(f"\n{VINTAGE}Press Enter to continue...{RESET}")
            
        elif choice == '2':
            vault_ui.ui.header("Add Profile")
            name = vault_ui.ui.input_prompt("Enter your name")
            email = vault_ui.ui.input_prompt("Enter your email")
            username = vault_ui.ui.input_prompt("Enter your username")
            
            new_profile = {
                "name": encrypt_and_encode_secure(name, hashed_pass),
                "email": encrypt_and_encode_secure(email, hashed_pass),
                "username": encrypt_and_encode_secure(username, hashed_pass)
            }
            
            profiles.append(new_profile)
            contents["profiles"] = profiles
            vault.save_vault_contents(contents, hashed_pass)
            vault_ui.ui.success_message("Profile added successfully")
            
        elif choice == '3':
            if not profiles:
                vault_ui.ui.error_message("No profile to edit")
                continue
                
            vault_ui.ui.header("Edit Profile")
            profile = profiles[0]
            name = vault_ui.ui.input_prompt("Enter new name (or Enter to keep current)")
            email = vault_ui.ui.input_prompt("Enter new email (or Enter to keep current)")
            username = vault_ui.ui.input_prompt("Enter new username (or Enter to keep current)")
            
            if name:
                profile["name"] = encrypt_and_encode_secure(name, hashed_pass)
            if email:
                profile["email"] = encrypt_and_encode_secure(email, hashed_pass)
            if username:
                profile["username"] = encrypt_and_encode_secure(username, hashed_pass)
            
            vault.save_vault_contents(contents, hashed_pass)
            vault_ui.ui.success_message("Profile updated successfully")
            
        elif choice == '0':
            break
        else:
            vault_ui.ui.error_message("Invalid option")

def decode_and_decrypt_secure(field, info, hashed_pass):
    val = info.get(field, "N/A")
    if val == "N/A":
        return "N/A"
    if isinstance(val, str):
        try:
            val_bytes = base64.b64decode(val)
        except:
            val_bytes = val.encode()
    else:
        val_bytes = val
    return vault.decrypt_data(val_bytes, hashed_pass).decode("utf-8")

def mobile_feature_select(hashed_pass, device_type='mobile'):
    """Mobile-friendly feature selection view"""
    vault_ui = VaultUI(device_type)
    try:
        with open("Bunker.mmf", "rb") as f:
            encrypted_contents = f.read()
        contents = json.loads(
            vault.decrypt_data(encrypted_contents, hashed_pass).decode()
        )
    except FileNotFoundError:
        contents = {"profiles": [], "notes": [], "accounts": []}

    
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
            
            try:
                with open("Bunker.mmf", "rb") as f:
                    encrypted_contents = f.read()
                contents = json.loads(
                    vault.decrypt_data(encrypted_contents, hashed_pass).decode()
                )
            except FileNotFoundError:
                contents = {"profiles": [], "notes": []}
            
            if choice == '1':
                mobile_password_manager(hashed_pass, contents, device_type)
            elif choice == '2':
                mobile_note_manager(hashed_pass, contents, device_type)
            elif choice == '3':
                mobile_profile_manager(hashed_pass, contents, device_type)
            elif choice == '0':
                vault_ui.ui.success_message("Goodbye!")
                break
            else:
                vault_ui.ui.error_message("Invalid option")
                
    except Exception as e:
        vault_ui.ui.error_message(f"An error occurred: {safe_error(e)}")
        return False
    return True

def encrypt_and_encode_secure(value, hashed_pass):
    return base64.b64encode(
        vault.encrypt_data(str(value).encode(), hashed_pass)
    ).decode("utf-8")
def mobile_setup_view():
    """Mobile-friendly vault setup view"""
    try:
        clear_screen()
        print(BUNKER_ASCII)
        print(f"{CYAN}Welcome to BUNKER Mobile Setup{RESET}\n")
        
        # Check if vault exists
        try:
            with open("bunker.mmf", "rb"):
                print(f"{GREEN}✓ Existing vault detected{RESET}")
                return load_salt()
        except FileNotFoundError:
            print(f"{MUSTARD}⚠ No vault found - Let's set up a new one{RESET}")
            return vaultSetup()
            
    except Exception as e:
        print(f"{RED}✗ Setup failed: {safe_error(e)}{RESET}")
        return None


