import os, platform
from main.SECURE_IO import safe_error, write_private_bytes
import importlib.util
import time
import sys
import hashlib
import base64

L_CYAN = "\033[38;5;159m"  # Light Cyan
BUNKER = "\033[90m"
DBLUE = "\033[36m"
FORANGE = "\033[38;5;214m"
FBLUE = "\033[38;5;33m"
FRED = "\033[38;5;196m"
GOLD = "\033[93m"  # Gold color brigth yellow
GREEN = "\033[92m"  # Green color
RED = "\033[91m"  # Red color
RESET = "\033[0m"  # Reset to default color
DPURPLE = "\033[34m"  # Dark Purple
MUSTARD = "\033[33m"  # Mustard Yellow
VINTAGE = "\033[31m"  # Vintage Red dark red ograngeish
LPURPLE = "\033[94m"  # light putple
PURPLE = "\033[95m"  #
CYAN = "\033[96m"  #
# Accessibility: honour the NO_COLOR convention (https://no-color.org).
# If NO_COLOR is set to any non-empty value, print without ANSI colours.
if os.environ.get("NO_COLOR"):
    L_CYAN = BUNKER = DBLUE = FORANGE = FBLUE = FRED = GOLD = GREEN = RED = RESET = DPURPLE = MUSTARD = VINTAGE = LPURPLE = PURPLE = CYAN = ""

class ModernUI:
    """Minimal UI elements needed for device detection"""
    @staticmethod
    def header(title):
        print(f"\n{CYAN}={'='*50}{RESET}")
        print(f"{PURPLE}{title:^50}{RESET}")
        print(f"{CYAN}={'='*50}{RESET}\n")
    
    @staticmethod
    def menu_item(key, description):
        print(f"{GOLD}[{key}]{RESET} {CYAN}{description}{RESET}")
    
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



art = rf"""
                                 /\
                            /\  //\\
                     /\    //\\///\\\
                    //\\  ///\////\\\\  
       /\          /  ^ \/^ ^/^  ^  ^ \
      / ^\    /\  / ^   /  ^/ ^ ^ ^   ^\
     /^   \  / ^\/ ^ ^   ^ / ^  ^    ^  \
    /  ^ ^ \/^  ^\ ^ ^ ^  /^  ^   ^      \
   / ^ ^  ^ \ ^   \  ^   /        ^   ^   \
  / ^^  ^ ^ ^\     \    /   +-------------------+
 /___________________ ______| BUNKER CHECKPOINT |
                    /|\     |                   | 
                   / | \    |    DEVICE TYPE    |
                  /  |  \   |      REQUIRED     |
                 /   |   \  +-------------------+
                /    |    \     |            |
               /     |     \    |            |
"""


def get_platform_info():
    """Detect the current platform and return platform-specific details"""
    system = platform.system().lower()
    
    # Base platform info
    platform_info = {
        "system": system,
        "is_mobile": False,
        "is_ios": False,
        "is_android": False,
        "is_desktop": True,
        "capabilities": set()
    }
    
    # iOS detection (a-Shell environment)
    if (system == "darwin" and 
        (os.environ.get("IDEVICE_IDENTITY") or 
         "IPHONE" in platform.platform() or
         "iOS" in platform.platform())):
        platform_info.update({
            "is_mobile": True,
            "is_ios": True,
            "is_desktop": False,
            "capabilities": {"basic_file_ops", "network_basic"}
        })
    
    # Android detection (Termux environment)
    elif "ANDROID_ROOT" in os.environ or "ANDROID_DATA" in os.environ:
        platform_info.update({
            "is_mobile": True,
            "is_android": True,
            "is_desktop": False,
            "capabilities": {"basic_file_ops", "network_basic", "terminal"}
        })
    
    # Desktop platforms
    else:
        platform_info["capabilities"] = {"full_terminal", "network_advanced", "basic_file_ops"}
        
        # Add platform-specific capabilities
        if system == "darwin":  # macOS
            platform_info["capabilities"].update({"gui", "clipboard"})
        elif system == "windows":
            platform_info["capabilities"].update({"gui", "clipboard"})
    
    return platform_info

def check_terminal_size(min_rows=27, min_cols=120):
    """Simplified terminal size check for mobile devices"""
    try:
        terminal_size = os.get_terminal_size()
        needs_resize = terminal_size.lines < min_rows or terminal_size.columns < min_cols
        
        if needs_resize:
            print(f"{GOLD}Your terminal size might be too small for optimal viewing.{RESET}")
            print(f"{GOLD}Current size: {terminal_size.lines} rows x {terminal_size.columns} columns{RESET}")
            print(f"{GOLD}Recommended: {min_rows} rows x {min_cols} columns{RESET}")
            time.sleep(2)
            
        return not needs_resize
    except Exception:
        return True  # Assume terminal size is okay if we can't check

def detect_device():
    """Detect device type with user confirmation and fallback to manual selection"""
    ui = ModernUI()
    detected_type = detect_user_agent()
    
    # First try auto-detection with confirmation
    print(art)
    ui.header("MULTI DEVICE INTERFACE")
    print(f"{GOLD}I detect that you're using a {GREEN}{detected_type} device.{RESET}")
    if ui.confirmation_prompt("Is this correct?"):
        return detected_type
    
    # If user says no, show manual selection
    # If detection was wrong, ask user to specify
    print(f"\n{VINTAGE}Please select your actual device type:{RESET}\n")
    ui.menu_item('1', '📱 Mobile Phone')
    ui.menu_item('2', '📱 Tablet')
    ui.menu_item('3', '💻 Desktop/Laptop')
    ui.menu_item('4', '🔧 Other')
    
    choice = ui.input_prompt("\nSelect your device type")
    return {
        '1': 'mobile',
        '2': 'tablet',
        '3': 'desktop',
        '4': 'other'
    }.get(choice, 'desktop')



def clear_screen():
    """
    Clear the terminal screen with enhanced platform support and error handling.
    Uses multiple methods to ensure screen is cleared across different terminals.
    """
    try:
        # Windows-specific handling
        if platform.system().lower() == "windows":
            os.system("cls")  # Try native Windows clear first
            # Fallback to ANSI escape sequences if supported
            print("\033[2J\033[H", end="", flush=True)
            
        # Unix-like systems (Linux, macOS, BSD)
        else:
            # Try native clear command
            os.system("clear")
            # Ensure screen is fully cleared with ANSI escape sequences
            print("\033[2J\033[H", end="", flush=True)
            sys.stdout.flush()
        
        # Additional ANSI escape sequences for thorough clearing
        print("\033[3J", end="", flush=True)  # Clear scrollback buffer
        
    except Exception as e:
        # Fallback method if everything else fails
        for _ in range(100):
            print("\n", end="", flush=True)
        sys.stdout.flush()
        
        # Move cursor to top-left
        print("\033[H", end="", flush=True)
        
# IMPORTS
import os, sys, time, importlib.util, base64, json, secrets
import datetime, threading, platform, gc, uuid, hashlib, getpass
from queue import Queue
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet

# Security constants
MIN_PASSWORD_LENGTH = 8  # Increased from 6
MAX_PASSWORD_LENGTH = 32
RECOMMENDED_PASSWORD_LENGTH = 12
KEY_SIZE = 32
SALT_SIZE = 32
NONCE_SIZE = 12
TAG_SIZE = 16
timeoutGlobalCode = "*TIMEOUT*"

# Additional security settings
PEPPER = os.environ.get("BUNKER_PEPPER", "default_pepper_value")

def detect_user_agent():
    """
    Attempt to detect the user's device type from the environment.
    Returns: str - One of 'mobile', 'tablet', 'desktop'
    """
    # Get system info
    term = os.environ.get('TERM', '').lower()
    screen_size = os.get_terminal_size().columns if hasattr(os, 'get_terminal_size') else 80
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    # Check for mobile/tablet specific indicators
    if any(dev in term for dev in ['mobile', 'phone', 'android', 'ios']):
        return 'mobile'
    elif any(dev in term for dev in ['ipad', 'tablet']):
        return 'tablet'
    
    # Use screen size as a fallback indicator
    if screen_size <= 80:
        return 'mobile'
    elif screen_size <= 120:
        return 'tablet'
    
    # Additional checks for arm-based devices
    if 'arm' in machine and system in ['darwin', 'linux']:
        return 'mobile' if screen_size <= 100 else 'tablet'
    
    return 'desktop'

class SecureVaultEnhanced:
    def __init__(self):
        self.backend = default_backend()
        self.config_file = "bunker.cfg"  # Single configuration file
        self.database_file = "Bunker.mmf"
        self.salt_file = "bunker.salt"
        self.ui_config_file = "config.cfg"
        self._memory_guard = bytearray(32)
        self._shared_key = None
        self._last_key_update = 0
        
    def encrypt_data(self, data, key):
        """Encrypt data using AES-GCM"""
        # Ensure data is bytes
        if isinstance(data, str):
            data = data.encode('utf-8')
            
        # Generate a random 12-byte nonce
        nonce = os.urandom(12)
        
        # Create cipher and encrypt
        aesgcm = AESGCM(base64.urlsafe_b64decode(key))
        ciphertext = aesgcm.encrypt(nonce, data, None)
        
        # Return nonce + ciphertext as bytes
        return nonce + ciphertext
        
    def decrypt_data(self, encrypted_data, key):
        """Decrypt data using AES-GCM"""
        # Ensure encrypted_data is bytes
        if isinstance(encrypted_data, str):
            try:
                # Try to decode as base64 first
                encrypted_data = base64.urlsafe_b64decode(encrypted_data)
            except:
                # If not base64, convert to bytes
                encrypted_data = encrypted_data.encode('utf-8')
        
        # Extract nonce and ciphertext
        nonce, ciphertext = encrypted_data[:12], encrypted_data[12:]
        
        # Create cipher and decrypt
        aesgcm = AESGCM(base64.urlsafe_b64decode(key))
        return aesgcm.decrypt(nonce, ciphertext, None)
    
    def derive_key_hybrid(self, password: str, salt: bytes, pepper: str = "") -> bytes:
        """Hybrid key derivation using PBKDF2 on mobile"""
        try:
            # Combine password and pepper
            password_peppered = password + pepper
            
            # Use only PBKDF2 for mobile version since argon2 may not be available
            pbkdf2 = PBKDF2HMAC(
                algorithm=hashes.SHA3_256(),
                length=KEY_SIZE,
                salt=salt,
                iterations=110000,
                backend=self.backend
            )
            derived_key = pbkdf2.derive(password_peppered.encode())
            return base64.urlsafe_b64encode(derived_key)
            
        except Exception as e:
            self.secure_wipe()
            raise ValueError(f"Key derivation failed: {safe_error(e)}")
            
    def secure_wipe(self):
        """Securely wipe sensitive data from memory"""
        if hasattr(self, '_memory_guard'):
            for i in range(len(self._memory_guard)):
                self._memory_guard[i] = 0
    
    def __del__(self):
        """Secure cleanup when object is destroyed"""
        self.secure_wipe()

# Initialize global vault instance
vault = SecureVaultEnhanced()

def save_salt(salt, filename="bunker.salt"):
    """Save salt to file (atomic, owner-only)"""
    write_private_bytes(filename, salt)

def load_salt(filename="bunker.salt"):
    """Load salt from file"""
    with open(filename, "rb") as f:
        return f.read()

def get_mobile_ui_key():
    """Generate a consistent key for mobile UI config"""
    # Use system-specific information to generate a consistent key
    system_info = []
    
    try:
        # Machine ID (most reliable)
        if os.path.exists('/etc/machine-id'):
            with open('/etc/machine-id', 'r') as f:
                system_info.append(f.read().strip())
        elif os.path.exists('/var/lib/dbus/machine-id'):
            with open('/var/lib/dbus/machine-id', 'r') as f:
                system_info.append(f.read().strip())
    except:
        pass
    
    # Add more system-specific info
    system_info.extend([
        platform.node(),  # hostname
        platform.system(),  # OS name
        platform.machine(),  # architecture
        os.getenv('USER', os.getenv('USERNAME', 'unknown'))  # username
    ])
    
    # Combine all system info
    combined_info = '|'.join(filter(None, system_info)).encode('utf-8')
    
    # Use SHA-256 to create a consistent 32-byte key
    key = hashlib.sha256(combined_info).digest()
    return base64.urlsafe_b64encode(key)

def derive_system_key():
    """Derive a system-specific key using available system information"""
    try:
        # Get system information that should be consistent across reboots
        components = []
        
        # Try to get machine ID first (most reliable on Unix systems)
        machine_id = None
        for path in ['/etc/machine-id', '/var/lib/dbus/machine-id']:
            try:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        machine_id = f.read().strip()
                        break
            except:
                pass
        
        if machine_id:
            components.append(machine_id)
            
        # Add other system information
        components.extend([
            platform.node(),  # hostname
            platform.system(),  # OS name
            platform.machine(),  # architecture
            os.path.expanduser('~'),  # home directory path
            os.getenv('USER', os.getenv('USERNAME', 'unknown'))  # username
        ])
        
        # Get vault salt if available (this helps ensure consistency with desktop)
        try:
            if os.path.exists('bunker.salt'):
                with open('bunker.salt', 'rb') as f:
                    vault_salt = f.read()
                components.append(str(vault_salt))
        except:
            pass
            
        # Create a consistent string from gathered info
        system_string = '|'.join(filter(None, components)).encode('utf-8')
        
        # Use PBKDF2 for key derivation (more secure than plain hash)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'BUNKER_MOBILE_KEY',  # Fixed salt for system key
            iterations=100000,
            backend=default_backend()
        )
        
        return base64.urlsafe_b64encode(kdf.derive(system_string))
        
    except Exception:
        # Fallback to a basic device key if all else fails
        fallback = f"bunker_device_{platform.node()}_{platform.system()}"
        return base64.urlsafe_b64encode(hashlib.sha256(fallback.encode()).digest())

def save_ui_config(config):
    """Save UI configuration using system-derived key"""
    try:
        # Get the system-specific key
        key = derive_system_key()
        
        # Prepare data
        data = json.dumps(config).encode("utf-8")
        encrypted = vault.encrypt_data(data, key)
        
        # Atomic, owner-only write (temp file + fsync + replace)
        write_private_bytes("config.cfg", encrypted)
        
    except Exception as e:
        print(f"{RED}** ALERT: Failed to save UI config: {safe_error(e)} **{RESET}")
        if os.path.exists("config.cfg.tmp"):
            os.remove("config.cfg.tmp")
        raise

def load_ui_config():
    """Load UI configuration using system-derived key"""
    try:
        # Get the system-specific key
        key = derive_system_key()
        
        with open("config.cfg", "rb") as f:
            encrypted = f.read()
            
        decrypted = vault.decrypt_data(encrypted, key)
        config = json.loads(decrypted.decode("utf-8"))
        
        # Validate config structure
        required_keys = ["attempts", "max_attempts", "disable_ipv4", "current_timeout"]
        if not all(key in config for key in required_keys):
            raise ValueError("Invalid config structure")
            
        return config
        
    except FileNotFoundError:
        # Create default config
        default_config = {
            "attempts": 0,
            "max_attempts": 3,
            "disable_ipv4": True,
            "current_timeout": 60
        }
        save_ui_config(default_config)
        return default_config
        
    except Exception as e:
        print(f"{RED}** ALERT: UI config file missing or corrupted. Error: {safe_error(e)} **{RESET}")
        secure_cleanup_common()  # Clean up before exit
        sys.exit(1)

def save_ui_config(config):
    """Save UI configuration using system-specific key"""
    try:
        # Get system-specific key
        key = derive_system_key()
            
        data = json.dumps(config).encode("utf-8")
        encrypted = vault.encrypt_data(data, key)
        
        # Atomic, owner-only write (temp file + fsync + replace)
        write_private_bytes("config.cfg", encrypted)
        
    except Exception as e:
        print(f"{RED}** ALERT: Failed to save UI config: {safe_error(e)} **{RESET}")
        if os.path.exists("config.cfg.tmp"):
            os.remove("config.cfg.tmp")
        raise

def load_ui_config():
    """Load UI configuration using system-specific key"""
    try:
        # Get system-specific key
        key = derive_system_key()
        
        with open("config.cfg", "rb") as f:
            encrypted = f.read()
        
        decrypted = vault.decrypt_data(encrypted, key)
        config = json.loads(decrypted.decode("utf-8"))
        
        # Validate config structure
        required_keys = ["attempts", "max_attempts", "disable_ipv4", "current_timeout"]
        if not all(key in config for key in required_keys):
            raise ValueError("Invalid config structure")
            
        return config
        
    except FileNotFoundError:
        # Create default config
        default_config = {
            "attempts": 0,
            "max_attempts": 3,
            "disable_ipv4": True,
            "current_timeout": 60
        }
        save_ui_config(default_config)
        return default_config
        
    except Exception as e:
        print(f"{RED}** ALERT: UI config file missing or corrupted. Error: {safe_error(e)} **{RESET}")
        secure_cleanup_common()  # Clean up before exit
        sys.exit(1)

def wipe_sensitive_memory():
    """Attempt to clear sensitive data from memory"""
    try:
        import gc
        # Force garbage collection
        gc.collect()
        # Clear local variables
        locals().clear()
    except Exception as e:
        print(f"{RED}** Warning: Memory wiping failed: {safe_error(e)} **{RESET}")

def cleanup_temp_files():
    """Remove temporary files created during operation"""
    # Only true temporaries belong here. bunker.salt and Bunker.mmf are the
    # vault itself: deleting them on exit makes the vault unrecoverable.
    temp_files = ["config.cfg.tmp", "vault.tmp"]
    for file in temp_files:
        try:
            if os.path.exists(file):
                os.remove(file)
        except Exception as e:
            print(f"{RED}** Warning: Failed to remove {file}: {safe_error(e)} **{RESET}")

def secure_cleanup_common():
    """Common cleanup operations shared by all exit scenarios"""
    try:
        # Clear any secret BUNKER put on the clipboard. Exit paths use
        # os._exit(), which skips atexit, so this must happen here.
        try:
            from main.SECURE_IO import clear_clipboard_if_ours
            clear_clipboard_if_ours()
        except Exception:
            pass

        # Wipe sensitive data in memory where possible
        wipe_sensitive_memory()
        
        # Remove temporary files
        cleanup_temp_files()
        
        # Clear any remaining vault data
        if hasattr(vault, 'clear_vault'):
            vault.clear_vault()
    except Exception as e:
        print(f"{RED}** ALERT: Error during cleanup: {safe_error(e)} **{RESET}")
        # Continue with exit even if cleanup fails

def timeoutCleanup():
    """Cleanup on timeout"""
    try:
        secure_cleanup_common()
        clear_screen()
        os._exit(0)
    except Exception as e:
        print(f"{RED}Error during timeout cleanup: {safe_error(e)}{RESET}")
        os._exit(1)

def timeoutInput(caption, timeout=60):
    """Handle timeout input"""
    try:
        import threading
        def input_thread(q):
            try:
                text = input(caption)
                q.put(text)
            except:
                q.put(None)
        
        q = Queue()
        thread = threading.Thread(target=input_thread, args=(q,), daemon=True)
        thread.start()
        thread.join(timeout)
        
        if thread.is_alive():
            timeoutCleanup()
            return None
            
        try:
            return q.get_nowait()
        except:
            return timeoutGlobalCode
            
    except Exception as e:
        print(f"{RED}Error during timeout input: {safe_error(e)}{RESET}")
        return timeoutGlobalCode

def timeout_getpass(prompt, timeout=60):
    """Get password with timeout"""
    try:
        import threading
        def getpass_thread(q):
            try:
                pwd = getpass.getpass(prompt)
                q.put(pwd)
            except:
                q.put(None)
                
        q = Queue()
        thread = threading.Thread(target=getpass_thread, args=(q,), daemon=True)
        thread.start()
        thread.join(timeout)
        
        if thread.is_alive():
            timeoutCleanup() 
            return None
            
        try:
            return q.get_nowait()
        except:
            return None
            
    except Exception as e:
        print(f"{RED}Error during timeout getpass: {safe_error(e)}{RESET}")
        return None
        
def setup_timeout() -> int:
    """Configure timeout settings"""
    while True:
        try:
            timeout_choice = input(
                f"{GOLD}Enter timeout value in seconds (10-3600, or 0 for no timeout. "
                f"Press enter for recommended 60 seconds, .c to cancel): {RESET}"
            )

            if timeout_choice == ".c":
                print(f"{GREEN}Operation cancelled...{RESET}")
                return None

            if timeout_choice.strip() == "":
                return 60

            timeout_value = int(timeout_choice)
            if timeout_value == 0:
                confirm = input(f"{RED}** WARNING: Are you sure you want to disable auto-logout? (y/n): {RESET}").lower()
                if confirm != 'y':
                    continue
                return 0
            elif 10 <= timeout_value <= 3600:
                return timeout_value
            else:
                print(f"{RED}** ALERT: Timeout must be between 10 and 3600 seconds, or 0 for no timeout. **{RESET}")
        except ValueError:
            print(f"{RED}** ALERT: Please enter a valid number. **{RESET}")

def verify_setup(vault: SecureVaultEnhanced, password: str, salt: bytes, verifier: bytes) -> bool:
    """Verify the vault setup"""
    try:
        derived_key = vault.derive_key_hybrid(password, salt)
        if not derived_key:
            return False
            
        decrypted = vault.decrypt_data(verifier, derived_key)
        return decrypted == b"BUNKER_VERIFIED"
    except Exception as e:
        print(f"{RED}** ALERT: Verification failed: {safe_error(e)} **{RESET}")
        return False
            
def verify_setup(vault: SecureVaultEnhanced, password: str, salt: bytes, verifier: bytes) -> bool:
    """Verify the vault setup"""
    try:
        derived_key = vault.derive_key_hybrid(password, salt)
        if not derived_key:
            return False
            
        decrypted = vault.decrypt_data(verifier, derived_key)
        return decrypted == b"BUNKER_VERIFIED"
    except Exception as e:
        print(f"{RED}** ALERT: Verification failed: {safe_error(e)} **{RESET}")
        return False
        
def vaultSetup():
    """Setup vault with enhanced security"""
    try:
        while True:
            setup_choice = input(f"\n{GOLD}Enter (.g) for simplified user guide, or (y/n) if you're ready to setup bunker password: {RESET}").lower()
            if setup_choice == 'y':
                break
            elif setup_choice == 'n':
                check_terminal_size()
                clear_screen()
                print(f"{GREEN}Operation cancelled...{RESET}")
                return False
            elif setup_choice == '.g':
                print(f"{CYAN}Setup Guide not implemented in mobile view{RESET}")
                continue
            else:
                print(f"{RED}** ALERT: Invalid input. Please enter y, n, or .g. **{RESET}")
                continue

        while True:
            show_password_choice = input(f"{GOLD}Do you want to show your password? (y/n) or (.c) to cancel: {RESET}").lower()
            if show_password_choice == 'y':
                show_password = True
                print(f"{RED}** ALERT: Your password will be shown as you type. **{RESET}")
                password_provided = input(f"{GOLD}Enter Password: {RESET}")
                if password_provided == '.c':
                    print(f"{GREEN}Operation cancelled...{RESET}")
                    return False
                    
                password_confirmation = input(f"{GOLD}Confirm password: {RESET}")
                if password_confirmation == '.c':
                    print(f"{GREEN}Operation cancelled...{RESET}")
                    return False
            elif show_password_choice == 'n':
                show_password = False
                password_provided = getpass.getpass(f"{GOLD}Enter Password: {RESET}")
                if password_provided == '.c':
                    print(f"{GREEN}Operation cancelled...{RESET}")
                    return False
                    
                password_confirmation = getpass.getpass(f"{GOLD}Confirm password: {RESET}")
                if password_confirmation == '.c':
                    print(f"{GREEN}Operation cancelled...{RESET}")
                    return False
            elif show_password_choice == '.c':
                print(f"{GREEN}Operation cancelled...{RESET}")
                return False
            else:
                print(f"{RED}** ALERT: Invalid input. Please enter y, n, or .c. **{RESET}")
                continue
                
            if password_provided != password_confirmation:
                print(f"{RED}** ALERT: Passwords do not match. Please try again. **{RESET}")
                continue
                
            if len(password_provided) < 8:
                print(f"{RED}** ALERT: Password must be at least 8 characters long. **{RESET}")
                continue
                
            break

        try:
            # Generate salt and save it
            salt = os.urandom(SALT_SIZE)
            save_salt(salt)

            # Derive key using password + salt (+ optional pepper)
            pepper = os.environ.get("BUNKER_PEPPER", "")
            derived_key = vault.derive_key_hybrid(password_provided, salt, password_provided)
            
            # Setup timeout
            timeout_value = setup_timeout()
            if timeout_value is None:
                print(f"{GREEN}Operation cancelled...{RESET}")
                return False

            # Create initial UI config
            ui_config = {
                "attempts": 0,
                "max_attempts": 3,
                "disable_ipv4": True,
                "current_timeout": timeout_value
            }
            
            # Save UI config with mobile-compatible encryption
            save_ui_config(ui_config)

            # Create verifier
            verifier = vault.encrypt_data(b"BUNKER_VERIFIED", derived_key)

            # Initialize empty database
            empty_db = {}
            
            # Save empty database
            encrypted_db = vault.encrypt_data(json.dumps(empty_db).encode(), derived_key)
            with open("Bunker.mmf", "wb") as f:
                f.write(encrypted_db)

            if os.name == 'posix':
                os.chmod("Bunker.mmf", 0o600)

            clear_screen()

            if timeout_value == 0:
                print(f"{RED}** WARNING: Auto-logout is disabled **{RESET}")
            else:
                print(f"{GREEN}Auto-logout timer set to: {timeout_value} seconds{RESET}")

            print(f"\n{GREEN}** SUCCESS: Vault setup complete! **{RESET}")
            print(f"{CYAN}✓ Master password configured{RESET}")
            print(f"{CYAN}✓ Database initialized{RESET}")
            print(f"{CYAN}✓ Security settings configured{RESET}")
            
            input(f"{GOLD}Press ENTER to continue: {RESET}")

            time.sleep(0.5)
            return True

        except Exception as e:
            print(f"{RED}** ALERT: Setup failed: {safe_error(e)} **{RESET}")
            return False
    except Exception as e:
        print(f"{RED}** ALERT: Setup failed: {safe_error(e)} **{RESET}")
        return False
    finally:
        # Secure cleanup
        vault.secure_wipe()
        gc.collect()
