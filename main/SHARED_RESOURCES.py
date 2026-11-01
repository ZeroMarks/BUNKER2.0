import sys, random, string, os, platform, gc,\
pyperclip, requests, psutil, datetime, secrets
from main.SECURE_IO import safe_error


# ANSI escape codes for colored output
# theme 1
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

#ART

nuke_art = rf"""{RED}
                                                    _.-^^---....,,--
                                                _--                  --_
                                               <                        >)
                                               |                         |
                                                \._                   _./
                                                   ```--. . , ; .--'''
                                                         | |   |
                                                      .-=||  | |=-.
                                                      `-=#$%&%$#=-'
                                                         | ;  :|
                                                _____.,-#%&$@%#&#~,._____{RESET}
"""

nuke_text = rf"""{RED}
               _____ _          ___           _              ___     _     _  _ _   _ _  _____ ___  _
              |_   _| |_  ___  | _ )_  _ _ _ | |_____ _ _   / __|___| |_  | \| | | | | |/ | __|   \| |
                | | | ' \/ -_) | _ \ || | ' \| / / -_| '_| | (_ / _ |  _| | .` | |_| | ' <| _|| |) |_|
                |_| |_||_\___| |___/\_,_|_||_|_\_\___|_|    \___\___/\__| |_|\_|\___/|_|\_|___|___/(_)

{RESET}
"""

divider = rf"""{FBLUE}◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢{RESET}"""


title_art = rf"""
{FBLUE}
                                                        )      )       (
                                          (          ( /(   ( /(       )\ )
                                        ( )\     (   )\())  )\()) (   (()/(
                                        )((_)    )\ ((_)\  ((_)\  )\   /(_))
                                       ((_)_  _ ((_) _((_) _ ((_)((_) (_))
{CYAN}                                        | _ )| | | || \| || |/ / | __|| _ \
                                        | _ \| |_| || .` || ' <  | _| |   /
                                        |___/ \___/ |_|\_||_|\_\ |___||_|_\{RESET}
"""


subwm = f"                                                                                          {CYAN}PROPERTY OF ZEROMARKSLLC{RESET}"


#ART + CODE


# ip curl
from typing import Optional
import threading , socket, subprocess, time, json

# Function to animate a loading bar with color
def loading_bar(duration, length=30):
    end_time = time.time() + duration
    print(f"{GOLD}Curl IP... Diplay Ip is {GREEN}ENABLED...{RESET}")
    while time.time() < end_time:
        for i in range(length + 1):
            bar = f'{MUSTARD}{"#" * i}{RESET}'
            padded_bar = pad_string(bar, length)
            sys.stdout.write(f"\r[{padded_bar}] {int((i / length) * 100)}%")
            sys.stdout.flush()
            time.sleep(duration / length)
    sys.stdout.write(
        "\r" + " " * (length + 10) + "\r"
    )  # Clear the line after the animation
    clear_screen()

# Function to animate a loading bar
def printable_length(s):
    return len(s) - s.count(GOLD) * (len(GOLD) - len(RESET))


# Function to pad thee string to the correct length

def pad_string(s, length):
    return s + " " * (length - printable_length(s))

def displaySection(title):
    print(f"{FBLUE}\n{'◢◤ ' * 5} {CYAN}{title} {FBLUE}{'◢◤ ' * 5}{RESET}")


# Initialize variables and locks
cached_ip = None
cache_lock = threading.Lock()
ip_fetch_thread = None

def start_ip_fetch_thread():
    global ip_fetch_thread
    if not ip_fetch_thread or not ip_fetch_thread.is_alive():
        ip_fetch_thread = threading.Thread(target=fetch_ip_thread_func, daemon=True)
        ip_fetch_thread.start()


def stop_ip_fetch_thread():
    global ip_fetch_thread
    if ip_fetch_thread and ip_fetch_thread.is_alive():
        ip_fetch_thread = None



def fetch_ip_thread_func():
    global cached_ip
    while True:
        current_connection = check_internet_connection()
        with cache_lock:
            if current_connection:
                ip = get_public_ipv4()
                if ip:  # Update cache only if new IP is successfully fetched
                    cached_ip = ip
            else:
                cached_ip = ""  # Set cached_ip to empty string to indicate offline
        time.sleep(30)  # Check every minute for internet connectivity changes

def get_public_ipv4() -> Optional[str]:
    try:
        output = subprocess.check_output(
            [
                "curl",
                "-4",
                "https://api64.ipify.org?format=json", #need to make a script for my site
                "--connect-timeout",
                "5",
                "--max-time",
                "10",
            ],
            stderr=subprocess.DEVNULL,
        )
        data = json.loads(output.decode("utf-8"))
        public_ipv4 = data["ip"]
        return public_ipv4
    except subprocess.CalledProcessError:
        return None
    except subprocess.TimeoutExpired:
        return None
    except Exception:
        return None


def check_internet_connection() -> bool:
    try:
        # Attempt to create a socket connection to Google's DNS server (8.8.8.8)
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        return True
    except OSError:
        return False



def print_IP(disable_ipv4: bool) -> str:
    with cache_lock:
        if disable_ipv4:
            ipv4_string = "   (IP fetching disabled)  "
        elif cached_ip == "":
            ipv4_string = "INTERNET IP:   (OFFLINE)   "
        else:
            ipv4_string = f"INTERNET IP: {cached_ip}"
    return ipv4_string


def display_bunker(disable_ipv4):
    if not disable_ipv4:
        start_ip_fetch_thread()
        loading_bar(1.7)

    else:
        stop_ip_fetch_thread()
    ipv4_string = print_IP(disable_ipv4)
    new = rf"""
                             *           .           .    {MUSTARD}_{RESET}    *           .                      .
                               .                         {MUSTARD}(({RESET}                             .
                 .                         .       /\     {MUSTARD}`{RESET}          .                                        *
                                              /\  /$$\        .
                              *        /\    /$$\/$$$$\      * /\    *                          .
                                   .  /$$\  /$$$/$$$$$$\  /\  /$$\                  *                       .
                         /\          {DBLUE}/  ^ \/^ ^/^  ^  ^ \{RESET}/$$\{DBLUE}/  ^ \      {RESET}.{DBLUE}     {CYAN}{ipv4_string}{FBLUE}
{RESET}                   *    /$$\{DBLUE}    /\  / ^   /  ^/ ^ ^ ^   ^\ ^/  ^^  \
{RESET}                       /$$$$\{DBLUE}  / ^\/ ^ ^   ^ / ^  ^    ^  \/ ^   ^  \       {GOLD}*{RESET}      +------------------+
                 {RESET}.{DBLUE}    /  ^ ^ \/^  ^\ ^ ^ ^   ^  ^   ^   {BUNKER}____{DBLUE}  ^   ^  \     {RESET}/|\{RESET}     |     PROPERTY     |
 {DBLUE}                    / ^ ^  ^ \ ^  {BUNKER}_{DBLUE}\{BUNKER}___________________{BUNKER}|  |{BUNKER}_____{DBLUE}^ ^  \   {RESET}/||{FBLUE}o{RESET}\    |        OF        |
 {DBLUE}                   / ^^  ^ ^ ^\  {BUNKER}/______________________________\{DBLUE} ^ ^ \ {RESET}/|{DBLUE}o{RESET}|||\   |   {CYAN}ZEROMARKSLLC{RESET}   |
 {DBLUE}                  /  ^  ^^ ^ ^  {BUNKER}/________________________________\{DBLUE}  ^  {RESET}/|||||{DBLUE}o{RESET}|\{RESET}  |    {RED} KEEP OUT!{RESET}    |
 {DBLUE}                 /^ ^  ^ ^^  ^    {BUNKER}|||||||||{CYAN}B-022{BUNKER}||||||||     |||      {RESET}/||{FBLUE}o{RESET}||||||\ +------------------+
 {DBLUE}                / ^   ^   ^    ^  {BUNKER}||||||||||||||||||||||     |||          {VINTAGE}| |         {RESET}|           |
 {DBLUE}               / ^ ^ ^  ^  ^  ^   {BUNKER}||||||||||||||||||||||_____|||{RESET}oooooooooo{VINTAGE}| |{RESET}ooooooo  |           |
  {RESET}        oooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooo{RESET}
"""
    print(new)


# DISABLE IP DISPLAY
def display_watermark(disable_ipv4):
    if not disable_ipv4:
        start_ip_fetch_thread()
    else:
        stop_ip_fetch_thread()
    ipv4_string = print_IP(disable_ipv4)
    watermark = f"""
{FBLUE}
                        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
{LPURPLE}                        | | {CYAN} PROPERTY OF: ZEROMARKSLLC{LPURPLE}  | | | | {CYAN}{ipv4_string}{FBLUE} {LPURPLE}| |
{FBLUE}                        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+{RESET}


"""
    print(watermark)


#code
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

def check_terminal_size(min_rows=27, min_cols=120):
    """
    Check if terminal size meets minimum requirements and attempt to resize if needed.
    
    Args:
        min_rows: Minimum required rows (default: 27)
        min_cols: Minimum required columns (default: 120)
        
    Returns:
        bool: True if terminal was adjusted, False otherwise
    """
    adjusted = False  # Flag to indicate if terminal size was adjusted

    try:
        # Get current terminal size using shutil (cross-platform)
        try:
            import shutil
            current_cols, current_rows = shutil.get_terminal_size()
            # Print current size for debugging (can be removed in production)
            # print(f"Current terminal size: {current_rows} rows x {current_cols} columns")
        except Exception:
            # Fallback to platform-specific methods if shutil fails
            current_rows, current_cols = 0, 0

        # Check if we need to resize
        needs_resize = current_rows < min_rows or current_cols < min_cols
        
        # Only attempt resize if needed
        if needs_resize:
            if platform.system() == "Windows":
                try:
                    # Try using ctypes for Windows (more reliable)
                    import ctypes
                    kernel32 = ctypes.windll.kernel32
                    
                    # Get console handle
                    h = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
                    
                    # Set console screen buffer size
                    kernel32.SetConsoleScreenBufferSize(h, ctypes.wintypes._COORD(min_cols, min_rows))
                    
                    # Set console window info
                    rect = ctypes.wintypes.SMALL_RECT(0, 0, min_cols-1, min_rows-1)
                    kernel32.SetConsoleWindowInfo(h, True, ctypes.byref(rect))
                    
                    adjusted = True
                except Exception:
                    # Fallback to mode command if ctypes fails
                    try:
                        os.system(f"mode con: cols={min_cols} lines={min_rows}")
                        adjusted = True
                    except Exception:
                        pass

            elif platform.system() == "Darwin":  # macOS
                try:
                    # Try using ANSI escape sequences (works in most terminals)
                    sys.stdout.write(f"\033[8;{min_rows};{min_cols}t")
                    sys.stdout.flush()
                    adjusted = True
                except Exception:
                    # Fallback to stty if ANSI fails
                    try:
                        os.system(f'printf "\033[8;{min_rows};{min_cols}t"')
                        adjusted = True
                    except Exception:
                        pass

            elif platform.system() == "Linux":
                try:
                    # Try using ANSI escape sequences first (works in most terminals)
                    sys.stdout.write(f"\033[8;{min_rows};{min_cols}t")
                    sys.stdout.flush()
                    adjusted = True
                except Exception:
                    # Fallback to curses if ANSI fails
                    try:
                        import curses
                        stdscr = curses.initscr()
                        curses.resizeterm(min_rows, min_cols)
                        curses.endwin()
                        adjusted = True
                    except Exception:
                        pass
    except Exception:
        # Silently handle any errors - terminal resizing is not critical
        pass

    return adjusted

def spinning_line(duration, message="Checking Files for tampering...", color=GOLD):
    """
    Display a spinning line animation for the specified duration.
    
    Args:
        duration: Duration in seconds to display the animation
        message: Message to display alongside the spinner (default: "Checking Files for tampering...")
        color: Color to use for the message (default: GOLD)
    """


    try:

        clear_screen()
        print(title_art)
        print(f"{CYAN}Checking Files{RESET}")
        print(divider)
        # More visually appealing spinner characters
        spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        
        # Fallback to simple spinner if unicode might not be supported
        if platform.system() == "Windows":
            spinner = ["-", "\\", "|", "/"]
            
        # Slow down the animation by increasing the sleep time
        animation_speed = 0.1  # Slower animation (0.2s instead of 0.1s)
        
        # Calculate how many frames we need to show based on duration and speed
        total_frames = int(duration / animation_speed)
        
        i = 0
        
        # Hide cursor if possible
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()
        
        # Display initial message for a moment before animation starts
        sys.stdout.write(f"\r{color}{message}{RESET}")
        sys.stdout.flush()
        
        
        try:
            # Run for a fixed number of frames instead of using time
            for _ in range(total_frames):
                symbol = spinner[i % len(spinner)]
                sys.stdout.write(f"\r{color}{message} {symbol}{RESET}")
                sys.stdout.flush()
                time.sleep(animation_speed)
                i += 1
                  # Pause briefly at the start
        finally:
            # Show cursor again
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()
            
        # Add a brief pause at the end so user can see the final state
        time.sleep(.3)
            
        # Clear the line and reset cursor position
        sys.stdout.write("\r" + " " * (len(message) + 10) + "\r")
        sys.stdout.flush()
        
        # Display completion message
        sys.stdout.write(f"\r{GREEN}✓ {message} Complete!{RESET}")
        sys.stdout.flush()
        time.sleep(.5)  # Show completion message for a second
        
        # Clear screen after animation
        clear_screen()
        
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        sys.stdout.write("\033[?25h")  # Show cursor
        sys.stdout.write("\r" + " " * (len(message) + 10) + "\r")
        sys.stdout.flush()
        clear_screen()
        print(f"{RED}Operation cancelled by user.{RESET}")
        
    except Exception as e:
        # If animation fails, just wait silently
        time.sleep(duration)
        clear_screen()
        # Optionally log the error
        # print(f"{RED}Animation error: {safe_error(e)}{RESET}")

def get_config_paths():
    """Get all possible config file paths"""
    base_paths = [
        ".",
        "main",
        "config" if os.path.exists("config") else None
    ]
    
    config_files = [
        "Bunker.mmf",
        "bunker.cfg",
        "bunker.salt",
        "config.cfg",
        ".vault_config"
    ]
    
    paths = []
    for base in base_paths:
        if base:
            for file in config_files:
                paths.append(os.path.join(base, file))
                
    return paths

def safe_exit(message, code=1):
    """Leave BUNKER after an error WITHOUT touching the vault.

    Policy: the vault is only ever destroyed by self_destruct() when the
    failed-login limit is reached. Crashes, errors, EOF, Ctrl+C and
    timeouts must end here (or in the timeout/interrupt cleanups) instead.
    """
    print(f"{RED}** ALERT: {message} **{RESET}")
    print(f"{CYAN}BUNKER closed. Your vault files were not changed.{RESET}")
    try:
        from main.SHARED_RESOURCES_MOBILE import secure_cleanup_common
        secure_cleanup_common()
    except Exception:
        pass
    sys.exit(code)


def self_destruct():
    """Destroy the vault. Only called when the failed-login limit is reached.

    Securely deletes all sensitive files with multiple overwrite passes."""
    # Updated list of sensitive files
    sensitive_files = [
        "Bunker.mmf",
        "bunker.cfg",
        "bunker.salt",
        "config.cfg",
        "bunker.chk",
        ".vault_config",
        "*.bak.*",        # overwrite_db backups (patterns are expanded below)
        "*.prev",         # copies kept during a master password change
        ".bunker-*.tmp",  # leftovers from an interrupted atomic write
    ]
    
    print(f"{GOLD}Self-destruct initiated. Searching for sensitive files...{RESET}")
    
    deleted_count = 0
    try:
        # Multiple overwrite passes for each file
        for file_name in sensitive_files:
            # Check current directory and potential locations
            paths_to_check = [
                file_name,  # Current directory
                os.path.join("main", file_name),  # main directory
                os.path.join("config", file_name) if os.path.exists("config") else None
            ]
            
            # Filter out None values; expand patterns; never follow symlinks
            # (overwriting through one would damage a file elsewhere).
            import glob
            expanded = []
            for p in paths_to_check:
                if not p:
                    continue
                expanded.extend(glob.glob(p) if any(c in p for c in "*?[") else [p])
            paths_to_check = [p for p in expanded if not os.path.islink(p)]
            
            for path in paths_to_check:
                if os.path.exists(path):
                    try:
                        print(f"{GOLD}Securely deleting: {path}{RESET}")
                        file_size = os.path.getsize(path)
                        
                        # Multiple overwrite passes with different patterns
                        for pass_num in range(3):  # DoD standard uses 3 passes
                            with open(path, "wb") as file:
                                pattern = {
                                    0: os.urandom(file_size),  # Random data
                                    1: b'\x00' * file_size,    # Zeros
                                    2: b'\xFF' * file_size     # Ones
                                }[pass_num]
                                file.write(pattern)
                                file.flush()
                                os.fsync(file.fileno())
                        
                        # Rename file to random name before deletion
                        random_name = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
                        random_path = os.path.join(os.path.dirname(path), random_name)
                        os.rename(path, random_path)
                        
                        # Platform-specific secure deletion
                        if platform.system() == 'Windows':
                            os.remove(random_path)
                        elif platform.system() == 'Darwin':  # macOS
                            subprocess.run(['rm', '-P', random_path], check=False)
                        else:  # Linux and other Unix-like systems
                            try:
                                subprocess.run(['shred', '-uzn', '3', random_path], check=False)
                            except FileNotFoundError:
                                os.remove(random_path)
                                
                        deleted_count += 1
                        print(f"{GREEN}Successfully deleted: {path}{RESET}")
                    except Exception as e:
                        try:
                            print(f"{RED}Secure deletion failed for {path}, attempting simple removal{RESET}")
                            os.remove(path)
                            deleted_count += 1
                        except Exception as inner_e:
                            print(f"{RED}Failed to delete {path}: {safe_error(inner_e)}{RESET}")
                
    except Exception as e:
        print(f"{RED}Error during self-destruct: {safe_error(e)}{RESET}")
    finally:
        # Enhanced memory wiping
        gc.collect()
        
        print(f"{GREEN}Deleted {deleted_count} sensitive files.{RESET}")
        time.sleep(1)
        
        clear_screen()
        print(f"{RED}** ALERT: SELF DESTRUCT INITIATED **{RESET}")
        print(nuke_text)
        print(nuke_art)
        print(f"\n{CYAN}BUNKER setup will start on next launch{RESET}")
        sys.exit(1)

def displayHeader(title):
    clear_screen()
    print(title_art)
    print(subwm)
    print(divider)
    print(str(title) + "\n")


###Helpers
# Clipboard handling lives in SECURE_IO so there is one timer and one rule:
# copied secrets are cleared after 30 seconds and when BUNKER exits.
def clear_clipboard(delay=0):
    """Clear the clipboard now if it still holds a secret BUNKER copied."""
    from main.SECURE_IO import clear_clipboard_if_ours
    return clear_clipboard_if_ours()


def to_clipboard(input_to_copy):
    """Copy a secret to the clipboard with auto-clear. Returns a status message."""
    from main.SECURE_IO import copy_secret, copy_notice
    if copy_secret(input_to_copy):
        return f"{GREEN}\n** SUCCESS: {copy_notice('Password')} **{RESET}"
    return f"{RED}\n** ALERT: Failed to copy to clipboard. **{RESET}"


# SYSTEM INFORMATION FUNCTIONS
def get_uptime():
    """Get system uptime with enhanced error handling"""
    try:
        boot_time = psutil.boot_time()
        uptime = datetime.datetime.now() - datetime.datetime.fromtimestamp(boot_time)
        
        # Format uptime in a more readable way
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if days > 0:
            return f"{days} days, {hours} hours, {minutes} minutes"
        elif hours > 0:
            return f"{hours} hours, {minutes} minutes"
        else:
            return f"{minutes} minutes, {seconds} seconds"
    except Exception as e:
        # More specific error message
        print(f"{RED}Error fetching system uptime: {safe_error(e)}{RESET}")
        return "Unknown"


def check_vpn():
    """Check for VPN connection with enhanced detection and error handling"""
    try:
        # Check for common VPN interfaces
        vpn_interfaces = ["tun", "tap", "ppp", "wg", "nordlynx", "utun"]
        network_interfaces = psutil.net_if_addrs()
        
        for interface in network_interfaces:
            if any(interface.startswith(vpn) for vpn in vpn_interfaces):
                return True
        
        # Check routing table for VPN gateways
        try:
            if os.name == 'nt':  # Windows
                routes = subprocess.check_output("route print", shell=True, stderr=subprocess.DEVNULL).decode('utf-8', errors='ignore')
            else:  # Unix/Linux/Mac
                routes = subprocess.check_output("netstat -nr", shell=True, stderr=subprocess.DEVNULL).decode('utf-8', errors='ignore')
            
            # Common VPN gateway patterns
            vpn_gateways = ["10.8.", "10.9.", "10.10.", "192.168.10."]
            if any(gateway in routes for gateway in vpn_gateways):
                return True
        except subprocess.SubprocessError:
            # Silently handle subprocess errors
            pass
            
        return False
        
    except Exception as e:
        # More specific error message
        print(f"{RED}Error checking VPN status: {safe_error(e)}{RESET}")
        return False


def get_external_ip():
    """Get external IP with timeout, retry logic, and enhanced security"""
    try:
        # Try multiple IP services with timeout
        ip_services = [
            "https://api.ipify.org?format=json",
            "https://ifconfig.me/ip",
            "https://icanhazip.com"
        ]
        
        for service in ip_services:
            try:
                # Set timeout to prevent hanging
                response = requests.get(service, timeout=3)
                
                if response.status_code == 200:
                    if service.endswith("json"):
                        return response.json().get("ip", "Unknown")
                    else:
                        return response.text.strip()
            except requests.RequestException:
                # Try next service if this one fails
                continue
                
        return "Unknown"
        
    except Exception as e:
        # More specific error message
        print(f"{RED}Error fetching external IP: {safe_error(e)}{RESET}")
        return "Unknown"
    
    
def get_network_interfaces():
    """Get network interfaces with enhanced error handling"""
    try:
        interfaces = psutil.net_if_addrs()
        # Filter out loopback interfaces for security
        return {k: v for k, v in interfaces.items() if not k.startswith('lo')}
    except Exception as e:
        print(f"{RED}Error fetching network interfaces: {safe_error(e)}{RESET}")
        return {}


def get_network_connections(timeout=5):
    """Get network connections with timeout and enhanced error handling"""
    try:
        # Use a timeout to prevent hanging
        result = {}
        conn_thread = threading.Thread(
            target=lambda: result.update({'connections': psutil.net_connections()}),
            daemon=True
        )
        conn_thread.start()
        conn_thread.join(timeout)
        
        if conn_thread.is_alive():
            # Thread is still running after timeout
            return None, "Operation timed out"
            
        if 'connections' not in result:
            return None, "Failed to retrieve connections"
            
        return result['connections'], None
        
    except psutil.AccessDenied:
        # More helpful error message with instructions
        return None, "Permission denied. Try running with administrator/root privileges."
    except Exception as e:
        return None, f"Error: {safe_error(e)}"


def format_connections(connections, detailed=False):
    """Format network connections with enhanced security and readability"""
    if not connections:
        return ["No connections available"]
        
    formatted_connections = []
    try:
        for conn in connections:
            # Handle potential None values safely
            laddr_ip = conn.laddr.ip if hasattr(conn, 'laddr') and conn.laddr else "N/A"
            laddr_port = conn.laddr.port if hasattr(conn, 'laddr') and conn.laddr else "N/A"
            raddr_ip = conn.raddr.ip if hasattr(conn, 'raddr') and conn.raddr else "N/A"
            raddr_port = conn.raddr.port if hasattr(conn, 'raddr') and conn.raddr else "N/A"
            
            # Get connection type name safely
            conn_type = getattr(conn, 'type', None)
            type_name = conn_type.name if hasattr(conn_type, 'name') else str(conn_type)
            
            # Get status safely
            status = getattr(conn, 'status', 'Unknown')
            
            # Get PID safely
            pid = getattr(conn, 'pid', None)
            pid_str = str(pid) if pid is not None else "N/A"

            if detailed:
                formatted = (
                    f"🔹 Connection Details:\n"
                    f"   - Type: {type_name}\n"
                    f"   - Local: {laddr_ip}:{laddr_port}\n"
                    f"   - Remote: {raddr_ip}:{raddr_port}\n"
                    f"   - Status: {status}\n"
                    f"   - Process ID: {pid_str}"
                )
            else:
                formatted = f"🔹 {type_name} connection from {laddr_ip}:{laddr_port} to {raddr_ip}:{raddr_port} status: {status}"
                
            formatted_connections.append(formatted)
            
        return formatted_connections
        
    except Exception as e:
        return [f"{RED}Error formatting connections: {safe_error(e)}{RESET}"]


def display_network_summary(connections):
    """Display network connection summary with enhanced security and usability"""
    try:
        if not connections:
            print(f"{RED}No connection data available{RESET}")
            return
            
        # Count connections by status and type safely
        established = sum(1 for conn in connections if getattr(conn, 'status', None) == psutil.CONN_ESTABLISHED)
        listening = sum(1 for conn in connections if getattr(conn, 'status', None) == psutil.CONN_LISTEN)
        
        # Handle potential AttributeError if socket module is not imported correctly
        try:
            udp = sum(1 for conn in connections if getattr(conn, 'type', None) == socket.SOCK_DGRAM)
        except (AttributeError, NameError):
            udp = sum(1 for conn in connections if getattr(conn, 'type', None) == 2)  # SOCK_DGRAM is usually 2
            
        # Get unique PIDs safely
        unique_pids = len(set(conn.pid for conn in connections if hasattr(conn, 'pid') and conn.pid is not None))
        
        # Get connection count by remote IP (potential security insight)
        remote_ips = {}
        for conn in connections:
            if hasattr(conn, 'raddr') and conn.raddr and conn.raddr.ip != "":
                remote_ips[conn.raddr.ip] = remote_ips.get(conn.raddr.ip, 0) + 1
                
        # Find top remote IPs
        top_remote_ips = sorted(remote_ips.items(), key=lambda x: x[1], reverse=True)[:5]
        
        displaySection("Network Connections Summary")
        print(f"\n⚠️  ** BEWARE PAGE DOES NOT TIME OUT ** ⚠️ \n")
        print(f"🔹 Established Connections: {established}")
        print(f"🔹 Listening Ports: {listening}")
        print(f"🔹 UDP Connections: {udp}")
        print(f"🔹 Processes with Active Connections: {unique_pids}")
        
        # Display top remote IPs if available
        if top_remote_ips:
            print(f"\n🔹 Top Remote IPs:")
            for ip, count in top_remote_ips:
                print(f"   - {ip}: {count} connection{'s' if count > 1 else ''}")
                
    except Exception as e:
        print(f"{RED}Error displaying network summary: {safe_error(e)}{RESET}")




def check_password_strength(password):
    """Check password strength with enhanced security criteria"""
    # Basic criteria
    length = len(password)
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in string.punctuation for c in password)
    
    # Advanced criteria
    unique_chars = len(set(password))
    has_sequential = any(
        password[i:i+3].lower() in "abcdefghijklmnopqrstuvwxyz0123456789" 
        for i in range(len(password) - 2)
    )
    has_repeated = any(
        password[i] == password[i+1] == password[i+2] 
        for i in range(len(password) - 2)
    )
    
    # Common patterns to avoid
    common_patterns = [
        "password", "123456", "qwerty", "admin", "welcome", 
        "letmein", "abc123", "monkey", "1234", "12345"
    ]
    has_common_pattern = any(pattern in password.lower() for pattern in common_patterns)

    # Calculate strength score (0-10)
    strength = 0
    if length >= 16:
        strength += 2
    elif length >= 12:
        strength += 1
    
    if has_upper:
        strength += 1
    if has_lower:
        strength += 1
    if has_digit:
        strength += 1
    if has_special:
        strength += 1
    
    # Bonus for unique characters
    if unique_chars >= length * 0.8:
        strength += 1
    
    # Penalty for sequential or repeated characters
    if has_sequential:
        strength -= 1
    if has_repeated:
        strength -= 1
    
    # Severe penalty for common patterns
    if has_common_pattern:
        strength -= 2
    
    # Ensure strength is within bounds
    strength = max(0, min(strength, 5))

    # Generate feedback
    feedback = []
    if length >= 12:
        feedback.append(f"✅  {GREEN}Password is at least 12 characters long.{RESET}")
    else:
        feedback.append(
            f"❌ {RED}Password should be at least 12 characters long.{RESET}"
        )

    if has_upper:
        feedback.append(
            f"✅  {GREEN}Password includes at least one uppercase letter.{RESET}"
        )
    else:
        feedback.append(
            f"❌ {RED}Password should include at least one uppercase letter.{RESET}"
        )

    if has_lower:
        feedback.append(
            f"✅  {GREEN}Password includes at least one lowercase letter.{RESET}"
        )
    else:
        feedback.append(
            f"❌ {RED}Password should include at least one lowercase letter.{RESET}"
        )

    if has_digit:
        feedback.append(f"✅  {GREEN}Password includes at least one digit.{RESET}")
    else:
        feedback.append(f"❌ {RED}Password should include at least one digit.{RESET}")

    if has_special:
        feedback.append(
            f"✅  {GREEN}Password includes at least one special character.{RESET}"
        )
    else:
        feedback.append(
            f"❌ {RED}Password should include at least one special character.{RESET}"
        )
        
    # Advanced feedback
    if unique_chars < length * 0.8:
        feedback.append(
            f"❌ {RED}Password has too many repeated characters.{RESET}"
        )
    
    if has_sequential:
        feedback.append(
            f"❌ {RED}Password contains sequential characters (like 'abc' or '123').{RESET}"
        )
    
    if has_repeated:
        feedback.append(
            f"❌ {RED}Password contains repeated characters (like 'aaa' or '111').{RESET}"
        )
    
    if has_common_pattern:
        feedback.append(
            f"❌ {RED}Password contains common patterns that are easy to guess.{RESET}"
        )

    return strength, feedback


def provide_suggestions(feedback):
    """Provide password improvement suggestions based on feedback"""
    suggestions = []
    
    # Basic suggestions based on feedback
    for tip in feedback:
        if "❌" in tip:
            if "12 characters long" in tip:
                suggestions.append("Use a longer password (12+ characters) for better security.")
            if "uppercase letter" in tip:
                suggestions.append("Add at least one uppercase letter (A-Z).")
            if "lowercase letter" in tip:
                suggestions.append("Add at least one lowercase letter (a-z).")
            if "digit" in tip:
                suggestions.append("Include at least one digit (0-9).")
            if "special character" in tip:
                suggestions.append(
                    "Include at least one special character (e.g., !, @, #, $, %, ^, &, *)."
                )
            if "repeated characters" in tip:
                suggestions.append(
                    "Use more unique characters instead of repeating the same ones."
                )
            if "sequential characters" in tip:
                suggestions.append(
                    "Avoid sequential patterns like 'abc', '123', or 'qwerty'."
                )
            if "common patterns" in tip:
                suggestions.append(
                    "Avoid common words and patterns that are easy to guess."
                )
    
    # Add general suggestions if we have few specific ones
    if len(suggestions) < 2:
        suggestions.append("Consider using a passphrase: a combination of random words.")
        suggestions.append("Mix uppercase, lowercase, numbers, and symbols throughout the password.")
    
    # Add a suggestion for password managers if appropriate
    if len(feedback) > 2 and "❌" in "".join(feedback):
        suggestions.append(
            "Consider using a password manager to generate and store strong, unique passwords."
        )
    
    return suggestions

def general_tips(feedback):
    """Generate general password tips based on feedback with enhanced security awareness"""
    all_tips = {
        "12 characters long": "Use a longer password (16+ characters) for better security.",
        "uppercase letter": "Use a mix of uppercase and lowercase letters throughout the password.",
        "lowercase letter": "Use a mix of uppercase and lowercase letters throughout the password.",
        "digit": "Include numbers in non-obvious positions (not just at the beginning or end).",
        "special character": "Include special symbols (~!@#$%^&*_-+=`) scattered throughout the password.",
        "common words": "Avoid using common words, names, dates, or easily guessable information.",
        "repeated characters": "Avoid repeating the same character multiple times (like 'aaa' or '111').",
        "sequential characters": "Avoid sequential patterns like 'abc', '123', or 'qwerty'.",
        "unique characters": "Use a variety of different characters for better security.",
    }

    # Check which criteria are already met
    existing_criteria = [tip.lower() for tip in feedback if "✅" in tip]
    existing_criteria_text = " ".join(existing_criteria)

    # Return tips for criteria that aren't met
    return [
        tip for key, tip in all_tips.items() 
        if key.lower() not in existing_criteria_text
    ]


def combined_tips(feedback):
    """Combine specific and general password tips with enhanced organization"""
    try:
        # Get specific suggestions based on feedback
        specific_suggestions = provide_suggestions(feedback)
        
        # Get general advice that applies
        general_advice = general_tips(feedback)
        
        # Combine suggestions, avoiding duplicates
        combined = specific_suggestions + [
            tip for tip in general_advice 
            if not any(tip.lower() in s.lower() for s in specific_suggestions)
        ]
        
        # Add a general security reminder if we have suggestions
        if combined:
            combined.append(
                "Remember: A strong password is your first line of defense against unauthorized access."
            )
            
        # Add a suggestion about password managers if not already included
        if not any("password manager" in tip.lower() for tip in combined):
            combined.append(
                "Consider using a password manager to generate and store strong, unique passwords for all your accounts."
            )
            
        return combined
        
    except Exception as e:
        # Return a basic set of tips if there's an error
        print(f"{RED}Error generating password tips: {safe_error(e)}{RESET}")
        return [
            "Use a mix of uppercase letters, lowercase letters, numbers, and symbols.",
            "Make your password at least 12 characters long.",
            "Avoid using personal information or common words.",
            "Use a different password for each account.",
            "Consider using a password manager."
        ]


def generate_password(length=12, allowed_symbols="~!@#$%^&*_-+=`", enhanced=True):
    """Generate a secure random password with enhanced security options
    
    Args:
        length: Length of the password (minimum 6, default 12)
        allowed_symbols: String of allowed special characters
        enhanced: Whether to use enhanced security features
        
    Returns:
        A secure random password as a string
    """
    try:
        # Enforce minimum length
        if length < 6:
            length = 12
            
        # Define allowed characters
        allowed_characters = string.ascii_letters + string.digits + allowed_symbols

        if enhanced:
            # Enhanced version with more security guarantees
            
            # Ensure at least one of each required character type
            password = [
                secrets.choice(string.ascii_uppercase),
                secrets.choice(string.ascii_lowercase),
                secrets.choice(string.digits),
                secrets.choice(allowed_symbols),
            ]
            
            # Add another special character for extra security if length allows
            if length >= 10:
                password.append(secrets.choice(allowed_symbols))
                
            # Add another digit for extra security if length allows
            if length >= 12:
                password.append(secrets.choice(string.digits))

            # Fill the rest of the password length with random choices from allowed characters
            while len(password) < length:
                password.append(secrets.choice(allowed_characters))

            # Shuffle the password to ensure randomness
            secrets.SystemRandom().shuffle(password)
            
            # Convert to string
            result = "".join(password)
            
            # Verify the password meets requirements
            has_upper = any(c.isupper() for c in result)
            has_lower = any(c.islower() for c in result)
            has_digit = any(c.isdigit() for c in result)
            has_symbol = any(c in allowed_symbols for c in result)
            
            # Regenerate if requirements aren't met (shouldn't happen, but just in case)
            if not (has_upper and has_lower and has_digit and has_symbol):
                return generate_password(length, allowed_symbols, enhanced)
                
            return result
            
        else:
            # Original version for backward compatibility
            password = [
                secrets.choice(string.ascii_uppercase),
                secrets.choice(string.ascii_lowercase),
                secrets.choice(string.digits),
                secrets.choice(allowed_symbols),
            ]

            while len(password) < length:
                password.append(secrets.choice(allowed_characters))

            secrets.SystemRandom().shuffle(password)
            return "".join(password)
            
    except Exception as e:
        # Fallback to a simpler but still secure method if there's an error
        print(f"{RED}Error generating password: {safe_error(e)}{RESET}")
        
        # Simple fallback method
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        return "".join(secrets.choice(chars) for _ in range(max(12, length)))


