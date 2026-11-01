import base64, json, subprocess, platform, psutil, socket, datetime, \
base64, uuid, traceback, sys, string, secrets, pyperclip, os, time, importlib.util
import keyboard as kb
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.fernet import Fernet

from cryptography.exceptions import InvalidTag
from main.SECURE_IO import copy_secret, copy_notice, reveal_secret, safe_error, mask, open_private
from main.VAULT_STORE import write_bytes_atomic
from main.INITIALIZE import  (vaultSetup, display_user_guide,
timeoutInput, load_salt, loadDatabase, vault,changeMasterPassword, 
changeAutoLogoutTimer, MIN_PASSWORD_LENGTH,load_ui_config,
MAX_PASSWORD_LENGTH, RECOMMENDED_PASSWORD_LENGTH, save_ui_config,
timeout_getpass, overwrite_db, timeoutCleanup, timeoutGlobalCode,
setup_secure_exit_handlers, secure_cleanup_common, interruptCleanup,
verify_export_encryption, generate_export_encryption, saveDatabase )

from main.SHARED_RESOURCES import (L_CYAN, BUNKER, DBLUE, 
FORANGE, FBLUE, FRED, GOLD, GREEN, RED, RESET, DPURPLE,
MUSTARD, VINTAGE, LPURPLE, PURPLE, CYAN )

from main.SHARED_RESOURCES import (title_art, clear_screen, subwm,
divider, check_terminal_size, display_watermark, display_bunker,
start_ip_fetch_thread, stop_ip_fetch_thread, self_destruct, safe_exit, spinning_line,
displayHeader, displaySection, get_uptime, check_vpn, combined_tips,
get_external_ip, check_password_strength, to_clipboard,get_network_connections,
format_connections,get_network_interfaces, display_network_summary)

# LOGIN / SETUP
def main(device_type='desktop'):

# RUN PROGRAM
    try:
        # Initialize UI with provided device type
        clear_screen()
        
        from main.SHARED_RESOURCES_MOBILE import ModernUI
        ui = ModernUI()
        
        print(f"{GREEN}Using desktop interface...{RESET}")
        time.sleep(1)
        
        # Now check if vault exists
        try:
            with open("Bunker.mmf", "rb"):
                pass
        except Exception:
            check_terminal_size()
            clear_screen()
            print(title_art)
            print(subwm)
            print(divider)
            print(
                f"{CYAN}\nBUNKER SETUP\n\nWelcome to Bunker!\n\n{GOLD}Detected device type: {device_type}{RESET}\n\n{RED}ALERT: Bunker.mmf was DESTROYED or not found in local directory... SETUP A NEW PASSWORD!{RESET}"
            )
            # Perform vault setup
            if not vaultSetup():
                return  # Return if setup was cancelled or failed

        # If mobile or tablet, redirect to MOBILE.py
        if device_type in ['mobile', 'tablet']:
            print(f"{GREEN}Detected {device_type} device. Launching mobile-friendly interface...{RESET}")
            import importlib.util
            # Load mobile module from main directory
            mobile_path = os.path.join(os.path.dirname(__file__), 'main', 'MOBILE.py')
            spec = importlib.util.spec_from_file_location("MOBILE", mobile_path)
            mobile = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mobile)
            return mobile.main()
            
        # For desktop, continue with BUNKER.py interface
        print(f"{GREEN}Detected desktop device. Using standard interface...{RESET}")
        
        # Vault exists at this point, continue with setup

        # Load salt and encrypted config
        # Prompt for password
        #entered_pass = timeoutInput("Enter your vault password to load your settings: ")

        # Derive the key using the entered password and the salt
        salt = load_salt()  # Load your salt from file
        #derived_key = vault.derive_key_hybrid(entered_pass, salt, entered_pass)

        # Decrypt the config using the derived key
        with open("bunker.cfg", "rb") as f:
            encrypted_config = f.read()
        #config = json.loads(vault.decrypt_data(encrypted_config, derived_key).decode())

        # Now you can access your settings
        #attempts = config.get("attempts", 0)
        #max_attempts = config.get("max_attempts", 3)
        #disable_ipv4 = config["settings"].get("disable_ipv4", True)
        #current_timeout = config.get("timeout_value", 60)

        # UI/UX: Loading animation and welcome
        check_terminal_size()
        clear_screen()
        print(title_art)
        print(subwm)
        print(divider)

        ui_config = load_ui_config()
        attempts = ui_config["attempts"]
        max_attempts = ui_config["max_attempts"]
        disable_ipv4 = ui_config["disable_ipv4"]
        current_timeout = ui_config["current_timeout"]

        if not disable_ipv4:
            spinning_line(1.4)
        else:
            spinning_line(0.5)
        
        check_terminal_size()
        clear_screen()
        display_bunker(disable_ipv4)
        print(f"{CYAN}BUNKER ACCESS{RESET}")
        print(divider)
        
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

        # Password verification loop
        hashed_pass = False
        timedOut = False

        while not hashed_pass:
            user_cmd = input(
                f"{GOLD}Do you want to show your password? (y/n) or exit(e): {RESET}"
            ).lower()

            if user_cmd == timeoutGlobalCode:
                timeoutCleanup()
                timedOut = True
                break

            if user_cmd == "e":
                clear_screen()
                print(title_art)
                print(subwm)
                print(divider)
                print(f"{GREEN}Exiting...{RESET}")
                sys.exit()

            if user_cmd not in ["y", "n"]:
                print(f"{RED} ** ALERT: Invalid input. Please enter y, n, or e. **{RESET}")
                continue

            # Get password input
            try:
                if user_cmd == "y":
                    entered_pass = timeoutInput(
                        f"{GOLD}Enter the bunker access code to proceed: {RESET}",
                        timeout=current_timeout
                    )
                else:  # user_cmd == "n"
                    entered_pass = timeout_getpass(
                        f"{GOLD}Enter the bunker access code to proceed:{RESET}",
                        current_timeout,
                    )
            except TimeoutError:
                timeoutCleanup()
                timedOut = True
                break

            # Derive key using entered password
            derived_key = vault.derive_key_hybrid(entered_pass, salt, entered_pass)
            # Try to decrypt config and verify password
            login_successful = False
            
            try:
                # Decrypt config
                config = json.loads(vault.decrypt_data(encrypted_config, derived_key).decode())
                
                # Update values from config
                #attempts = config.get("attempts", 0)
                #max_attempts = config.get("max_attempts", 3)
                #disable_ipv4 = config["settings"].get("disable_ipv4", True)
                #current_timeout = config.get("timeout_value", 60)
                
                #temporarily store ui_config to update attempts
                ui_config = load_ui_config()
                attempts = ui_config["attempts"]
                max_attempts = ui_config["max_attempts"]
                disable_ipv4 = ui_config["disable_ipv4"]
                current_timeout = ui_config["current_timeout"]
                
                # Get salt and verifier from config
                cSALT = base64.b64decode(config["salt"])
                cVERIFIER = base64.b64decode(config["verifier"])
                
                # Extra verification step
                if vault.verify_password_enhanced(entered_pass, cSALT, cVERIFIER):
                    login_successful = True
                else:
                    print(f"{RED} ** ALERT: Password verification failed. Try again. **{RESET}")
                    
            except InvalidTag:
                # Wrong key: the only failure that counts as a failed attempt.
                print(f"{RED} ** ALERT: Incorrect access password. Try again. **{RESET}")
            except Exception as e:
                # Any other error (unreadable config, bad data) is not a failed
                # login and must never count toward self-destruct.
                safe_exit(f"Could not check the password ({safe_error(e)})")

            if login_successful:
                # Reset attempts on successful login
                attempts = 0
                #temporarily store ui_config to update attempts
                ui_config["attempts"] = attempts
                save_ui_config(ui_config)
                
                #config["attempts"] = attempts
                
                #encrypted_config = vault.encrypt_data(json.dumps(config).encode(), derived_key)
                #with open("bunker.cfg", "wb") as f:
                #    f.write(encrypted_config)
                
                hashed_pass = derived_key
                break
            else:
                # Increment attempts and update config if we have it
                attempts += 1
                #temporarily store ui_config to update attempts
                ui_config["attempts"] = attempts
                save_ui_config(ui_config)
                # Display attempt counter
                if attempts == 1:
                    print(PURPLE + "Attempt 1 of 3" + RESET)
                elif attempts == 2:
                    print(PURPLE + "Attempt 2 of 3" + RESET)
                elif attempts == 3:
                    print(
                        PURPLE + f"Attempt 3 of 3 {RED} ** ALERT: Self-destructing after this attempt... **" + RESET
                    )
                
                # Save updated attempts to config if we have it
                #if config:
                    #config["attempts"] = attempts
                #    encrypted_config = vault.encrypt_data(json.dumps(config).encode(), derived_key)
                 #   with open("bunker.cfg", "wb") as f:
                 #       f.write(encrypted_config)
                
                # Check if max attempts reached
                if attempts >= max_attempts:
                    print(f"{CYAN} ** ALERT: Maximum attempts reached. Exiting... Unauthorized access system locked. **{RESET}")
                    self_destruct()
                
                

                # Clean up sensitive data for this iteration
                if 'entered_pass' in locals():
                    del entered_pass
                if 'cSALT' in locals():
                    del cSALT
                if 'cVERIFIER' in locals():
                    del cVERIFIER

        # Check if we timed out
        if timedOut:
            sys.exit(0)

        # If login successful, proceed with main application
        if hashed_pass:
            # Load database
            try:
                dataBase = loadDatabase(hashed_pass)
            except Exception as e:
                safe_exit(f"Failed to open the vault after login ({safe_error(e)})")

            # Clean up sensitive data
            if 'entered_pass' in locals():
                del entered_pass
            if 'cSALT' in locals():
                del cSALT
            if 'cVERIFIER' in locals():
                del cVERIFIER

            # Start the main application
            manage_passwords_and_notes(hashed_pass)

            # Clean up after main application
            if 'hashed_pass' in locals():
                del hashed_pass
            if 'dataBase' in locals():
                del dataBase

        # Always clean up sensitive data
        vault.secure_wipe()
                
    except KeyboardInterrupt:
        # This is a fallback in case the signal handler doesn't catch it
        interruptCleanup()
    except Exception as e:
        # Includes EOF (Ctrl+D) at a prompt. Never destroys the vault.
        safe_exit(f"Unexpected error ({safe_error(e)})")

    # Normal exit - if we reach here, exit cleanly
    print(f"{GREEN}Thank you for using BUNKER. ZEROMARKS Dev Team!{RESET}")
    secure_cleanup_common()
    sys.exit(0)


# Y intercept
def manage_passwords_and_notes(hashed_pass):
    """Manage passwords and notes with enhanced security but following original structure"""
    try:
        # Initialize vault and decrypt database
        clear_screen()

        try:
            # Ensure contents is in bytes format for consistent decryption
            with open("Bunker.mmf", "rb") as f:
                db_bytes = f.read()
            decrypted_data = vault.decrypt_data(db_bytes, hashed_pass)
            db = json.loads(decrypted_data.decode("utf-8"))
            
        except json.JSONDecodeError:
            raise ValueError("Database format is invalid")
        except Exception as e:
            raise ValueError(f"Database decryption failed: {safe_error(e)}")

        timedOut = False
        while not timedOut:
            check_terminal_size()
            clear_screen()
            print(title_art)
            ui_config = load_ui_config()
            disable_ipv4 = ui_config["disable_ipv4"]
            display_watermark(disable_ipv4)
            timeout_display = displayTimeout()
            print(
                f"{CYAN}🏚️  MAIN MENU 🏚️{FBLUE}  - {LPURPLE}Version: BETA{RESET} {FBLUE}- "
                + timeout_display
            )
            print(divider)
            user_cmd = print(
                f"\n{GOLD}(a){CYAN} 👤 Manage accounts {GOLD}|{RESET} {GOLD}(s){CYAN} 🗂️  Manage notes {GOLD}|{RESET} {GOLD}(d){CYAN} 💻 Display ip  {GOLD}|{RESET} {GOLD}(f){CYAN} 🪄 Generate password {GOLD}|{RESET} {GOLD}(g){CYAN} 📘 User guide* \n\n{GOLD}(c){CYAN} 🔑 Change login password {GOLD}|{RESET} {GOLD}(r){CYAN} 🔍 Check password strength {GOLD}|{RESET} {GOLD}(e){CYAN} 🖥️  System info {GOLD}|{RESET} {GOLD}(t){CYAN} ⏲️  Change auto-logout timer\n\n{GOLD}(x){PURPLE} 🚪 Logout\n{RESET}"
            )
            user_cmd = timeoutInput(f"{GOLD}Enter your choice? {RESET}")
            print("\n")

            # Ensure user input is lowercase
            if user_cmd != timeoutGlobalCode:
                user_cmd = user_cmd.lower()

            # Menu options
            if user_cmd == "a":
                # Get the latest database before passing to manager
                try:
                    with open("Bunker.mmf", "rb") as f:
                        latest_contents = f.read()
                    timedOut = main_pwd_manager(hashed_pass, latest_contents)
                except Exception as e:
                    # The old fallback re-ran the manager with `contents`,
                    # which is unset on the first pick; the NameError reached
                    # the outer handler, which wipes the vault. Report the
                    # error (read failure or a bug in the manager) and return
                    # to the menu instead.
                    print(f"{RED}** ALERT: Could not complete that action ({safe_error(e)}). Returning to the menu. **{RESET}")
                    time.sleep(2)
                    continue

            elif user_cmd == "s":
                # Get the latest database before passing to manager
                try:
                    with open("Bunker.mmf", "rb") as f:
                        latest_contents = f.read()
                    timedOut = main_note_manager(hashed_pass, latest_contents)
                except Exception as e:
                    # The old fallback re-ran the manager with `contents`,
                    # which is unset on the first pick; the NameError reached
                    # the outer handler, which wipes the vault. Report the
                    # error (read failure or a bug in the manager) and return
                    # to the menu instead.
                    print(f"{RED}** ALERT: Could not complete that action ({safe_error(e)}). Returning to the menu. **{RESET}")
                    time.sleep(2)
                    continue

            elif user_cmd == "d":
                timedOut = changeDisplayIp(hashed_pass, disable_ipv4)

            elif user_cmd == "g":
                timedOut = display_user_guide(hashed_pass, db)

            elif user_cmd == "f":
                timedOut = pwdGenerate(hashed_pass, db)

            elif user_cmd == "c":
                timedOut = changeMasterPassword(hashed_pass, db)

            elif user_cmd == "r":
                timedOut = check_password(hashed_pass, db)

            elif user_cmd == "e":
                timedOut = system_info(hashed_pass, db)

            elif user_cmd == "t":
                timedOut = changeAutoLogoutTimer(hashed_pass, db)

            elif user_cmd == "x":
                clear_screen()
                sys.exit()
                timedOut = True

            elif user_cmd == timeoutGlobalCode:
                timeoutCleanup()
                timedOut = True

            # After each operation, refresh the database if needed
            if not timedOut and (user_cmd in ["a", "s", "c"]):
                try:
                    # Re-read the database to ensure we have the latest version
                    with open("Bunker.mmf", "rb") as f:
                        contents = f.read()
                    # Update the db variable with the latest data
                    decrypted_data = vault.decrypt_data(contents, hashed_pass)
                    db = json.loads(decrypted_data.decode("utf-8"))
                except Exception as e:
                    print(f"{RED}** ALERT: Failed to refresh database: {safe_error(e)} **{RESET}")
                    input(f"{GOLD}Press ENTER to continue...{RESET}")

    except Exception as e:
        # Used to wipe the vault on any error here. Report and return; the
        # caller exits normally and the vault is left untouched.
        print(f"{RED}** ALERT: Failed to manage database: {safe_error(e)} **{RESET}")
        
    finally:
        # Secure cleanup of sensitive data
        try:
            if 'db' in locals(): del db
            if 'decrypted_data' in locals(): del decrypted_data
            if 'hashed_pass' in locals(): del hashed_pass
            vault.secure_wipe()
        except:
            pass

def displayTimeout():
    """Display the current timeout setting with enhanced security"""
    try:
        
        # Load timeout value with enhanced security
        current_timeout = vault.load_timeout_value()
        
        if current_timeout is not None and current_timeout > 0:
            return f"{CYAN}Auto-Logout is: {GREEN}ON{RESET}"
            # To show the actual timeout value: f"{CYAN}Auto-Logout: {GREEN}ON{RESET} ({GOLD}{current_timeout}{RESET} seconds)"
        else:
            return f"{CYAN}Auto-Logout is: {RED}OFF{RESET}"
    except Exception as e:
        # Fail silently but return a default value
        return f"{CYAN}Auto-Logout: {GOLD}Unknown{RESET}"
    
def changeDisplayIp(hashed_pass, disable_ipv4):
    """Change IP display settings with enhanced security"""
    try:
        while True:
            clear_screen()
            displayHeader(f"{CYAN}🌐 IP DISPLAY SETTING{RESET}")
            # Load current UI config
            ui_config = load_ui_config()
            disable_ipv4 = ui_config.get("disable_ipv4", True)

            # Print current state
            current_state = (
                f"{RED}Disabled{RESET}" if disable_ipv4 else f"{GREEN}Enabled{RESET}"
            )
            current_state_input = (
                f"{GOLD}Do you want to enable IP fetching? (type 'e' or '.c' to cancel): {RESET}"
                if disable_ipv4
                else f"{GOLD}Do you want to disable IP fetching? (type 'd' or '.c' to cancel): {RESET}"
            )

            print(f"{DBLUE}IP fetching current state: {current_state}{RESET}")

            while True:
                # Get user input with timeout
                toggle_choice = timeoutInput(
                    f"\n{GOLD}{current_state_input}{RESET}"
                ).lower()

                # Process user input and update the state
                if toggle_choice == ".c" or toggle_choice == timeoutGlobalCode:
                    print(f"{GOLD}Returning to the previous menu.{RESET}")
                    return True if toggle_choice == timeoutGlobalCode else False
                elif toggle_choice == "d":
                    if disable_ipv4:
                        print(
                            f"{RED}ALERT: No changes were made. The setting is already {RED}disabled{RESET}."
                        )
                    else:
                        disable_ipv4 = True
                        stop_ip_fetch_thread()
                        print(
                            f"{GREEN}IP fetching has been successfully {RED}disabled{GREEN}.{RESET}"
                        )
                        break  # Exit the loop if valid input is provided
                elif toggle_choice == "e":
                    if not disable_ipv4:
                        print(
                            f"{RED} ALERT: No changes were made. The setting is already {GREEN}enabled{RESET}."
                        )
                    else:
                        disable_ipv4 = False
                        start_ip_fetch_thread()
                        print(
                            f"{GREEN}** SUCCESS: IP fetching has been successfully enabled. **{RESET}"
                        )
                        break  # Exit the loop if valid input is provided
                else:
                    print(
                        f"{RED} **  ALERT: Invalid choice. Please enter 'd', 'e', or '.c' **{RESET}"
                    )

            # Save the updated setting with enhanced security
            try:
                ui_config["disable_ipv4"] = disable_ipv4
                save_ui_config(ui_config)
            except Exception as e:
                print(f"{RED}** ALERT: Failed to save UI config: {safe_error(e)} **{RESET}")

                # Save settings to settings file
             #   try:
            #        settings_data = json.dumps({
            #            "disable_ipv4": disable_ipv4,
            #            "version": "2.0"
            #        }).encode()
                    
            #        encrypted_settings = vault.encrypt_data(settings_data, key)
                    
                    # Write directly as bytes to ensure consistent format
             #       with open("settings.enc", "wb") as settings_file:
             #           settings_file.write(encrypted_settings)
             #   except Exception as e:
             #       print(f"{RED}** ALERT: Failed to save settings file: {safe_error(e)} **{RESET}")
                
                # Update database if needed
             #   try:
                    # Ensure contents is bytes
              #      if isinstance(contents, str):
              #          contents = contents.encode()
                        
                    # Decrypt the database
              #      decrypted_data = vault.decrypt_data(contents, hashed_pass)
              #      db = json.loads(decrypted_data.decode("utf-8"))
                    
                    # If db has settings section, update it
              #      if isinstance(db, dict) and "settings" in db:
               #         db["settings"]["disable_ipv4"] = disable_ipv4
                #        db["settings"]["last_modified"] = datetime.datetime.now().isoformat()
                        
                        # Encrypt the updated database
                 #       encrypted_db = vault.encrypt_data(json.dumps(db).encode(), hashed_pass)
                        
                        # Write directly as bytes to ensure consistent format
                 #       with open("Bunker.mmf", "wb") as f:
                  #          f.write(encrypted_db)
                #except Exception as e:
                 #   print(f"{RED}** ALERT: Failed to update database settings: {safe_error(e)} **{RESET}")
                    
           # except Exception as e:
            #    print(f"{RED}** ALERT: Failed to save settings: {safe_error(e)} **{RESET}")

            while True:
                userContinue = timeoutInput(
                    f"{GOLD}\nPress 'enter' to return to menu or type 'r' to retry...{RESET}"
                )
                if userContinue.lower() == "r":
                    break  # Exit the current loop to retry the entire changeDisplayIp process
                elif userContinue == "" or userContinue == timeoutGlobalCode:
                    return True if userContinue == timeoutGlobalCode else False
                else:
                    print(
                        f"{RED} ** ALERT: Invalid input. Please press 'enter' to continue or type 'r' to retry. **{RESET}"
                    )
    except Exception as e:
        print(f"{RED}** ALERT: Failed to change IP display settings: {safe_error(e)} **{RESET}")
        return False
    finally:
        # Clean up sensitive data
        if 'db' in locals(): del db
        if 'decrypted_data' in locals(): del decrypted_data
        if 'hashed_pass' in locals(): del hashed_pass
        if 'contents' in locals(): del contents
        vault.secure_wipe()

def pwdGenerate(hashed_pass, db):
    """Generate a secure random password with enhanced security"""
    try:

        
        while True:
            clear_screen()
            displayHeader(f"🪄 {CYAN}GENERATE RANDOM PASSWORD{RESET}")
            print(
                f"{DBLUE}Minimum password length: {GOLD}{MIN_PASSWORD_LENGTH}{RESET} characters{RESET}"
            )
            print(
                f"{DBLUE}Maximum password length: {GOLD}{MAX_PASSWORD_LENGTH}{RESET} characters{RESET}"
            )
            print(
                f"{DBLUE}Recommended password length: {GOLD}{RECOMMENDED_PASSWORD_LENGTH}{RESET} characters{RESET}"
            )
            print(
                f"\n{GOLD}This utility generates a random password of the specified length and copies it to your clipboard for 30 secs.{RESET}"
            )

            while True:
                pass_length_input = timeoutInput(
                    f"{GOLD}Password length (type (.c) to cancel): {RESET}"
                )
                
                # Handle timeout or cancel
                if pass_length_input == ".c" or pass_length_input == timeoutGlobalCode:
                    return False if pass_length_input != timeoutGlobalCode else True

                # Validate input is a number
                if not pass_length_input.isdigit():
                    clear_screen()
                    displayHeader(f"🪄 {CYAN}GENERATE RANDOM PASSWORD{RESET}")
                    print(
                        f"{RED} ** ALERT: Invalid input. Please enter a valid number. **{RESET}"
                    )
                    userContinue = timeoutInput(
                        f"\n{GOLD}Press 'enter' to return to menu or type 'r' to retry...{RESET}"
                    )
                    if userContinue == timeoutGlobalCode:
                        return True
                    if userContinue.lower() == "r":
                        break
                    else:
                        return False

                # Validate password length
                pass_length = int(pass_length_input)
                if pass_length < MIN_PASSWORD_LENGTH or pass_length > MAX_PASSWORD_LENGTH:
                    clear_screen()
                    displayHeader(f"🪄 {CYAN}GENERATE RANDOM PASSWORD{RESET}")
                    print(
                        f"{RED} ** ALERT: Password length must be between {MIN_PASSWORD_LENGTH} and {MAX_PASSWORD_LENGTH} characters. **{RESET}"
                    )
                    userContinue = timeoutInput(
                        f"\n{GOLD}Press 'enter' to return to menu or type 'r' to retry...{RESET}"
                    )
                    if userContinue == timeoutGlobalCode:
                        return True
                    if userContinue.lower() == "r":
                        break
                    else:
                        return False

                try:
                    # Generate password with enhanced security
                    password = generate_password(pass_length)
                    
                    # Display and copy to clipboard
                    clear_screen()
                    displayHeader(f"🪄 {CYAN}GENERATE RANDOM PASSWORD{RESET}")
                    reveal_secret("Generated Password: ", password)
                    print(to_clipboard(password))

                    # Ask user to continue or return
                    userContinue = timeoutInput(
                        f"\n{GOLD}Press 'enter' to return to menu or type 'r' to retry...{RESET}"
                    )
                    if userContinue == timeoutGlobalCode:
                        return True
                    if userContinue.lower() == "r":
                        break
                    else:
                        return False
                        
                except ValueError as e:
                    clear_screen()
                    displayHeader(f"🪄 {CYAN}GENERATE RANDOM PASSWORD{RESET}")
                    print(f"{RED} ** ALERT: {safe_error(e)} **{RESET}")
                    userContinue = timeoutInput(
                        f"\n{GOLD}Press 'enter' to return to menu or type 'r' to retry...{RESET}"
                    )
                    if userContinue == timeoutGlobalCode:
                        return True
                    if userContinue.lower() == "r":
                        break
                    else:
                        return False
    except Exception as e:
        print(f"{RED} ** ALERT: An error occurred: {safe_error(e)} **{RESET}")
        return False
    finally:
        # Clean up sensitive data
        if 'password' in locals(): del password
        if 'hashed_pass' in locals(): del hashed_pass
        vault.secure_wipe()

def check_password(hashed_pass, db):
    """Check password strength with enhanced security"""
    try:
        
        while True:
            clear_screen()
            displayHeader(f"{CYAN}🔍 CHECK A PASSWORD STRENGTH{RESET}")

            password = timeoutInput(
                f"{GOLD}Enter a password to check its strength (type (.c) to cancel): {RESET}"
            )

            # Handle timeout or cancel
            if password == ".c" or password == timeoutGlobalCode:
                print(" ** ALERT: Operation canceled. **")
                return False if password != timeoutGlobalCode else True

            # Check password length
            if len(password) < MIN_PASSWORD_LENGTH or len(password) > MAX_PASSWORD_LENGTH:
                num_char = len(password)
                strength, feedback = check_password_strength(password)
                clear_screen()
                displayHeader(f"{CYAN}🔍 CHECK A PASSWORD STRENGTH{RESET}")
                print(f"{GOLD}Feedback on your password:{RESET}\n")
                for tip in feedback:
                    print(tip)
                print(f"\n{GOLD}Password strength: {RED}weak{RESET}")
                print(
                    f"{GOLD}You entered a password with '{num_char}' characters. For your safety, we recommend something at least {MIN_PASSWORD_LENGTH} and {MAX_PASSWORD_LENGTH} characters long."
                )
                print(f"\n{DBLUE}Tips for choosing a strong password:{RESET}\n")
                suggestions = combined_tips(feedback)
                for suggestion in suggestions:
                    print(f"- {suggestion}")
            else:
                # Check password strength
                strength, feedback = check_password_strength(password)
                clear_screen()
                displayHeader(f"{CYAN}🔍 CHECK A PASSWORD STRENGTH{RESET}")
                print(f"{GOLD}Password strength checklist:{RESET}\n")
                for tip in feedback:
                    print(tip)
                if strength >= 4:
                    print(f"\n{GOLD}Password strength: {GREEN}Strong{RESET}")
                else:
                    print(f"\n{GOLD}Password strength: {RED}Weak{RESET}")
                    suggestions = combined_tips(feedback)
                    print(f"\n{DBLUE}Suggestions to improve your password:{RESET}\n")
                    for suggestion in suggestions:
                        print(f"{RESET}- {suggestion}{RESET}")

            # Ask user to continue or return
            userContinue = timeoutInput(
                f"{GOLD}\nPress 'enter' to return to menu or type 'r' to retry...{RESET}"
            )
            if userContinue == timeoutGlobalCode:
                return True
            if userContinue.lower() != "r":
                return False
                
    except Exception as e:
        print(f"{RED} ** ALERT: An error occurred: {safe_error(e)} **{RESET}")
        return False
    finally:
        # Clean up sensitive data
        if 'password' in locals(): del password
        if 'hashed_pass' in locals(): del hashed_pass
        vault.secure_wipe()

def system_info(hashed_pass, db):
    """Display system and network information with enhanced security"""
    try:
          
        # Display header
        displayHeader("🖥️  SYSTEM & NETWORK INFORMATION")
        print("⚠️  ** BEWARE PAGE DOES NOT TIME OUT ** ⚠️")

        # Display system information
        displaySection("System Information")
        try:
            uname = platform.uname()
            print(f"System: {uname.system}")
            print(f"Node Name: {uname.node}")
            print(f"Release: {uname.release}")
            print(f"Version: {uname.version}")
            print(f"Machine: {uname.machine}")
            print(f"Processor: {uname.processor}")
        except Exception as e:
            print(f"{RED}** ALERT: Error fetching system information: {safe_error(e)} **{RESET}")

        # Display hardware information
        displaySection("Hardware Information")
        try:
            print(f"🔹 CPU Usage: {psutil.cpu_percent(interval=1)}%")
            memory = psutil.virtual_memory()
            print(f"🔹 Total Memory: {memory.total / (1024 ** 3):.2f} GB")
            print(f"🔹 Available Memory: {memory.available / (1024 ** 3):.2f} GB")
            print(f"🔹 Memory Usage: {memory.percent}%")

            disk_usage = psutil.disk_usage("/")
            print(f"🔹 Total Disk Space: {disk_usage.total / (1024 ** 3):.2f} GB")
            print(f"🔹 Used Disk Space: {disk_usage.used / (1024 ** 3):.2f} GB")
            print(f"🔹 Free Disk Space: {disk_usage.free / (1024 ** 3):.2f} GB")
            print(f"🔹 Disk Usage: {disk_usage.percent}%")
        except Exception as e:
            print(f"{RED}** ALERT: Error fetching hardware information: {safe_error(e)} **{RESET}")

        print("\n⚠️  ** BEWARE PAGE DOES NOT TIME OUT ** ⚠️")

        # Display network information section
        displaySection("Network Information")
        while True:
            network_choice = (
                input(
                    f"{GOLD}\nDo you want to see network details? (y/n) (type (.c) to cancel): {RESET}"
                )
                .strip()
                .lower()
            )
            if network_choice in ["y", "n", ".c"]:
                if network_choice == ".c":
                    print("Returning to menu")
                    return False
                break
            else:
                print(
                    f"{RED} ** ALERT: Invalid input. Please enter 'y', 'n', or '.c' to cancel. **{RESET}"
                )

        if network_choice == "y":
            try:
                # Display network interfaces
                print("\n🔹 Network Interfaces:")
                for interface, addrs in psutil.net_if_addrs().items():
                    addresses = []
                    for addr in addrs:
                        if addr.family == socket.AF_INET:  # IPv4
                            addresses.append(f"IPv4: {addr.address}")
                        elif addr.family == socket.AF_INET6:  # IPv6
                            addresses.append(f"IPv6: {addr.address}")
                        elif addr.family == psutil.AF_LINK:  # MAC
                            addresses.append(f"MAC: {addr.address}")
                    print(f"🔹 {interface}: {', '.join(addresses)}")
                
                # Ask for detailed network connections
                print(f"\n⚠️  ** BEWARE PAGE DOES NOT TIME OUT ** ⚠️ \n")
                while True:
                    user_choice = (
                        input(
                            f"{GOLD}Do you want to see detailed network connections? (y/n) (type (.c) to cancel): {RESET}"
                        )
                        .strip()
                        .lower()
                    )
                    if user_choice in ["y", "n", ".c"]:
                        if user_choice == ".c":
                            print("Returning to menu")
                            return False
                        break
                    else:
                        print(
                            f"{RED} ** ALERT: Invalid input. Please enter 'y', 'n', or '.c' to cancel. **{RESET}"
                        )

                if user_choice == "y":
                    try:
                        # Try to get network connections with limited info if not root
                        try:
                            # First try to get full connections (requires root/admin)
                            connections = psutil.net_connections(kind='inet')
                            
                            # Display connections in a formatted way
                            print("\n🔹 Active Network Connections:")
                            print(f"{'Local Address':<25} {'Remote Address':<25} {'Status':<15} {'PID':<10}")
                            print("-" * 75)
                            
                            for conn in connections:
                                if conn.laddr:
                                    laddr = f"{conn.laddr.ip}:{conn.laddr.port}"
                                else:
                                    laddr = "N/A"
                                    
                                if conn.raddr:
                                    raddr = f"{conn.raddr.ip}:{conn.raddr.port}"
                                else:
                                    raddr = "N/A"
                                    
                                status = conn.status if conn.status else "N/A"
                                pid = conn.pid if conn.pid else "N/A"
                                
                                print(f"{laddr:<25} {raddr:<25} {status:<15} {pid:<10}")
                                
                        except PermissionError:
                            # If permission denied, try alternative approach
                            print(f"{RED}** ALERT: Permission denied for detailed connections. **{RESET}")
                            print(f"{GOLD}Showing limited network information instead...{RESET}\n")
                            
                            # On Unix-like systems, try using netstat through subprocess
                            if platform.system() != "Windows":
                                try:
                                    print("\n🔹 Active Network Connections (Limited Info):")
                                    # Use netstat with limited options that don't require root
                                    result = subprocess.run(
                                        ["netstat", "-an"], 
                                        capture_output=True, 
                                        text=True, 
                                        check=False
                                    )
                                    if result.returncode == 0:
                                        # Format and display the output
                                        lines = result.stdout.split('\n')
                                        # Print header lines and first 20 connections
                                        header_found = False
                                        count = 0
                                        for line in lines:
                                            if 'Proto' in line or 'Active' in line:
                                                print(line)
                                                header_found = True
                                            elif header_found and line.strip() and count < 20:
                                                print(line)
                                                count += 1
                                        
                                        if count >= 20:
                                            print(f"\n{GOLD}(Showing first 20 connections only){RESET}")
                                    else:
                                        raise subprocess.SubprocessError("Command failed")
                                except Exception as e:
                                    print(f"{RED}** ALERT: Could not get network information: {safe_error(e)} **{RESET}")
                                    print(f"{GOLD}To see detailed network connections, run this script with administrator privileges.{RESET}")
                            else:
                                # On Windows, try using netstat through subprocess
                                try:
                                    print("\n🔹 Active Network Connections (Limited Info):")
                                    result = subprocess.run(
                                        ["netstat", "-an"], 
                                        capture_output=True, 
                                        text=True, 
                                        check=False
                                    )
                                    if result.returncode == 0:
                                        # Format and display the output
                                        lines = result.stdout.split('\n')
                                        # Print header lines and first 20 connections
                                        header_found = False
                                        count = 0
                                        for line in lines:
                                            if 'Proto' in line or 'Active' in line:
                                                print(line)
                                                header_found = True
                                            elif header_found and line.strip() and count < 20:
                                                print(line)
                                                count += 1
                                        
                                        if count >= 20:
                                            print(f"\n{GOLD}(Showing first 20 connections only){RESET}")
                                    else:
                                        raise subprocess.SubprocessError("Command failed")
                                except Exception as e:
                                    print(f"{RED}** ALERT: Could not get network information: {safe_error(e)} **{RESET}")
                                    print(f"{GOLD}To see detailed network connections, run this script with administrator privileges.{RESET}")
                    except Exception as e:
                        print(f"{RED}** ALERT: Error fetching network connections: {safe_error(e)} **{RESET}")
                        print(f"{GOLD}To see detailed network connections, run this script with administrator privileges.{RESET}")
            except Exception as e:
                print(f"{RED}** ALERT: Error fetching network information: {safe_error(e)} **{RESET}")

        print("\n⚠️  ** BEWARE PAGE DOES NOT TIME OUT ** ⚠️")

        # Display system uptime and addresses section
        displaySection("System Uptime and Addresses")
        
        # Get hostname safely
        try:
            hostname = socket.gethostname()
            print(f"\n🔹 Hostname: {hostname}")
        except Exception as e:
            print(f"{RED} ** ALERT: Error fetching hostname: {safe_error(e)} **{RESET}")
            hostname = "Unknown"
        
        # Get local IP safely
        try:
            # Try multiple methods to get local IP
            ip_address = None
            
            # Method 1: Using socket
            try:
                ip_address = socket.gethostbyname(hostname)
            except:
                pass
                
            # Method 2: Using a socket connection (more reliable)
            if not ip_address:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(("8.8.8.8", 80))
                    ip_address = s.getsockname()[0]
                    s.close()
                except:
                    pass
            
            # Method 3: Using psutil
            if not ip_address:
                for interface, addrs in psutil.net_if_addrs().items():
                    if interface != 'lo':  # Skip loopback
                        for addr in addrs:
                            if addr.family == socket.AF_INET:
                                ip_address = addr.address
                                break
                        if ip_address:
                            break
                            
            if not ip_address:
                ip_address = "Unknown"
        except Exception as e:
            print(f"{RED} ** ALERT: Error determining local IP: {safe_error(e)} **{RESET}")
            ip_address = "Unknown"
        
        # Get external IP safely
        try:
            external_ip = get_external_ip()
            if not external_ip:
                external_ip = "Unknown"
        except Exception as e:
            print(f"{RED} ** ALERT: Error fetching external IP: {safe_error(e)} **{RESET}")
            external_ip = "Unknown"
        
        # Ask if user wants to see IP addresses
        if network_choice == "y":
            while True:
                ip_choice = (
                    input(
                        f"{GOLD}\nDo you want to see your IP addresses? (y/n) (type (.c) to cancel): {RESET}"
                    )
                    .strip()
                    .lower()
                )
                if ip_choice in ["y", "n", ".c"]:
                    if ip_choice == "y":
                        print(f"🔹 Local IP Address: {ip_address}")
                        print(f"🔹 External IP Address: {external_ip}")
                    elif ip_choice == ".c":
                        print("Returning to menu")
                        return False
                    break
                else:
                    print(
                        f"{RED} ** ALERT: Invalid input. Please enter 'y', 'n', or '.c' to cancel. **{RESET}"
                    )

        # Check VPN status safely
        try:
            vpn_status = check_vpn()
            print(f"🔹 VPN Status: {'Connected' if vpn_status else 'Not connected'}")
        except Exception as e:
            print(f"{RED} ** ALERT: Error checking VPN status: {safe_error(e)} **{RESET}")

        # Get uptime safely
        try:
            uptime = get_uptime()
            print(f"🔹 System Uptime: {uptime}")
        except Exception as e:
            print(f"{RED} ** ALERT: Error fetching uptime: {safe_error(e)} **{RESET}")

        userContinue = input(f"\n{GOLD}Press 'enter' to return to menu... {RESET}")
        return False
        
    except Exception as e:
        print(f"{RED}** ALERT: Error displaying system information: {safe_error(e)} **{RESET}")
        return False
        
    finally:
        # Clean up sensitive data
        if 'hashed_pass' in locals(): del hashed_pass
        if 'db' in locals(): del db
        if 'external_ip' in locals(): del external_ip
        if 'ip_address' in locals(): del ip_address
        vault.secure_wipe()
# Always base64-decode before decrypting (for consistency)
def decode_and_decrypt(field,info,hashed_pass):
    val = info.get(field, "N/A")
    if val == "N/A":
        return "N/A"
    if isinstance(val, str):
        try:
            val_bytes = base64.b64decode(val)
        except Exception:
            val_bytes = val.encode()  # fallback for legacy data
    else:
        val_bytes = val
    return vault.decrypt_data(val_bytes, hashed_pass).decode("utf-8")

def decode_and_decrypt_tag(tag, hashed_pass):
    if tag == "N/A":
        return "N/A"
    if isinstance(tag, str):
        try:
            tag_bytes = base64.b64decode(tag)
        except Exception:
            tag_bytes = tag.encode()
    else:
        tag_bytes = tag
    return vault.decrypt_data(tag_bytes, hashed_pass).decode("utf-8")

def decrypt_note(note, hashed_pass):
    decrypted = {
        'title': decode_and_decrypt('title', note, hashed_pass),
        'content': decode_and_decrypt('content', note, hashed_pass),
        'tags': [decode_and_decrypt_tag(tag, hashed_pass) for tag in note.get('tags', [])]
    }
    for field in ['favorite', 'private']:
        if field in note:
            decrypted[field] = note[field]
    return decrypted

# Profile Display
def main_pwd_manager(hashed_pass, contents):
    """Main password manager interface with enhanced security but following original structure"""
    try:
        # Initialize vault
        clear_screen()
        
        # Decrypt database with enhanced security
        try:
            # Handle string input for contents (from file read)
            if isinstance(contents, str):
                contents = contents.encode()
                
            decrypted_data = vault.decrypt_data(contents, hashed_pass)
            db = json.loads(decrypted_data.decode("utf-8"))
        except Exception as e:
            raise ValueError(f"Failed to decrypt database: {safe_error(e)}")
        
        timedOut = False
        while not timedOut:
            try:
                check_terminal_size()
                clear_screen()
                print(title_art)
                ui_config = load_ui_config()
                disable_ipv4 = ui_config["disable_ipv4"]
                #temp
                #disable_ipv4 = vault.manage_config(hashed_pass)["settings"].get("disable_ipv4", True)
                display_watermark(disable_ipv4)
                timeout_display = displayTimeout()
                print(
                    f"{L_CYAN} 👤 ACCOUNT MANAGER{FBLUE} - {LPURPLE}Version: BETA {RESET}{FBLUE}- "
                    + timeout_display
                )
                print(divider)
                # {DBLUE}(d)elete profile data\n{PURPLE}e(x)it\n{RESET}"
                user_cmd = print(
                    f"{L_CYAN}\n{GOLD}(a){L_CYAN} ✏️  Add profile {GOLD}|{RESET} {GOLD}(s){L_CYAN} ⭐ Favorite profiles {GOLD}|{RESET} {GOLD}(d){L_CYAN} 🗑️  Delete profile {GOLD}|{RESET} {GOLD}(f){L_CYAN} 🔍 Find profile {GOLD}|{RESET} {GOLD}(c){L_CYAN} ⬆️  Export/Import \n\n{GOLD}(r){L_CYAN} 📖 Read all profiles {GOLD}|{RESET} {GOLD}(e){L_CYAN} 🖍️  Edit profile {GOLD}|{RESET}  🏷️  {GOLD}(t){L_CYAN} Tags folder {GOLD}|{RESET} {GOLD}(x){PURPLE} 🔙 Back\n{RESET}"
                )
                user_cmd = timeoutInput(f"{GOLD}What would you like to do? {RESET}")
                print("\n")

                # Ensure user input is lowercase
                if user_cmd == timeoutGlobalCode:
                    timeoutCleanup()
                    timedOut = True
                    continue
                    
                user_cmd = user_cmd.lower()

                # Process user commands
                if user_cmd == "a":
                    timedOut = addProfile(hashed_pass, db)

                elif user_cmd == "s":
                    timedOut = displayFavorites(hashed_pass, db)

                elif user_cmd == "d":
                    timedOut = deleteProfileData(hashed_pass, db)

                elif user_cmd == "f":
                    timedOut = findProfileData(hashed_pass, db)

                elif user_cmd == "c":
                    timedOut = manageProfiles(hashed_pass, db)

                elif user_cmd == "r":
                    timedOut = readAllProfiles(hashed_pass, db)

                elif user_cmd == "e":
                    timedOut = editProfileData(hashed_pass, db)

                elif user_cmd == "t":
                    timedOut = tagProfiles(hashed_pass, db)

                elif user_cmd == "x":
                    # Return to parent menu without setting timedOut
                    return False

            except Exception as e:
                print(f"{RED}** ALERT: Operation failed: {safe_error(e)} **{RESET}")
                input(f"{GOLD}Press ENTER to continue...{RESET}")

    except Exception as e:
        print(f"{RED}** ALERT: Failed to manage accounts: {safe_error(e)} **{RESET}")
        return False
        
    finally:
        # Secure cleanup of sensitive data
        try:
            if 'db' in locals(): del db
            if 'decrypted_data' in locals(): del decrypted_data
            if 'hashed_pass' in locals(): del hashed_pass
            vault.secure_wipe()
        except:
            pass
            
    return timedOut

def addProfile(hashed_pass, db):
    """Add a new profile with enhanced security and robust input validation"""
    try:
        current_timeout = vault.manage_config(hashed_pass)["timeout_value"]
        while True:
            clear_screen()
            displayHeader(f"{CYAN}✏️  ADD A PROFILE{RESET}")
            profile_data = {}

            # Domain input
            while True:
                add_domain = timeoutInput(
                    f"{GOLD}Website domain name (type (.c) to cancel): {RESET}"
                )
                if add_domain == ".c":
                    print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                    return False
                elif add_domain == timeoutGlobalCode:
                    timeoutCleanup()
                    return True
                elif not add_domain.strip():
                    print(f"{RED} ** ALERT: Invalid input. Please enter a valid domain name or (.c) to cancel. **{RESET}")
                    continue
                profile_data['domain'] = add_domain
                break

            # Email input
            while True:
                add_email = timeoutInput(
                    f"{GOLD}Email address (Press 'enter' to skip, type (.c) to cancel): {RESET}"
                )
                if add_email == ".c":
                    print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                    return False
                elif add_email == timeoutGlobalCode:
                    timeoutCleanup()
                    return True
                profile_data['email'] = add_email if add_email.strip() else "N/A"
                break

            # Username input
            while True:
                add_user = timeoutInput(
                    f"{GOLD}Username (Press 'enter' to skip, type (.c) to cancel): {RESET}"
                )
                if add_user == ".c":
                    print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                    return False
                elif add_user == timeoutGlobalCode:
                    timeoutCleanup()
                    return True
                profile_data['username'] = add_user if add_user.strip() else "N/A"
                break

            # Password input with visibility choice
            add_password = ""
            while True:
                user_input = timeoutInput(
                    f"{GOLD}Do you want to show your password while typing? (y/n) (type (.c) to cancel): {RESET}"
                ).lower()
                if user_input == timeoutGlobalCode:
                    timeoutCleanup()
                    return True
                if user_input == ".c":
                    return False
                if user_input not in ["y", "n"]:
                    print(f"{RED}** ALERT: Invalid input. Please enter 'y' or 'n'.**{RESET}")
                    continue
                try:
                    if user_input == "n":
                        add_password = timeout_getpass(
                            f"{GOLD}Enter the password (type (.g) to generate, type (.c) to cancel): {RESET}",
                            current_timeout,
                        )
                    else:  # user_input == "y"
                        add_password = timeoutInput(
                            f"{GOLD}Enter the password (type (.g) to generate, type (.c) to cancel): {RESET}"
                        )
                    if add_password == ".c":
                        return False
                    elif add_password == timeoutGlobalCode:
                        timeoutCleanup()
                        return True
                    if add_password == ".g":
                        add_password = generate_password(RECOMMENDED_PASSWORD_LENGTH)
                        profile_data['password'] = add_password
                        break
                    elif not add_password.strip():
                        print(f"{RED}** ALERT: Password input interrupted. Please try again.**{RESET}")
                        continue
                    else:
                        profile_data['password'] = add_password
                        break
                except TimeoutError:
                    print(f"{RED}** ALERT: Password input timed out. Please try again.**{RESET}")
                    timeoutCleanup()
                    return True

            # Favorite profile input
            is_favorite = False
            while True:
                add_favorite = timeoutInput(
                    f"{GOLD}Mark this profile as a favorite? (y/n) (type (.c) to cancel): {RESET}"
                ).lower()
                if add_favorite == ".c":
                    print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                    return False
                elif add_favorite == timeoutGlobalCode:
                    timeoutCleanup()
                    return True
                elif add_favorite == "y":
                    is_favorite = True
                    profile_data['favorite'] = True
                    break
                elif add_favorite == "n":
                    profile_data['favorite'] = False
                    break
                else:
                    print(f"{RED} ** ALERT: Invalid input. Please enter 'y' or 'n'. **{RESET}")

            # Save the profile
            try:
                if not all(k in profile_data for k in ['domain', 'password']):
                    raise ValueError("Missing required profile fields")
                profile_id = str(uuid.uuid4())
                encrypted_domain = base64.b64encode(vault.encrypt_data(profile_data['domain'].encode(), hashed_pass)).decode("utf-8")
                encrypted_email = base64.b64encode(vault.encrypt_data(profile_data['email'].encode(), hashed_pass)).decode("utf-8")
                encrypted_user = base64.b64encode(vault.encrypt_data(profile_data['username'].encode(), hashed_pass)).decode("utf-8")
                encrypted_password = base64.b64encode(vault.encrypt_data(profile_data['password'].encode(), hashed_pass)).decode("utf-8")
                db[profile_id] = {
                    "domain": encrypted_domain,
                    "email": encrypted_email,
                    "username": encrypted_user,
                    "password": encrypted_password,
                    "favorite": profile_data.get('favorite', False),
                }
                encrypted_db = vault.encrypt_data(json.dumps(db).encode(), hashed_pass)
                write_bytes_atomic("Bunker.mmf", encrypted_db)
                clear_screen()
                displayHeader(f"{CYAN}✏️  ADD PROFILE{RESET}")
                print(f"{GREEN}** SUCCESS: Profile successfully created! **{RESET}")
                print(f"\n{GOLD}Created profile has been added to {LPURPLE}(Domain: {profile_data['domain']}){GOLD} successfully! {RESET}")
                userContinue = timeoutInput(
                    f"{GOLD}\nPress 'enter' to return to menu or type 'r' to add another profile...{RESET}"
                )
                if userContinue == timeoutGlobalCode:
                    timeoutCleanup()
                    return True
                if userContinue.lower() == "r":
                    continue
                return False
            except Exception as e:
                print(f"{RED}Failed to add profile. Error: {safe_error(e)}{RESET}")
                userContinue = timeoutInput(
                    f"{GOLD}\nPress 'enter' to return to menu or type 'r' to retry...{RESET}"
                )
                if userContinue == timeoutGlobalCode:
                    timeoutCleanup()
                    return True
                if userContinue.lower() == "r":
                    continue
                return False
    except Exception as e:
        print(f"{RED}** ALERT: Failed to add profile: {safe_error(e)} **{RESET}")
        return False
    finally:
        if 'add_password' in locals(): del add_password
        if 'profile_data' in locals() and 'password' in profile_data: del profile_data['password']
        if 'profile_data' in locals(): del profile_data
        if 'hashed_pass' in locals(): del hashed_pass
        vault.secure_wipe()
def generate_password(length, allowed_symbols=string.punctuation):
    characters = string.ascii_letters + string.digits + allowed_symbols
    return "".join(secrets.choice(characters) for _ in range(length))

#fix prints 
def displayFavorites(hashed_pass, db):
    """Display favorite profiles with enhanced security"""
    try:
        clear_screen()
        displayHeader(f"{CYAN}⭐ FAVORITE PROFILES{RESET}")
        print(f"{GOLD}Searching for... 'FAVORITE PROFILES':{RESET}\n")

        # Ensure db is properly loaded as a dictionary
        if isinstance(db, bytes):
            try:
                decrypted_data = vault.decrypt_data(db, hashed_pass)
                db = json.loads(decrypted_data.decode("utf-8"))
            except Exception as e:
                print(f"{RED} ** ALERT: Error loading database: {safe_error(e)} **{RESET}")
                return False

        # Filter favorite profiles
        favorites = {k: v for k, v in db.items() if v.get("favorite", False)}
        decrypted_profiles = []
        index = 1

        for profile_id, info in favorites.items():
            try:
                # Decrypt profile data with enhanced security
                domain = decode_and_decrypt("domain", info, hashed_pass)
                username = decode_and_decrypt("username", info, hashed_pass)
                email = decode_and_decrypt("email", info, hashed_pass)
                is_favorite = "⭐" if info.get("favorite", False) else ""
                decrypted_profiles.append(
                    (index, profile_id, domain, username, email, is_favorite)
                )
                index += 1
            except Exception as e:
                # Silently skip profiles that cannot be decrypted
                continue

        num_favorites = len(decrypted_profiles)
        print(
            f"{GOLD}Found {num_favorites} favorite profile{'' if num_favorites == 1 else 's'}:{RESET}\n"
        )

        if num_favorites == 0:
            print(
                f"{RED} ** ALERT: No favorite profiles available to display. ADD OR EDIT A PROFILE! **{RESET}"
            )
            userContinue = timeoutInput(f"{GOLD}\nPress 'enter' to return to menu...{RESET}")
            return False if userContinue != timeoutGlobalCode else True
        else:
            for idx, profile in enumerate(decrypted_profiles, 1):
                domain, username, email, is_favorite = (
                    profile[2],
                    profile[3],
                    profile[4],
                    profile[5],
                )
                print(
                    f"{CYAN}Profile {idx} {is_favorite}{GOLD} | {LPURPLE}Domain: {domain}{RESET} \n{DBLUE}Username: {RESET}{username} {GOLD}, {DBLUE}Email:{RESET} {email}\n"
                )

            while True:
                profile_range = f"1-{num_favorites}" if num_favorites > 1 else "1"
                view_password = timeoutInput(
                    f"{GOLD}\nSelect the profile to view its password ({profile_range}) or type .c to cancel: {RESET}"
                )
                if view_password == ".c" or view_password == timeoutGlobalCode:
                    return False if view_password != timeoutGlobalCode else True
                elif view_password.isdigit():
                    selected_index = int(view_password)
                    if 1 <= selected_index <= num_favorites:
                        selected_profile = decrypted_profiles[selected_index - 1]
                        profile_id = selected_profile[1]
                        domain = selected_profile[2]
                        username = selected_profile[3]
                        email = selected_profile[4]
                        is_favorite = selected_profile[5]
                        try:
                            # Decrypt password with enhanced security
                            password = decode_and_decrypt("password", favorites[profile_id], hashed_pass)
                            while True:
                                clear_screen()
                                displayHeader(f"{CYAN}⭐ VIEW FAVORITE PROFILES{RESET}")
                                print(f"{GOLD}You selected profile:\n{RESET}")
                                print(
                                    f"{CYAN}Profile {selected_index} {is_favorite} {GOLD}|{LPURPLE} Domain: {domain}\n{DBLUE}Username:{RESET} {username} {GOLD}, {DBLUE}Email: {RESET}{email}\n"
                                )

                                copy_choice = timeoutInput(
                                    f"{GOLD}Type 'v' to view, 'c' to copy to clipboard, or '.c' to cancel\nDo you want to display the password or just copy it? : {RESET}"
                                ).lower()
                                
                                if copy_choice == timeoutGlobalCode:
                                    return True
                                    
                                if copy_choice == "v":
                                    print(
                                        f"\n{GOLD}Password requested for {LPURPLE}{domain}!{RESET}"
                                    )
                                    reveal_secret(f"{GREEN}Password request granted! \n\n{DBLUE}Password:{RESET} ", f"{password}{RESET}\n")
                                    break
                                elif copy_choice == "c":
                                    _copied = copy_secret(password)
                                    print(
                                        (f"{GREEN}{copy_notice('Password')}{RESET}\n" if _copied else f"{RED}** ALERT: Could not access the clipboard. **{RESET}\n")
                                    )
                                    break
                                elif copy_choice == ".c":
                                    return False
                                else:
                                    print(
                                        f"{RED} ** ALERT: Invalid option. Please enter 'v' to view, 'c' to copy, or '.c' to cancel. **{RESET}"
                                    )

                            while True:
                                user_choice = timeoutInput(
                                    f"{GOLD}Press 'enter' to return to the main menu or type 'r' to retry... {RESET}"
                                )
                                if user_choice == timeoutGlobalCode:
                                    return True
                                if user_choice == "r":
                                    return displayFavorites(hashed_pass, db)
                                elif user_choice == "":
                                    return False  # Return to the main menu
                                else:
                                    print(
                                        f"{RED} ** ALERT: Invalid input. Please press 'enter' to return to the main menu or type 'r' to retry. **{RESET}"
                                    )
                        except Exception as e:
                            print(
                                f"{RED} ** ALERT: Error reading password for profile '{selected_index}': {safe_error(e)} **{RESET}"
                            )
                            continue
                    else:
                        print(f"{RED} ** ALERT: Invalid profile number. **{RESET}")
                else:
                    print(
                        f"{RED} ** ALERT: Invalid input. Please enter a valid profile number or '.c' to cancel. **{RESET}"
                    )

        userContinue = timeoutInput(f"{GOLD}\nPress 'enter' to return to menu...{RESET}")
        return False if userContinue != timeoutGlobalCode else True
        
    except Exception as e:
        print(f"{RED}** ALERT: Failed to display favorites: {safe_error(e)} **{RESET}")
        return False
        
    finally:
        # Clean up sensitive data
        if 'password' in locals(): del password
        if 'hashed_pass' in locals(): del hashed_pass
        if 'decrypted_profiles' in locals(): del decrypted_profiles
        vault.secure_wipe()

def editProfileData(hashed_pass, db):
    """Edit profile data with enhanced security"""
    try:
        # Define current_timeout here to avoid undefined variable errors.
        current_timeout = vault.manage_config(hashed_pass)["timeout_value"]
        
        while True:
            clear_screen()
            displayHeader(f"{CYAN}🖍️  EDIT A PROFILE{RESET}")
            edit_domain = timeoutInput(
                f"{GOLD}Leave empty to show all, type (.c) to cancel.\nEnter a word or exact domain of the profile you would like to search for: {RESET}"
            )
            if edit_domain == ".c" or edit_domain == timeoutGlobalCode:
                print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                print("Returning to menu")
                return False if edit_domain != timeoutGlobalCode else True

            # Find profiles matching the domain or show all if input is empty
            if edit_domain.strip() == "":
                matching_profiles = {k: v for k, v in db.items() if "username" in v}
                clear_screen()
                displayHeader(f"{CYAN}🖍️  EDIT A PROFILE{RESET}")
                print(f"{GOLD}Showing all profiles as no domain was provided.{RESET}")
                print(f"{GOLD}Searching for... 'All Profiles':{RESET}\n")
            else:
                # Check if the input is a substring of the domain or part of other fields
                matching_profiles = {}
                for k, v in db.items():
                    if any(field in v for field in ["domain", "username", "email"]):
                        try:
                            # Check if search term is in any of the fields
                            for field in ["domain", "username", "email"]:
                                if field in v:
                                    decrypted_field = decode_and_decrypt(field, v, hashed_pass)
                                    if edit_domain.lower() in decrypted_field.lower():
                                        matching_profiles[k] = v
                                        break
                        except Exception:
                            # Skip profiles that can't be decrypted
                            continue
                            
                clear_screen()
                displayHeader(f"{CYAN}🖍️  EDIT A PROFILE{RESET}")
                print(f"{GOLD}Searching profiles for... '{edit_domain}':{RESET}\n")

            if not matching_profiles:
                print(
                    f"{GOLD}Found {len(matching_profiles)} matching profile{'s' if len(matching_profiles) > 1 else ''}:{RESET}\n"
                )
                print(
                    f"{RED} ** ALERT: Unable to find any profiles with input: '{edit_domain}' **{RESET}"
                )
                userContinue = timeoutInput(
                    f"{GOLD}\nPress 'enter' to return to menu...{RESET}"
                )
                return False if userContinue != timeoutGlobalCode else True

            print(
                f"{GOLD}Found {len(matching_profiles)} matching profile{'s' if len(matching_profiles) > 1 else ''}:{RESET}"
            )
            for i, (profile_id, info) in enumerate(matching_profiles.items(), 1):
                try:
                    # Robust base64 decode and decrypt for domain
                    domain = decode_and_decrypt("domain", info, hashed_pass)
                    decrypted_username = decode_and_decrypt("username", info, hashed_pass)
                    decrypted_email = decode_and_decrypt("email", info, hashed_pass)
                    is_favorite = "⭐" if info.get("favorite", False) else ""
                    print(
                        f"\n{CYAN}Profile {i} {is_favorite} {GOLD}| {LPURPLE}Domain: {domain}\n{DBLUE}Username:{RESET} {decrypted_username} {GOLD}, {DBLUE}Email:{RESET} {decrypted_email}"
                    )
                except KeyError:
                    print(
                        f"{RED} ** ALERT: Profile '{profile_id}' does not have a 'domain' key. Skipping. **{RESET}"
                    )
                except Exception as ex:
                    print(f"Error decrypting profile {profile_id}: {str(ex)}")

            # Ask user to select a profile to edit
            num_matching_profiles = len(matching_profiles)
            profile_range = (
                f"1-{num_matching_profiles}" if num_matching_profiles > 1 else "1"
            )
            while True:
                choice = timeoutInput(
                    f"{GOLD}\nSelect the profile to edit by number ({profile_range}) or type (.c) to cancel: {RESET}"
                )
                if choice == ".c" or choice == timeoutGlobalCode:
                    print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                    print("Returning to menu")
                    return False if choice != timeoutGlobalCode else True
                if choice.isdigit() and 1 <= int(choice) <= len(matching_profiles):
                    selected_profile_id = list(matching_profiles.keys())[int(choice) - 1]
                    selected_profile_info = matching_profiles[selected_profile_id]
                    break
                else:
                    print(
                        f"{RED} ** ALERT: Invalid choice. Please enter a valid number. **{RESET}"
                    )

            # Decrypt the selected profile details with enhanced security
            try:
 
                curr_domain = decode_and_decrypt("domain", selected_profile_info, hashed_pass)
                curr_username = decode_and_decrypt("username", selected_profile_info, hashed_pass)
                curr_email = decode_and_decrypt("email", selected_profile_info, hashed_pass)
                curr_password = decode_and_decrypt("password", selected_profile_info, hashed_pass)
                curr_favorite = selected_profile_info.get("favorite", False)
                is_favorite = "⭐" if curr_favorite else ""
            except Exception as ex:
                print(f"Error decrypting profile details: {str(ex)}")
                return False

            # Display selected profile
            clear_screen()
            displayHeader(f"{CYAN}🖍️  EDIT A PROFILE{RESET}")
            print(f"{GOLD}Selected Profile for Editing (#{choice}){RESET}")
            print(
                f"\n{CYAN}Profile {choice} {is_favorite} {GOLD}| {LPURPLE}Domain: {curr_domain}\n{DBLUE}Username:{RESET} {curr_username} {GOLD}, {DBLUE}Email:{RESET} {curr_email}"
            )

            # Get new domain
            edit_domain = timeoutInput(
                f"\n{GOLD}New Domain (press 'enter' to keep the current: {curr_domain} or type (.c) to cancel): {RESET}"
            )
            if edit_domain == ".c" or edit_domain == timeoutGlobalCode:
                return False if edit_domain != timeoutGlobalCode else True
            if not edit_domain.strip():
                edit_domain = curr_domain

            # Get new username
            edit_username = timeoutInput(
                f"{GOLD}New Username (press 'enter' to keep the current: {curr_username} or type (.c) to cancel): {RESET}"
            )
            if edit_username == ".c" or edit_username == timeoutGlobalCode:
                return False if edit_username != timeoutGlobalCode else True
            if not edit_username.strip():
                edit_username = curr_username

            # Get new email
            edit_email = timeoutInput(
                f"{GOLD}New Email (press 'enter' to keep the current: {curr_email} or type (.c) to cancel): {RESET}"
            )
            if edit_email == ".c" or edit_email == timeoutGlobalCode:
                return False if edit_email != timeoutGlobalCode else True
            if not edit_email.strip():
                edit_email = curr_email

            # Get new password
            edit_password = ""
            while True:
                user_input = timeoutInput(
                    f"{GOLD}Show your password while typing? (y/n) or press 'enter' to keep the current password (type (.c) to cancel): {RESET}"
                ).lower()

                if user_input == timeoutGlobalCode:
                    return True

                if not user_input:
                    edit_password = curr_password  # Keep the current password
                    break

                if user_input == ".c":
                    return False

                if user_input not in ["y", "n", ""]:
                    print(
                        f"{RED}** ALERT: Invalid input. Please enter 'y', 'n', or press 'enter'.**{RESET}"
                    )
                    continue

                # Get new password based on user's choice to show it or not
                try:
                    if user_input == "n":
                        edit_password = timeout_getpass(
                            f"{GOLD}Enter the new password (type (.c) to cancel, .g to generate a new password): {RESET}",
                            current_timeout,
                        )
                    else:  # user_input == 'y'
                        edit_password = timeoutInput(
                            f"{GOLD}Enter the new password (type (.c) to cancel, .g to generate a new password): {RESET}"
                        )

                    if edit_password == ".c":
                        return False  # Cancel editing if user chose to cancel

                    if edit_password == ".g":
                        edit_password = generate_password(RECOMMENDED_PASSWORD_LENGTH)
                        break

                    if not edit_password:
                        print(
                            f"{RED}** ALERT: Password input interrupted. Please try again.**{RESET}"
                        )
                        continue
                    else:
                        break

                except TimeoutError:
                    print(
                        f"{RED}** ALERT: Password input timed out. Please try again.**{RESET}"
                    )
                    continue

            # Handle favorite status
            while True:
                edit_favorite = timeoutInput(
                    f"{GOLD}Mark this profile as a favorite? (y/n) (press 'enter' to keep the current status or type (.c) to cancel): {RESET}"
                ).lower()
                if edit_favorite == ".c" or edit_favorite == timeoutGlobalCode:
                    return False if edit_favorite != timeoutGlobalCode else True
                if not edit_favorite.strip():
                    edit_favorite = curr_favorite
                    break
                if edit_favorite in ["y", "n"]:
                    edit_favorite = edit_favorite == "y"
                    break
                else:
                    print(
                        f"{RED} ** ALERT: Invalid input. Please enter 'y', 'n', or press 'enter'. **{RESET}"
                    )

            # Encrypting profile data with enhanced security
            try:
                encrypted_domain = base64.b64encode(vault.encrypt_data(str(edit_domain).encode(), hashed_pass)).decode("utf-8")
                encrypted_email = base64.b64encode(vault.encrypt_data(str(edit_email).encode(), hashed_pass)).decode("utf-8")
                encrypted_username = base64.b64encode(vault.encrypt_data(str(edit_username).encode(), hashed_pass)).decode("utf-8")
                encrypted_password = base64.b64encode(vault.encrypt_data(str(edit_password).encode(), hashed_pass)).decode("utf-8")
                
                db[selected_profile_id] = {
                "domain": encrypted_domain,
                "email": encrypted_email,
                "username": encrypted_username,
                "password": encrypted_password,
                "favorite": edit_favorite,
                }

                # Save encrypted database with enhanced security
                encrypted_db = vault.encrypt_data(json.dumps(db).encode(), hashed_pass)
                write_bytes_atomic("Bunker.mmf", encrypted_db)
                
                clear_screen()
                displayHeader(f"{CYAN}🖍️  EDIT A PROFILE{RESET}")
                print(f"{GREEN} ** SUCCESS: Profile '{curr_domain}' successfully updated! **{RESET}")
                print(f"\n{GOLD}Selected profile {CYAN}(#{choice}){GOLD} updated successfully!{RESET}")

            except Exception as e:
                print(f"{RED} ** ALERT: Failed to update database. Error: {safe_error(e)} **{RESET}")

            userContinue = timeoutInput(
                f"{GOLD}\nPress 'enter' to return to menu or type 'r' to retry...{RESET}"
            )
            if userContinue == timeoutGlobalCode:
                return True
            if userContinue.lower() == "r":
                continue
            else:
                return False
                
    except Exception as e:
        print(f"{RED}** ALERT: Failed to edit profile: {safe_error(e)} **{RESET}")
        return False
        
    finally:
        # Clean up sensitive data
        if 'edit_password' in locals(): del edit_password
        if 'curr_password' in locals(): del curr_password
        if 'hashed_pass' in locals(): del hashed_pass
        vault.secure_wipe()
        
def deleteProfileData(hashed_pass, db):
    """Delete profile data with enhanced security"""
    try:
        displayHeader(f"{CYAN}🗑️  DELETE A PROFILE{RESET}")

        while True:

            del_domain = timeoutInput(
                f"{GOLD}Leave empty to show all, type (.c) to cancel. \nEnter a word or exact domain of the profile you would like to search for: {RESET}"
            )
            if del_domain == ".c" or del_domain == timeoutGlobalCode:
                print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                print("Returning to menu")
                return False if del_domain != timeoutGlobalCode else True

            # Find profiles matching the domain or show all if input is empty
            if del_domain.strip() == "":
                matching_profiles = {
                    profile_id: info
                    for profile_id, info in db.items()
                    if "domain" in info and "password" in info  # Check for minimal requirements
                }
                clear_screen()
                del_domain = "ALL PROFILES"
                displayHeader(f"{CYAN}🗑️  DELETE A PROFILE{RESET}")
                print(f"{GOLD}Showing all profiles as no domain was provided.{RESET}")
                print(f"{GOLD}Searching for... 'All Profiles':{RESET}\n")
            else:
                matching_profiles = {}
                for profile_id, info in db.items():
                    if "domain" in info and "password" in info:  # Check for minimal requirements
                        try:
                            decrypted_domain = decode_and_decrypt("domain", info, hashed_pass)
                            if del_domain.lower() in decrypted_domain.lower():
                                matching_profiles[profile_id] = info
                        except Exception:
                            continue
                clear_screen()
                displayHeader(f"{CYAN}🗑️  DELETE A PROFILE{RESET}")
                print(f"{GOLD}Searching domain names for... '{del_domain}':{RESET}\n")

            num_matching_profiles = len(matching_profiles)
            if num_matching_profiles == 0:
                print(
                    f"{GOLD}Found {num_matching_profiles} matching profile{'s' if num_matching_profiles > 1 else ''}:{RESET}\n"
                )
                print(
                    f"{RED} ** ALERT: No profiles available to display. ADD OR EDIT A PROFILE! **{RESET}"
                )
                userContinue = timeoutInput(
                    f"{GOLD}\nPress 'enter' to return to menu...{RESET}"
                )
                return False if userContinue != timeoutGlobalCode else True

            print(
                f"{GOLD}Found {num_matching_profiles} matching profile{'s' if num_matching_profiles > 1 else ''}:{RESET}\n"
            )
            profile_indices = {}
            for i, (profile_id, info) in enumerate(matching_profiles.items(), 1):
                try:
                    domain_bytes = base64.b64decode(info["domain"]) if isinstance(info["domain"], str) else info["domain"]
                    domain = vault.decrypt_data(domain_bytes, hashed_pass).decode("utf-8")
                    username = info.get("username", "N/A")
                    if username != "N/A":
                        username_bytes = base64.b64decode(username) if isinstance(username, str) else username
                        username = vault.decrypt_data(username_bytes, hashed_pass).decode("utf-8")
                    email = info.get("email", "N/A")
                    if email != "N/A":
                        email_bytes = base64.b64decode(email) if isinstance(email, str) else email
                        email = vault.decrypt_data(email_bytes, hashed_pass).decode("utf-8")
                    is_favorite = "⭐" if info.get("favorite", False) else ""
                    profile_indices[i] = profile_id
                    print(
                        f"{CYAN}Profile {i} {is_favorite}{GOLD} | {LPURPLE}Domain: {domain}{RESET} \n{DBLUE}Username: {RESET}{username} {GOLD}, {DBLUE}Email:{RESET} {email}\n"
                    )
                except Exception as e:
                    print(
                        f"{RED} ** ALERT: Error reading profile '{profile_id}': {safe_error(e)} **{RESET}"
                    )

            # Ask if the user wants to delete all, select profiles, or cancel
            while True:
                delete_choice = timeoutInput(
                    f"\n{GOLD}Delete all {num_matching_profiles} profiles? (type 'a' to delete all, 's' to choose profiles, or (.c) to cancel): {RESET}"
                ).lower()
                if delete_choice in [".c", timeoutGlobalCode, "a", "s"]:
                    break
                else:
                    print(
                        f"{RED} ** ALERT: Invalid choice. Please enter 'a', 's', or '.c' to cancel. **{RESET}"
                    )
            if delete_choice == ".c" or delete_choice == timeoutGlobalCode:
                print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                print("Returning to menu")
                return False if delete_choice != timeoutGlobalCode else True

            keys_to_delete = []
            selected_indices = []
            if delete_choice == "a":
                keys_to_delete = list(matching_profiles.keys())
                selected_indices = list(profile_indices.keys())
            elif delete_choice == "s":
                while True:
                    profile_nums = timeoutInput(
                        f"{GOLD}\nEnter the numbers of the profiles to delete, separated by commas (type (.c) to cancel): {RESET}"
                    )
                    if profile_nums == ".c" or profile_nums == timeoutGlobalCode:
                        print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                        print("Returning to menu")
                        return False if profile_nums != timeoutGlobalCode else True

                    selected_indices = profile_nums.replace(" ", "").split(",")
                    valid_input = all(
                        index.strip().isdigit()
                        and 1 <= int(index.strip()) <= num_matching_profiles
                        for index in selected_indices
                    )

                    if valid_input:
                        keys_to_delete = [
                            profile_indices[int(index.strip())]
                            for index in selected_indices
                        ]
                        selected_indices = sorted(
                            [int(index.strip()) for index in selected_indices]
                        )  # Sort selected indices
                        break
                    else:
                        print(
                            f"{RED} ** ALERT: Invalid input. Please enter valid numbers corresponding to the profiles. **{RESET}"
                        )

            # Collect decrypted domain names and indices of deleted profiles
            decrypted_deleted_domains = []
            for index, profile_id in zip(selected_indices, keys_to_delete):
                try:
                    info = db[profile_id]
                    domain_bytes = base64.b64decode(info["domain"]) if isinstance(info["domain"], str) else info["domain"]
                    domain = vault.decrypt_data(domain_bytes, hashed_pass).decode("utf-8")
                    is_favorite = "⭐" if info.get("favorite", False) else ""
                    decrypted_deleted_domains.append(
                        f"\n{CYAN}Profile {index} {is_favorite} {GOLD}| {LPURPLE}Domain: {domain}{RESET}"
                    )
                except Exception as e:
                    print(
                        f"{RED} ** ALERT: Error decrypting domain '{profile_id}': {safe_error(e)} **{RESET}"
                    )

            # Delete the profiles
            for profile_id in keys_to_delete:
                del db[profile_id]

            # Print the result
            if decrypted_deleted_domains:
                clear_screen()
                displayHeader(f"{CYAN}🗑️  DELETE A PROFILE{RESET}")
                print(
                    f"{GREEN}** SUCCESS: All selected have been deleted successfully! **{RESET}"
                )
                print(
                    f"{GOLD}\nSelected profile{'s' if len(decrypted_deleted_domains) > 1 else ''} deleted:{RESET}"
                )
                print(f"{f'{GOLD},\n{LPURPLE}'.join(decrypted_deleted_domains)}")
                
            # Save changes to the database with enhanced security
            try:
                encrypted_db = vault.encrypt_data(json.dumps(db).encode(), hashed_pass)
                write_bytes_atomic("Bunker.mmf", encrypted_db)
            except Exception as e:
                print(f"{RED} ** ALERT: Failed to update database. Error: {safe_error(e)} **{RESET}")

            userContinue = timeoutInput(
                f"{GOLD}\nPress 'enter' to return to menu or type 'r' to retry...{RESET}"
            )
            if userContinue == "r":
                continue
            else:
                return False if userContinue != timeoutGlobalCode else True
                
    except Exception as e:
        print(f"{RED}** ALERT: Failed to delete profile: {safe_error(e)} **{RESET}")
        return False
        
    finally:
        # Clean up sensitive data
        if 'hashed_pass' in locals(): del hashed_pass
        vault.secure_wipe()

def findProfileData(hashed_pass, db):
    """Find profile data with enhanced security"""
    try:
        displayHeader(f"{CYAN}🔍 FIND A PROFILE{RESET}")
        print(f"{GOLD}Type and submit (.c) to cancel.{RESET}")

        while True:
            clear_screen()
            displayHeader(f"{CYAN}🔍 FIND A PROFILE{RESET}")
            read_domain = timeoutInput(
                f"{GOLD}Type (.c) to cancel. \nEnter a word or exact domain of the profile you would like to search for: {RESET}"
            )

            if read_domain == ".c" or read_domain == timeoutGlobalCode:
                print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                print(f"{GOLD}Returning to Menu{RESET}")
                return False if read_domain != timeoutGlobalCode else True

            if not read_domain.strip():
                print(
                    f"\n{RED} ** ALERT: Please enter a valid domain name or (.c) to cancel. **{RESET}"
                )
                userContinue = timeoutInput(
                    f"{GOLD}\nPress 'enter' to return to menu or type 'r' to retry...{RESET}"
                )
                if userContinue == "r":
                    continue
                else:
                    return False if userContinue != timeoutGlobalCode else True

            try:
                # Find matching profiles with enhanced security
                matches = []
                for profile_id, info in db.items():
                    if "domain" in info:
                        try:
                            domain_bytes = base64.b64decode(info["domain"]) if isinstance(info["domain"], str) else info["domain"]
                            decrypted_domain = vault.decrypt_data(domain_bytes, hashed_pass).decode("utf-8")
                            if read_domain.lower() in decrypted_domain.lower():
                                matches.append(profile_id)
                        except Exception:
                            continue

                num_matching_profiles = len(matches)

                if not matches:
                    print(
                        f"{RED}\n ** ALERT: Could not find a match. Try viewing all saved profiles. **{RESET}"
                    )
                    userContinue = timeoutInput(
                        f"{GOLD}\nPress 'enter' to return to menu or type 'r' to retry...{RESET}"
                    )
                    if userContinue == "r":
                        continue
                    else:
                        return False if userContinue != timeoutGlobalCode else True

                clear_screen()
                displayHeader(f"{CYAN}🔍 FIND A PROFILE{RESET}")
                print(f"{GOLD}Searching for... '{read_domain}':{RESET}")
                print(
                    f"{GOLD}\nClosest match{'es' if num_matching_profiles > 1 else ''}:{RESET}"
                )

                for i, profile_id in enumerate(matches, 1):
                    domain_info = db[profile_id]
                    try:
                        # Decrypt profile data with enhanced security
                        domain = decode_and_decrypt("domain", domain_info, hashed_pass)
                        username = decode_and_decrypt("username", domain_info, hashed_pass)
                        email = decode_and_decrypt("email", domain_info, hashed_pass)
                        is_favorite = "⭐" if domain_info.get("favorite", False) else ""
                        print(
                            f"\n{CYAN}PROFILE {i} {is_favorite} {GOLD}| {LPURPLE}Domain: {domain}{RESET}"
                        )
                        print(
                            f"{DBLUE}Username: {RESET}{username}, {DBLUE}Email: {RESET}{email}"
                        )
                    except Exception as e:
                        print(f"{RED} ** ALERT: Error decrypting profile {i}: {safe_error(e)} **{RESET}")
                        continue

                profile_range = (
                    f"1-{num_matching_profiles}" if num_matching_profiles > 1 else "1"
                )
                while True:
                    user_choice = timeoutInput(
                        f"{GOLD}\nSelect the profile to view its password ({profile_range}) or type .c to cancel: {RESET}"
                    )
                    if user_choice == ".c" or user_choice == timeoutGlobalCode:
                        print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                        print(f"{GOLD}Returning to Menu{RESET}")
                        return False if user_choice != timeoutGlobalCode else True

                    if not user_choice.isdigit():
                        print(
                            f"\n{RED} ** ALERT: Please enter a valid profile number or (.c) to cancel. **{RESET}"
                        )
                        continue

                    profile_num = int(user_choice)
                    if profile_num <= 0 or profile_num > len(matches):
                        print(
                            f"\n{RED} ** ALERT: Invalid profile number. Please enter a valid number. **{RESET}"
                        )
                        continue

                    try:
                        profile_id = matches[profile_num - 1]
                        domain_info = db[profile_id]
                        
                        # Decrypt profile data with enhanced security
                        domain = decode_and_decrypt("domain", domain_info, hashed_pass)
                        username = decode_and_decrypt("username", domain_info, hashed_pass)
                        email = decode_and_decrypt("email", domain_info, hashed_pass)
                        password = decode_and_decrypt("password", domain_info, hashed_pass)
                        is_favorite = "⭐" if domain_info.get("favorite", False) else ""

                        while True:
                            clear_screen()
                            displayHeader(f"{CYAN}🔍 FIND A PROFILE{RESET}")
                            print(f"{GOLD}You selected profile:\n{RESET}")
                            print(
                                f"{CYAN}Profile {profile_num} {is_favorite} {GOLD}| {LPURPLE}Domain: {domain}\n{DBLUE}Username:{RESET} {username} {GOLD}, {DBLUE}Email: {RESET}{email}\n"
                            )

                            option = timeoutInput(
                                f"{GOLD}Type 'v' to view, 'c' to copy to clipboard, or '.c' to cancel\nDo you want to display the password or just copy it? : {RESET}"
                            ).lower()
                            if option == "v":
                                print(
                                    f"\n{GOLD}Password requested for {LPURPLE}{domain}!{RESET}"
                                )
                                reveal_secret(f"{GREEN}Password request granted! \n\n{DBLUE}Password:{RESET} ", f"{password}{RESET}\n")
                                break
                            elif option == "c":
                                _copied = copy_secret(password)
                                print(
                                    (f"\n{GREEN}{copy_notice('Password')}{RESET}\n" if _copied else f"\n{RED}** ALERT: Could not access the clipboard. **{RESET}\n")
                                )
                                break
                            elif option == ".c" or option == timeoutGlobalCode:
                                return False if option != timeoutGlobalCode else True
                            else:
                                print(
                                    f"{RED} ** ALERT: Invalid option. Please enter 'v' to view, 'c' to copy, or '.c' to cancel. **{RESET}"
                                )

                        userContinue = timeoutInput(
                            f"{GOLD}\nPress 'enter' to return to menu or type 'r' to retry...{RESET}"
                        )
                        if userContinue == "r":
                            return findProfileData(hashed_pass, db)
                        else:
                            return False if userContinue != timeoutGlobalCode else True

                    except Exception as ex:
                        print(
                            f"\n{RED} ** ALERT: Unable to find password for profile {profile_num}: {str(ex)} **{RESET}"
                        )
                        continue

            except Exception as e:
                print(f"{RED} ** ALERT: Error finding profile: {safe_error(e)} **{RESET}")
                userContinue = timeoutInput(
                    f"{GOLD}\nPress 'enter' to return to menu...{RESET}"
                )
                return False if userContinue != timeoutGlobalCode else True
                
    except Exception as e:
        print(f"{RED}** ALERT: Failed to find profile: {safe_error(e)} **{RESET}")
        return False
        
    finally:
        # Clean up sensitive data
        if 'password' in locals(): del password
        if 'hashed_pass' in locals(): del hashed_pass
        vault.secure_wipe()

def tagProfiles(hashed_pass, db):
    """Sort and find profiles by domain tags with enhanced security"""
    try:
        displayHeader(f"{CYAN}🏷️  SORT AND FIND DOMAINS{RESET}")

        # Ensure db is properly loaded as a dictionary
        if isinstance(db, bytes):
            try:
                decrypted_data = vault.decrypt_data(db, hashed_pass)
                db = json.loads(decrypted_data.decode("utf-8"))
            except Exception as e:
                print(f"{RED} ** ALERT: Error loading database: {safe_error(e)} **{RESET}")
                return False

        # Collect all domains from the database (only from valid profiles)
        all_domains = {}
        for profile_id, info in db.items():
            try:
                # Check if this is a valid profile with required fields
                if "domain" in info and "password" in info:
                    domain = decode_and_decrypt("domain", info, hashed_pass)
                    if domain in all_domains:
                        all_domains[domain].append(profile_id)
                    else:
                        all_domains[domain] = [profile_id]
            except Exception:
                continue

        if not all_domains:
            print(f"{GOLD}Searching for... 'All Domains':{RESET}\n")
            print(
                f"{GOLD}Found {len(all_domains)} matching domain{'s' if len(all_domains) != 1 else ''}:\n{RESET}"
            )
            print(
                f"{RED} ** ALERT: No profiles available to display. ADD OR EDIT A PROFILE! **{RESET}"
            )
            userContinue = timeoutInput(
                f"{GOLD}\nPress 'enter' to return to menu...{RESET}"
            )
            return False if userContinue != timeoutGlobalCode else True

        # Display all available domains
        print(f"{GOLD}Searching for... 'All Domain Tags':{RESET}\n")
        print(
            f"{GOLD}Found {len(all_domains)} domain tag{'s' if len(all_domains) != 1 else ''}:\n{RESET}"
        )
        domains_list = list(all_domains.keys())
        for i, domain in enumerate(domains_list, 1):
            # Count valid profiles for this domain
            valid_profiles = len(all_domains[domain])
            print(
                f"{CYAN}Tag {i} {GOLD}| {LPURPLE}Domain: {LPURPLE}{domain} {GOLD}({valid_profiles} profile{'s' if valid_profiles != 1 else ''}){RESET}"
            )

        while True:
            selected_domain_index = timeoutInput(
                f"{GOLD}\nEnter a number to filter profiles by domain (type (.c) to cancel): {RESET}"
            )
            if selected_domain_index == ".c" or selected_domain_index == timeoutGlobalCode:
                print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                return False if selected_domain_index != timeoutGlobalCode else True

            try:
                selected_domain_index = int(selected_domain_index) - 1
                if 0 <= selected_domain_index < len(domains_list):
                    break
                else:
                    print(
                        f"{RED} ** ALERT: Invalid selection. Please select a valid domain number.{RESET}"
                    )
            except ValueError:
                print(f"{RED} ** ALERT: Invalid input. Please enter a number.{RESET}")

        selected_domain = domains_list[selected_domain_index]
        clear_screen()
        displayHeader(f"{CYAN}🏷️  SORT AND FIND PROFILES{RESET}")

        # Find profiles that match the selected domain with enhanced security
        matching_profiles = []
        for profile_id, info in db.items():
            if "domain" in info:
                try:
                    domain = decode_and_decrypt("domain", info, hashed_pass)
                    if domain == selected_domain:
                        matching_profiles.append((profile_id, info))
                except Exception:
                    continue

        num_matching_profiles = len(matching_profiles)

        if matching_profiles:
            print(f"{GOLD}Searching for domains under... '{selected_domain}':{RESET}")
            print(
                f"{GOLD}\nClosest match{'es' if num_matching_profiles > 1 else ''}:{RESET}"
            )
            print(
                f"{GOLD}Found {num_matching_profiles} matching profile{'s' if num_matching_profiles != 1 else ''}:\n{RESET}"
            )
            for i, (profile_id, info) in enumerate(matching_profiles, 1):
                try:
                    # Decrypt profile data with enhanced security
                    domain = decode_and_decrypt("domain", info, hashed_pass)
                    username = decode_and_decrypt("username", info, hashed_pass)
                    email = decode_and_decrypt("email", info, hashed_pass)
                    is_favorite = "⭐" if info.get("favorite", False) else ""
                    print(
                    f"\n{CYAN}PROFILE {i} {is_favorite} {GOLD}| {LPURPLE}Domain: {domain}\n{DBLUE}Username: {RESET}{username}, {DBLUE}Email: {RESET}{email}{RESET}"
                    )
                except Exception:
                    continue

            profile_range = (
                f"1-{num_matching_profiles}" if num_matching_profiles > 1 else "1"
            )
            while True:
                user_choice = timeoutInput(
                    f"{GOLD}\nSelect the profile to view its password ({profile_range}) or type .c to cancel: {RESET}"
                )
                if user_choice == ".c" or user_choice == timeoutGlobalCode:
                    print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                    return False if user_choice != timeoutGlobalCode else True

                if not user_choice.isdigit():
                    print(
                        f"{RED} ** ALERT: Invalid input. Please enter a valid profile number or (.c) to cancel. **{RESET}"
                    )
                    continue

                profile_num = int(user_choice)
                if profile_num <= 0 or profile_num > len(matching_profiles):
                    print(
                        f"{RED} ** ALERT: Invalid profile number. Please enter a valid number. **{RESET}"
                    )
                    continue

                profile_id, info = matching_profiles[profile_num - 1]
                try:
                    # Decrypt profile data with enhanced security
                    domain = decode_and_decrypt("domain", info, hashed_pass)
                    username = decode_and_decrypt("username", info, hashed_pass)
                    email = decode_and_decrypt("email", info, hashed_pass)
                    password = decode_and_decrypt("password", info, hashed_pass)
                    is_favorite = "⭐" if info.get("favorite", False) else ""

                    while True:
                        clear_screen()
                        displayHeader(f"{CYAN}🏷️  SORT AND FIND DOMAINS{RESET}")
                        print(f"{GOLD}You selected profile:\n{RESET}")
                        print(
                            f"{CYAN}Profile {profile_num} {is_favorite} {GOLD}| {LPURPLE}Domain: {domain}\n{DBLUE}Username:{RESET} {username} {GOLD}, {DBLUE}Email: {RESET}{email}\n"
                        )

                        option = timeoutInput(
                            f"{GOLD}Type 'v' to view, 'c' to copy to clipboard, or '.c' to cancel\nDo you want to display the password or just copy it? : {RESET}"
                        ).lower()
                        if option == "v":
                            print(
                                f"\n{GOLD}Password requested for {LPURPLE}{domain}!{RESET}"
                            )
                            reveal_secret(f"{GREEN}Password request granted! \n\n{DBLUE}Password:{RESET} ", f"{password}{RESET}\n")
                            break
                        elif option == "c":
                            _copied = copy_secret(password)
                            print(
                                (f"\n{GREEN}{copy_notice('Password')}{RESET}\n" if _copied else f"\n{RED}** ALERT: Could not access the clipboard. **{RESET}\n")
                            )
                            break
                        elif option == ".c" or option == timeoutGlobalCode:
                            return False if option != timeoutGlobalCode else True
                        else:
                            print(
                                f"{RED} ** ALERT: Invalid option. Please enter 'v' to view, 'c' to copy, or '.c' to cancel. **{RESET}"
                            )

                    userContinue = timeoutInput(
                        f"{GOLD}\nPress 'enter' to return to menu or type 'r' to retry...{RESET}"
                    )
                    if userContinue == "r":
                        break
                    else:
                        return False if userContinue != timeoutGlobalCode else True

                except Exception as ex:
                    print(
                        f"\n{RED} ** ALERT: Unable to find password for profile {profile_num}: {str(ex)} **{RESET}"
                    )
                    continue

        else:
            print(
                f"\n{RED} ** ALERT: No profiles found for domain '{selected_domain}'.{RESET}"
            )
            userContinue = timeoutInput(
                f"{GOLD}\nPress 'enter' to return to menu...{RESET}"
            )
            return False if userContinue != timeoutGlobalCode else True
            
    except Exception as e:
        print(f"{RED}** ALERT: Failed to tag profiles: {safe_error(e)} **{RESET}")
        return False
        
    finally:
        # Clean up sensitive data
        if 'password' in locals(): del password
        if 'hashed_pass' in locals(): del hashed_pass
        vault.secure_wipe()

def readAllProfiles(hashed_pass, db):
    """Read all profiles with enhanced security"""
    try:
        clear_screen()
        displayHeader(f"{CYAN}📖  VIEW ALL PROFILES{RESET}")

        print(f"{GOLD}Searching for... 'All PROFILES':{RESET}\n")

        # Filter profiles that have the minimal requirements (domain and password)
        matching_profiles = {
            profile_id: info 
            for profile_id, info in db.items() 
            if "domain" in info and "password" in info
        }
        num_matching_profiles = len(matching_profiles)

        if num_matching_profiles == 0:
            print(f"{GOLD}Found {num_matching_profiles} matching profile{'s' if num_matching_profiles > 1 else ''}:{RESET}\n")
            print(f"{RED} ** ALERT: No profiles available to display. ADD OR EDIT A PROFILE! **{RESET}")
            userContinue = timeoutInput(f"{GOLD}\nPress 'enter' to return to menu...{RESET}")
            return False if userContinue != timeoutGlobalCode else True

        print(f"{GOLD}Found {num_matching_profiles} matching profile{'s' if num_matching_profiles > 1 else ''}:{RESET}\n")

        # Store decrypted profiles for later use
        decrypted_profiles = []
        index = 1
        for profile_id, info in matching_profiles.items():
            try:
                # Decrypt domain (required field) with enhanced security
                domain_bytes = base64.b64decode(info["domain"]) if isinstance(info["domain"], str) else info["domain"]
                domain = vault.decrypt_data(domain_bytes, hashed_pass).decode("utf-8")
                
                # Handle optional fields with enhanced security
                username = info.get("username", "N/A")
                if username != "N/A":
                    username_bytes = base64.b64decode(username) if isinstance(username, str) else username
                    username = vault.decrypt_data(username_bytes, hashed_pass).decode("utf-8")

                email = info.get("email", "N/A")
                if email != "N/A":
                    email_bytes = base64.b64decode(email) if isinstance(email, str) else email
                    email = vault.decrypt_data(email_bytes, hashed_pass).decode("utf-8")

                is_favorite = "⭐" if info.get("favorite", False) else ""
                decrypted_profiles.append(
                    (index, profile_id, domain, username, email, is_favorite)
                )
                index += 1

            except Exception as e:
                # Silently skip profiles that cannot be decrypted
                continue

        # Display profiles
        for idx, profile in enumerate(decrypted_profiles, 1):
            domain, username, email, is_favorite = profile[2], profile[3], profile[4], profile[5]
            print(
                f"{CYAN}Profile {idx} {is_favorite}{GOLD} | {LPURPLE}Domain: {domain}{RESET} \n{DBLUE}Username: {RESET}{username} {GOLD}, {DBLUE}Email:{RESET} {email}\n"
            )

        # Handle password viewing
        while True:
            profile_range = f"1-{len(decrypted_profiles)}" if len(decrypted_profiles) > 1 else "1"
            view_password = timeoutInput(
                f"{GOLD}\nSelect the profile to view its password ({profile_range}) or type .c to cancel: {RESET}"
            )
            if view_password == ".c" or view_password == timeoutGlobalCode:
                return False if view_password != timeoutGlobalCode else True
            elif view_password.isdigit():
                selected_index = int(view_password)
                if 1 <= selected_index <= len(decrypted_profiles):
                    selected_profile = decrypted_profiles[selected_index - 1]
                    profile_id = selected_profile[1]
                    domain = selected_profile[2]
                    username = selected_profile[3]
                    email = selected_profile[4]
                    is_favorite = selected_profile[5]
                    try:
                        # Decrypt password with enhanced security
                        password_bytes = base64.b64decode(matching_profiles[profile_id]["password"]) if isinstance(matching_profiles[profile_id]["password"], str) else matching_profiles[profile_id]["password"]
                        password = vault.decrypt_data(password_bytes, hashed_pass).decode("utf-8")
                        
                        while True:
                            clear_screen()
                            displayHeader(f"{CYAN}📖  VIEW ALL PROFILES{RESET}")
                            print(f"{GOLD}You selected profile:\n{RESET}")
                            print(
                                f"{CYAN}Profile {selected_index} {is_favorite} {GOLD}|{LPURPLE} Domain: {domain}\n{DBLUE}Username:{RESET} {username} {GOLD}, {DBLUE}Email: {RESET}{email}\n"
                            )

                            copy_choice = timeoutInput(
                                f"{GOLD}Type 'v' to view, 'c' to copy to clipboard, or '.c' to cancel\nDo you want to display the password or just copy it? : {RESET}"
                            ).lower()
                            if copy_choice == "v":
                                print(f"\n{GOLD}Password requested for {LPURPLE}{domain}!{RESET}")
                                reveal_secret(f"{GREEN}Password request granted! \n\n{DBLUE}Password:{RESET} ", f"{password}{RESET}\n")
                                break
                            elif copy_choice == "c":
                                _copied = copy_secret(password)
                                print((f"{GREEN}{copy_notice('Password')}{RESET}\n" if _copied else f"{RED}** ALERT: Could not access the clipboard. **{RESET}\n"))
                                break
                            elif copy_choice == ".c" or copy_choice == timeoutGlobalCode:
                                return False if copy_choice != timeoutGlobalCode else True
                            else:
                                print(f"{RED} ** ALERT: Invalid option. Please enter 'v' to view, 'c' to copy, or '.c' to cancel. **{RESET}")

                        while True:
                            user_choice = timeoutInput(
                                f"{GOLD}Press 'enter' to return to the main menu or type 'r' to retry... {RESET}"
                            )
                            if user_choice == timeoutGlobalCode:
                                return True
                            if user_choice == "r":
                                return readAllProfiles(hashed_pass, db)
                            elif user_choice == "":
                                return False  # Return to the main menu
                            else:
                                print(f"{RED} ** ALERT: Invalid input. Please press 'enter' to return to the main menu or type 'r' to retry. **{RESET}")

                    except Exception as e:
                        print(f"{RED} ** ALERT: Error reading password for profile '{selected_index}': {safe_error(e)} **{RESET}")
                        continue
                else:
                    print(f"{RED} ** ALERT: Invalid profile number. **{RESET}")
            else:
                print(f"{RED} ** ALERT: Invalid input. Please enter a valid profile number or '.c' to cancel. **{RESET}")

        userContinue = timeoutInput(f"{GOLD}\nPress 'enter' to return to menu...{RESET}")
        return False if userContinue != timeoutGlobalCode else True
        
    except Exception as e:
        print(f"{RED}** ALERT: Failed to read profiles: {safe_error(e)} **{RESET}")
        return False
        
    finally:
        # Clean up sensitive data
        if 'password' in locals(): del password
        if 'hashed_pass' in locals(): del hashed_pass
        if 'decrypted_profiles' in locals(): del decrypted_profiles
        vault.secure_wipe()

# Note Display
def main_note_manager(hashed_pass, contents):
    """Main note manager interface with enhanced security"""
    try:
        # Initialize vault
        clear_screen()
        
        # Ensure contents is properly initialized
        if contents is None:
            raise ValueError("Database contents are missing")
            
        # Decrypt database with enhanced security
        try:
            # Handle string input for contents (from file read)
            if isinstance(contents, str):
                contents = contents.encode()
                
            decrypted_data = vault.decrypt_data(contents, hashed_pass)
            db = json.loads(decrypted_data.decode("utf-8"))
        except Exception as e:
            raise ValueError(f"Failed to decrypt database: {safe_error(e)}")
        
        timedOut = False
        while not timedOut:
            try:
                check_terminal_size()
                clear_screen()
                print(title_art)
                ui_config = load_ui_config()
                disable_ipv4 = ui_config["disable_ipv4"]
                #temp
                #disable_ipv4 = vault.manage_config(hashed_pass)["settings"].get("disable_ipv4", True)
                display_watermark(disable_ipv4)
                timeout_display = displayTimeout()
                print(
                    f"{L_CYAN}🗂️  NOTES MANAGER {FBLUE}- {LPURPLE}Version: BETA {RESET}{FBLUE}- "
                    + timeout_display
                )
                print(divider)
                user_cmd = print(
                    f"{GOLD}\n(a){L_CYAN} 📝 Add note {GOLD}|{RESET} {GOLD}(s){L_CYAN} ⭐ Favorite notes {GOLD}|{RESET} {GOLD}(d){L_CYAN} 🗑️  Delete a note {GOLD}|{RESET} {GOLD}(f){L_CYAN} 🔍 Find a note {GOLD}|{RESET} {GOLD}(c){L_CYAN} ⬆️  Export/Import \n\n{GOLD}(r){L_CYAN} 📖 Read all notes {GOLD}|{RESET} {GOLD}(e){L_CYAN} 🖍️  Edit note data {GOLD}|{RESET} 🏷️  {GOLD}(t){L_CYAN} Tags folder {GOLD}|{RESET} {GOLD}(x){PURPLE} 🔙 Back\n{RESET}"
                )
                user_cmd = timeoutInput(f"{GOLD}What would you like to do? {RESET}")
                print("\n")

                # Handle timeout
                if user_cmd == timeoutGlobalCode:
                    timeoutCleanup()
                    timedOut = True
                    continue
                
                # Ensure user input is lowercase
                user_cmd = user_cmd.lower()

                # Process user commands
                if user_cmd == "a":
                    # Get the latest database contents before calling addNote
                    try:
                        with open("Bunker.mmf", "r") as f:
                            latest_contents = f.read()
                        if latest_contents:
                            latest_contents_bytes = latest_contents.encode()
                            decrypted_latest = vault.decrypt_data(latest_contents_bytes, hashed_pass)
                            db = json.loads(decrypted_latest.decode("utf-8"))
                    except Exception:
                        # If we can't get the latest, use what we have
                        pass
                        
                    timedOut = addNote(hashed_pass, db)
                    
                    # Save changes after operation
                    if not timedOut:
                        try:
                            encrypted_db = vault.encrypt_data(json.dumps(db).encode(), hashed_pass)
                            write_bytes_atomic("Bunker.mmf", encrypted_db)
                            # Update contents for future operations
                            contents = encrypted_db
                        except Exception as e:
                            print(f"{RED}** ALERT: Failed to save changes: {safe_error(e)} **{RESET}")
                            input(f"{GOLD}Press ENTER to continue...{RESET}")

                elif user_cmd == "s":
                    timedOut = displayFavoriteNotes(hashed_pass, db)

                elif user_cmd == "d":
                    timedOut = deleteNoteData(hashed_pass, db)
                    # Save changes after operation
                    if not timedOut:
                        try:
                            encrypted_db = vault.encrypt_data(json.dumps(db).encode(), hashed_pass)
                            write_bytes_atomic("Bunker.mmf", encrypted_db)
                            # Update contents for future operations
                            contents = encrypted_db
                        except Exception as e:
                            print(f"{RED}** ALERT: Failed to save changes: {safe_error(e)} **{RESET}")
                            input(f"{GOLD}Press ENTER to continue...{RESET}")

                elif user_cmd == "f":
                    timedOut = findNoteData(hashed_pass, db)

                elif user_cmd == "c":
                    timedOut = manageNotes(hashed_pass, db)

                elif user_cmd == "r":
                    timedOut = displayAllNotes(hashed_pass, db)

                elif user_cmd == "e":
                    timedOut = editNoteData(hashed_pass, db)
                    # Save changes after operation
                    if not timedOut:
                        try:
                            encrypted_db = vault.encrypt_data(json.dumps(db).encode(), hashed_pass)
                            write_bytes_atomic("Bunker.mmf", encrypted_db)
                            # Update contents for future operations
                            contents = encrypted_db
                        except Exception as e:
                            print(f"{RED}** ALERT: Failed to save changes: {safe_error(e)} **{RESET}")
                            input(f"{GOLD}Press ENTER to continue...{RESET}")

                elif user_cmd == "t":
                    timedOut = tagNotes(hashed_pass, db)

                elif user_cmd == "x":
                    # Return to parent menu without setting timedOut
                    return False

            except Exception as e:
                print(f"{RED}** ALERT: Operation failed: {safe_error(e)} **{RESET}")
                input(f"{GOLD}Press ENTER to continue...{RESET}")

    except Exception as e:
        print(f"{RED}** ALERT: Failed to manage notes: {safe_error(e)} **{RESET}")
        return False
        
    finally:
        # Secure cleanup of sensitive data
        try:
            if 'db' in locals(): del db
            if 'decrypted_data' in locals(): del decrypted_data
            if 'hashed_pass' in locals(): del hashed_pass
            # Don't delete contents here as it might be needed by the caller
            vault.secure_wipe()
        except:
            pass
            
    return timedOut

#addnote
def addNote(hashed_pass, db):
    """Add a new note with enhanced security and robust input validation"""
    try:
        while True:
            clear_screen()
            displayHeader(f"{CYAN}📝 ADD A NOTE{RESET}")

            # Title input (required)
            while True:
                note_title = timeoutInput(
                    f"{GOLD}Enter a title for the note (type (.c) to cancel): {RESET}"
                )
                if note_title == ".c" or note_title == timeoutGlobalCode:
                    print(f"{RED}** ALERT: Operation canceled. **{RESET}")
                    return False
                if not note_title.strip():
                    print(f"{RED}** ALERT: Title cannot be empty. **{RESET}")
                    continue
                note_title = note_title.strip()
                break

            # Content input (required)
            while True:
                note_content = timeoutInput(
                    f"{GOLD}Enter the content of the note (type (.c) to cancel): {RESET}"
                )
                if note_content == ".c" or note_content == timeoutGlobalCode:
                    print(f"{RED}** ALERT: Operation canceled. **{RESET}")
                    return False
                if not note_content.strip():
                    print(f"{RED}** ALERT: Content cannot be empty. **{RESET}")
                    continue
                note_content = note_content.strip()
                break

            # Tags input (optional, comma-separated)
            tags_input = timeoutInput(
                f"{GOLD}Enter tags for the note (comma-separated, press 'enter' to skip, type (.c) to cancel): {RESET}"
            )
            if tags_input == ".c" or tags_input == timeoutGlobalCode:
                print(f"{RED}** ALERT: Operation canceled. **{RESET}")
                return False

            # Favorite input
            is_favorite = False
            while True:
                add_favorite = timeoutInput(
                    f"{GOLD}Mark this note as a favorite? (y/n) (type (.c) to cancel): {RESET}"
                ).lower()
                if add_favorite == ".c" or add_favorite == timeoutGlobalCode:
                    print(f"{RED}** ALERT: Operation canceled. **{RESET}")
                    return False
                elif add_favorite == "y":
                    is_favorite = True
                    break
                elif add_favorite == "n":
                    break
                else:
                    print(f"{RED}** ALERT: Invalid input. Please enter 'y' or 'n'. **{RESET}")

            # Privacy input
            is_private = False
            while True:
                privacy_choice = timeoutInput(
                    f"{GOLD}Mark this note as private? (y/n) (type (.c) to cancel): {RESET}"
                ).lower()
                if privacy_choice == ".c" or privacy_choice == timeoutGlobalCode:
                    print(f"{RED}** ALERT: Operation canceled. **{RESET}")
                    return False
                elif privacy_choice == "y":
                    is_private = True
                    break
                elif privacy_choice == "n":
                    break
                else:
                    print(f"{RED}** ALERT: Invalid input. Please enter 'y' or 'n'. **{RESET}")

            # Handle tags based on privacy setting
            if is_private:
                tags = [base64.b64encode(vault.encrypt_data("PRIVATE".encode(), hashed_pass)).decode("utf-8")]
                print(f"{GOLD}Tags automatically set to 'PRIVATE' for private notes.{RESET}")
            else:
                if not tags_input.strip():
                    tags = [base64.b64encode(vault.encrypt_data("N/A".encode(), hashed_pass)).decode("utf-8")]
                else:
                    tags = [
                        base64.b64encode(vault.encrypt_data(tag.strip().encode(), hashed_pass)).decode("utf-8")
                        for tag in tags_input.split(",")
                        if tag.strip()
                    ]
                    if not tags:
                        tags = [base64.b64encode(vault.encrypt_data("N/A".encode(), hashed_pass)).decode("utf-8")]

            try:
                note_id = str(uuid.uuid4())
                encrypted_title = base64.b64encode(vault.encrypt_data(note_title.encode(), hashed_pass)).decode("utf-8")
                encrypted_content = base64.b64encode(vault.encrypt_data(note_content.encode(), hashed_pass)).decode("utf-8")
                db[note_id] = {
                    "title": encrypted_title,
                    "content": encrypted_content,
                    "tags": tags,
                    "favorite": is_favorite,
                    "private": is_private
                }
                encrypted_db = vault.encrypt_data(json.dumps(db).encode(), hashed_pass)
                write_bytes_atomic("Bunker.mmf", encrypted_db)
                clear_screen()
                displayHeader(f"{CYAN}📝 ADD A NOTE{RESET}")
                print(f"{GREEN}** SUCCESS: Note successfully created! **{RESET}")
                if is_private:
                    print(f"\n{GOLD}Created private note:{RESET}")
                    print(f"{GOLD}• Status: {RED}PRIVATE{RESET}")
                    print(f"{GOLD}• Tags: {LPURPLE}PRIVATE{RESET}")
                else:
                    decrypted_tags = []
                    for tag in tags:
                        try:
                            if isinstance(tag, str):
                                tag = tag.encode("utf-8")
                            decrypted_tag = vault.decrypt_data(base64.b64decode(tag), hashed_pass)
                            if isinstance(decrypted_tag, bytes):
                                decrypted_tag = decrypted_tag.decode("utf-8")
                            decrypted_tags.append(decrypted_tag)
                        except Exception:
                            decrypted_tags.append("N/A")
                    print(f"{GOLD}\nCreated note has been added with:{RESET}")
                    print(f"{GOLD}• Title: {LPURPLE}{note_title}{RESET}")
                    print(f"{GOLD}• Tags: {LPURPLE}{', '.join(decrypted_tags)}{RESET}")
                    print(f"{GOLD}• Favorite: {LPURPLE}{'Yes' if is_favorite else 'No'}{RESET}")
            except Exception as e:
                print(f"{RED}** ALERT: Failed to add note. Error: {safe_error(e)} **{RESET}")

            while True:
                userContinue = timeoutInput(
                    f"{GOLD}\nPress 'enter' to return to menu or type 'r' to add another note...{RESET}"
                )
                if userContinue == "":
                    return False if userContinue != timeoutGlobalCode else True
                elif userContinue.lower() == "r":
                    clear_screen()
                    displayHeader(f"{CYAN}📝 ADD A NOTE{RESET}")
                    break
                else:
                    print(
                        f"{RED}** ALERT: Invalid input. Please press 'enter' to return to menu or type 'r' to add another note. **{RESET}"
                    )
    except Exception as e:
        print(f"{RED}** ALERT: Failed to add note: {safe_error(e)} **{RESET}")
        return False
    finally:
        if 'note_title' in locals(): del note_title
        if 'note_content' in locals(): del note_content
        if 'tags_input' in locals(): del tags_input
        if 'hashed_pass' in locals(): del hashed_pass
        vault.secure_wipe()

def displayFavoriteNotes(hashed_pass, db):
    """Display favorite notes with enhanced security"""
    try:
        displayHeader(f"{CYAN}⭐ FAVORITE NOTES{RESET}")

        # Ensure db is properly loaded as a dictionary
        if isinstance(db, bytes):
            try:
                decrypted_data = vault.decrypt_data(db, hashed_pass)
                db = json.loads(decrypted_data.decode("utf-8"))
            except Exception as e:
                print(f"{RED} ** ALERT: Error loading database: {safe_error(e)} **{RESET}")
                return False

        # Filter favorite notes with new structure
        favorites = {
            note_id: info 
            for note_id, info in db.items() 
            if info.get("favorite", False) and "title" in info and "content" in info and "tags" in info
            and "password" not in info  # Exclude profiles
        }

        decrypted_notes = []
        for idx, (note_id, info) in enumerate(favorites.items(), 1):
            try:
                # Decrypt the note title, content, and tags with helpers
                decrypted_title = decode_and_decrypt("title", info, hashed_pass)
                decrypted_content_preview = decode_and_decrypt("content", info, hashed_pass)
                preview_length = 3
                preview_words = decrypted_content_preview.split()[:preview_length]
                preview_text = " ".join(preview_words) + (
                "..." if len(preview_words) < len(decrypted_content_preview.split()) else ""
                )
                tags = [decode_and_decrypt_tag(tag, hashed_pass) for tag in info.get("tags", [])]

                is_favorite = "⭐" if info.get("favorite", False) else ""
                is_private = info.get("private", False) # Get private status
                decrypted_notes.append(
                    (idx, note_id, decrypted_title, preview_text, tags, info, is_favorite, is_private)
                )
            except Exception as e:
                print(f"{RED}Error decrypting note {idx}: {safe_error(e)}{RESET}")
                continue

        num_favorites = len(decrypted_notes)
        if num_favorites == 0:
            print(f"{GOLD}Searching for... 'FAVORITE NOTES':{RESET}\n")
            print(
                f"{GOLD}Found {num_favorites} favorite note{'s' if num_favorites != 1 else ''}:{RESET}"
            )
            print(
                f"\n{RED} ** ALERT: No favorite notes available to display. ADD OR EDIT A NOTE! **{RESET}"
            )
        else:
            print(f"{GOLD}Searching for... 'FAVORITE NOTES':{RESET}\n")
            print(
                f"{GOLD}Found {num_favorites} favorite note{'s' if num_favorites != 1 else ''}:{RESET}"
            )
            for idx, _, title, preview, tags, _, is_favorite, is_private in decrypted_notes:
                print(
                    f"\n{L_CYAN}Note {idx} {is_favorite} {GOLD}| {LPURPLE}Tags: {', '.join(tags)}{RESET}"
                )
                if is_private:
                    print(f"{L_CYAN}Data: {RED}🔒[PRIVATE]{RESET}\n")
                else:
                    print(
                        f"{L_CYAN}Title: {RESET}{title} {GOLD}, {DBLUE}Preview:{RESET} {preview}\n"
                    )

            while True:
                note_range = f"1-{num_favorites}" if num_favorites > 1 else "1"
                view_note = timeoutInput(
                    f"{GOLD}\nSelect the note to view its full content ({note_range}) or type .c to cancel: {RESET}"
                )
                if view_note == ".c":
                    return False
                elif view_note == timeoutGlobalCode:
                    return True
                elif view_note.isdigit():
                    selected_index = int(view_note)
                    if 1 <= selected_index <= num_favorites:
                        selected_note = decrypted_notes[selected_index - 1]
                        _, _, title, _, tags, info, is_favorite, is_private = selected_note

                        try:
                            # Decrypt content with helper
                            decrypted_content = decode_and_decrypt("content", info, hashed_pass)

                            while True:
                                clear_screen()
                                displayHeader(f"{CYAN}⭐ VIEW NOTE CONTENT{RESET}")
                                if is_private:
                                    print(f"{RED}🔒 PRIVATE NOTE ACCESS{RESET}")
                                    verify = timeoutInput(
                                        f"{GOLD}This is a private note. Type 'view' to show content or '.c' to cancel: {RESET}"
                                    ).lower()
                                    if verify == ".c":
                                        return False
                                    elif verify == timeoutGlobalCode:
                                        return True
                                    elif verify != "view":
                                        print(f"{RED} ALERT: Invalid input. Type 'view' to show content or '.c' to cancel. {RESET}")
                                        continue

                                # After verification, show real note details
                                clear_screen()
                                displayHeader(f"{CYAN}⭐ VIEW NOTE CONTENT{RESET}")
                                print(f"{GOLD}You selected note (#{selected_index}):\n{RESET}")
                                print(f"{CYAN}Note {selected_index} {is_favorite}{RESET}")
                                print(f"{GOLD}Title: {RESET}{title}")
                                print(f"{GOLD}Tags: {RESET}{', '.join(tags)}\n")

                                copy_choice = timeoutInput(
                                    f"{GOLD}\nType 'v' to view full content, 'c' to copy content, or '.c' to cancel\nWhat do you want to do?: {RESET}"
                                ).lower()
                                if copy_choice == "v":
                                    if is_private:
                                        clear_screen()
                                        displayHeader(f"{CYAN}⭐ VIEW NOTE CONTENT{RESET}")
                                        print(f"{GOLD}Full Note Details:{RESET}\n")
                                        print(f"{CYAN}Note {selected_index} {is_favorite}{RESET}")
                                        print(f"{GOLD}Title: {RESET}{title}")
                                        print(f"{GOLD}Tags: {RESET}{', '.join(tags)}")
                                        reveal_secret(f"{GOLD}Content: {RESET}", f"{decrypted_content}\n")
                                    else:
                                        reveal_secret(f"\n{GOLD}Full Note Content: {RESET}", f"{decrypted_content}\n")
                                    break
                                elif copy_choice == "c":
                                    _copied = copy_secret(decrypted_content)
                                    print((f"{GREEN}{copy_notice('Note content')}{RESET}\n" if _copied else f"{RED}** ALERT: Could not access the clipboard. **{RESET}\n"))
                                    break
                                elif copy_choice == ".c":
                                    return False
                                elif copy_choice == timeoutGlobalCode:
                                    return True
                                else:
                                    print(f"{RED} ** ALERT: Invalid option. Please enter 'v' to view, 'c' to copy, or '.c' to cancel. **{RESET}")

                            while True:
                                user_choice = timeoutInput(
                                    f"{GOLD}Press 'enter' to return to the main menu or type 'r' to retry... {RESET}"
                                )
                                if user_choice == "r":
                                    return displayFavoriteNotes(hashed_pass, db)
                                elif user_choice == "":
                                    return False  # Return to the main menu
                                elif user_choice == timeoutGlobalCode:
                                    return True
                                else:
                                    print(
                                        f"{RED} ** ALERT: Invalid input. Please press 'enter' to return to the main menu or type 'r' to retry. **{RESET}"
                                    )
                        except Exception as e:
                            print(
                                f"{RED} ** ALERT: Error decrypting content for note '{selected_index}': {safe_error(e)} **{RESET}"
                            )
                            continue
                    else:
                        print(f"{RED} ** ALERT: Invalid note number. **{RESET}")
                else:
                    print(
                        f"{RED} ** ALERT: Invalid input. Please enter a valid note number or '.c' to cancel. **{RESET}"
                    )

        userContinue = timeoutInput(f"{GOLD}\nPress 'enter' to return to menu...{RESET}")
        if userContinue == timeoutGlobalCode:
            return True
        return False
        
    except Exception as e:
        print(f"{RED}** ALERT: Failed to display favorite notes: {safe_error(e)} **{RESET}")
        return False
        
    finally:
        # Clean up sensitive data
        if 'decrypted_content' in locals(): del decrypted_content
        if 'hashed_pass' in locals(): del hashed_pass
        if 'decrypted_notes' in locals(): del decrypted_notes
        vault.secure_wipe()

def editNoteData(hashed_pass, db):
    """Edit note data with enhanced security"""
    try:
        while True:
            clear_screen()
            displayHeader(f"{CYAN}🖍️  EDIT A NOTE{RESET}")

            # Prompt for a search term or allow showing all notes
            edit_title = timeoutInput(
                f"{GOLD}Leave empty to show all, type (.c) to cancel.\nEnter a word or exact title of the note you would like to search for: {RESET}"
            )
            if edit_title == ".c" or edit_title == timeoutGlobalCode:
                print(f"{RED}** ALERT: Operation canceled. **{RESET}")
                return False if edit_title == ".c" else True

            # Find notes matching the title or show all if input is empty
            if edit_title.strip() == "":
                matching_notes = {k: v for k, v in db.items() if "content" in v and "password" not in v}
                clear_screen()
                displayHeader(f"{CYAN}🖍️  EDIT A NOTE{RESET}")
                print(f"{GOLD}Showing all notes as no title was provided.{RESET}\n")
            else:
                matching_notes = {}
                for k, v in db.items():
                    if "title" in v and "content" in v and "password" not in v:
                        try:
                            # Use decryption helper for title
                            decrypted_title = decode_and_decrypt("title", v, hashed_pass).lower()
                            if edit_title.lower() in decrypted_title:
                                matching_notes[k] = v
                        except Exception:
                            continue
                clear_screen()
                displayHeader(f"{CYAN}🖍️  EDIT A NOTE{RESET}")
                print(f"{GOLD}Searching notes for... '{edit_title}':{RESET}\n")

            if not matching_notes:
                print(
                    f"{GOLD}Found {len(matching_notes)} matching note{'s' if len(matching_notes) != 1 else ''}:{RESET}"
                )
                print(
                    f"{RED}\n ** ALERT: Unable to find any notes with input: '{edit_title}' **{RESET}"
                )
                timeoutInput(f"\n{GOLD}Press 'enter' to return to menu... {RESET}")
                return False

            print(
                f"{GOLD}Found {len(matching_notes)} matching note{'s' if len(matching_notes) != 1 else ''}:{RESET}"
            )
            for i, (note_id, info) in enumerate(matching_notes.items(), 1):
                try:
                    is_private = info.get("private", False)
                    
                    # Use decryption helper for title
                    decrypted_title = decode_and_decrypt("title", info, hashed_pass)
                    # Decrypt tags with helper
                    decrypted_tags = [decode_and_decrypt_tag(tag, hashed_pass) for tag in info.get("tags", [])]
                    decrypted_tags_str = ", ".join(decrypted_tags)
                    
                    is_favorite = "⭐" if info.get("favorite", False) else ""
                    
                    print(
                        f"{CYAN}\nNote {i} {is_favorite} {GOLD}| {LPURPLE}Tags: {decrypted_tags_str}{RESET}"
                    )
                    
                    if is_private:
                        print(f"{L_CYAN}Data: {RED}🔒[PRIVATE]{RESET}")
                    else:
                        # Use decryption helper for content
                        decrypted_content = decode_and_decrypt("content", info, hashed_pass)
                        preview_words = decrypted_content.split()[:3]
                        preview_text = " ".join(preview_words) + (
                        "..." if len(preview_words) < len(decrypted_content.split()) else ""
                        )
                        print(
                        f"{L_CYAN}Title: {RESET}{decrypted_title} {GOLD}, {DBLUE}Preview:{RESET} {preview_text}"
                        )
                except Exception as e:
                    print(f"{RED}Error displaying note: {safe_error(e)}{RESET}")

            # Prompt for note selection
            while True:
                note_range = f"1-{len(matching_notes)}" if len(matching_notes) > 1 else "1"
                note_choice = timeoutInput(
                    f"{GOLD}\nSelect the note to edit by number ({note_range}) or type (.c) to cancel: {RESET}"
                )
                if note_choice == ".c" or note_choice == timeoutGlobalCode:
                    print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                    return False if note_choice != timeoutGlobalCode else True
                if (
                    not note_choice.isdigit()
                    or int(note_choice) < 1
                    or int(note_choice) > len(matching_notes)
                ):
                    print(
                        f"{RED} ** ALERT: Invalid choice. Please enter a valid number. **{RESET}"
                    )
                    continue  # Allow user to retry entering a valid number

                selected_index = int(note_choice)
                selected_note = list(matching_notes.items())[selected_index - 1]
                note_id, info = selected_note

                try:
                    # Get current values with enhanced security
                    # Use decryption helpers for current values
                    curr_title = decode_and_decrypt("title", info, hashed_pass)
                    curr_content = decode_and_decrypt("content", info, hashed_pass)
                    curr_tags = [decode_and_decrypt_tag(tag, hashed_pass) for tag in info.get("tags", [])]
                    
                    curr_favorite = info.get("favorite", False)
                    curr_private = info.get("private", False)

                    # Display current note details
                    clear_screen()
                    displayHeader(f"{CYAN}🖍️  EDIT A NOTE{RESET}")
                    print(f"{GOLD}Selected Note for Editing (#{selected_index}): {RESET}")
                    
                    if curr_private:
                        print(f"{RED}🔒 PRIVATE NOTE ACCESS{RESET}")
                        verify = timeoutInput(
                            f"{GOLD}This is a private note. Type 'view' to show content or '.c' to cancel: {RESET}"
                        ).lower()
                        if verify == ".c" or verify == timeoutGlobalCode:
                            return False if verify != timeoutGlobalCode else True
                        elif verify != "view":
                            print(f"{RED}** ALERT: Invalid input. Type 'view' to show content or '.c' to cancel. **{RESET}")
                            continue

                    print(
                        f"\n{CYAN}Note {selected_index} {'⭐' if curr_favorite else ''} {GOLD}| {LPURPLE}Tags: {', '.join(curr_tags)}{RESET}"
                    )
                    print(f"{L_CYAN}Title: {RESET}{curr_title}")
                    reveal_secret(f"{L_CYAN}Content: {RESET}", f"{curr_content}\n")

                    # Prompt for new values
                    new_title = timeoutInput(
                        f"{GOLD}New Title (press 'enter' to keep current: {curr_title}, type (.c) to cancel): {RESET}"
                    )
                    if new_title == ".c" or new_title == timeoutGlobalCode:
                        print(f"{RED}** ALERT: Operation canceled. **{RESET}")
                        return False if new_title != timeoutGlobalCode else True
                    new_title = new_title.strip() or curr_title

                    new_content = timeoutInput(
                        f"{GOLD}New Content (press 'enter' to keep current content): {RESET}"
                    )
                    if new_content == ".c" or new_content == timeoutGlobalCode:
                        print(f"{RED}** ALERT: Operation canceled. **{RESET}")
                        return False if new_content != timeoutGlobalCode else True
                    new_content = new_content.strip() or curr_content

                    new_tags_input = timeoutInput(
                        f"{GOLD}New Tags (comma-separated, press 'enter' to keep current tags): {RESET}"
                    )
                    if new_tags_input == ".c" or new_tags_input == timeoutGlobalCode:
                        print(f"{RED}** ALERT: Operation canceled. **{RESET}")
                        return False if new_tags_input != timeoutGlobalCode else True
                    new_tags = [tag.strip() for tag in new_tags_input.split(",")] if new_tags_input.strip() else curr_tags

                    # Favorite
                    while True:
                        new_favorite_input = timeoutInput(
                        f"{GOLD}Mark as favorite? (y/n, press 'enter' to keep current): {RESET}"
                        ).lower()
                        if new_favorite_input == ".c" or new_favorite_input == timeoutGlobalCode:
                            print(f"{RED}** ALERT: Operation canceled. **{RESET}")
                            return False if new_favorite_input != timeoutGlobalCode else True
                        if new_favorite_input == "":
                            new_favorite = curr_favorite
                            break
                        if new_favorite_input not in ["y", "n"]:
                            print(f"{RED}** ALERT: Invalid input. Please enter 'y', 'n', or press 'enter'. **{RESET}")
                            continue
                        new_favorite = (new_favorite_input == "y")
                        break
                        # Private
                    while True:
                        new_private_input = timeoutInput(
                        f"{GOLD}Mark as private? (y/n, press 'enter' to keep current): {RESET}"
                        ).lower()
                        if new_private_input == ".c" or new_private_input == timeoutGlobalCode:
                            print(f"{RED}** ALERT: Operation canceled. **{RESET}")
                            return False if new_private_input != timeoutGlobalCode else True
                        if new_private_input == "":
                            new_private = curr_private
                            break
                        if new_private_input not in ["y", "n"]:
                            print(f"{RED}** ALERT: Invalid input. Please enter 'y', 'n', or press 'enter'. **{RESET}")
                            continue
                            new_private = (new_private_input == "y")
                            break

                    # If note is marked as private, force tags to be "PRIVATE"
                    if new_private:
                        new_tags = ["PRIVATE"]
                        print(f"{GOLD}Tags automatically set to 'PRIVATE' for private notes.{RESET}")

                    # Encrypt and save new values with enhanced security
                    encrypted_title = base64.b64encode(vault.encrypt_data(new_title.encode(), hashed_pass)).decode("utf-8")
                    encrypted_content = base64.b64encode(vault.encrypt_data(new_content.encode(), hashed_pass)).decode("utf-8")
                    encrypted_tags = [
                        base64.b64encode(vault.encrypt_data(tag.encode(), hashed_pass)).decode("utf-8")
                        for tag in new_tags
                    ]

                    # Update database
                    if note_id in db:
                        del db[note_id]  # Remove old entry
                
                    # Add new entry with same UUID
                    db[note_id] = {
                        "title": encrypted_title,
                        "content": encrypted_content,
                        "tags": encrypted_tags,
                        "favorite": new_favorite,
                        "private": new_private
                    }

                    # Save updated database with enhanced security
                    encrypted_db = vault.encrypt_data(json.dumps(db).encode(), hashed_pass)
                    
                    # Write directly as bytes to ensure consistent format
                    write_bytes_atomic("Bunker.mmf", encrypted_db)

                    # Success message
                    clear_screen()
                    displayHeader(f"{CYAN}🖍️  EDIT A NOTE{RESET}")
                    print(f"{GREEN}** SUCCESS: Note successfully updated! **{RESET}")

                    # Display updated note
                    print(f"\n{GOLD}Updated note details:{RESET}")
                    if new_private:
                        print(f"{CYAN}Note {selected_index} {'⭐' if new_favorite else ''} {GOLD}| {LPURPLE}Tags: PRIVATE{RESET}")
                        print(f"{L_CYAN}Data: {RED}🔒[PRIVATE]{RESET}")
                    else:
                        print(f"{CYAN}Note {selected_index} {'⭐' if new_favorite else ''} {GOLD}| {LPURPLE}Tags: {', '.join(new_tags)}{RESET}")
                        print(f"{L_CYAN}Title: {RESET}{new_title}")
                        preview_words = new_content.split()[:3]
                        preview_text = " ".join(preview_words) + ("..." if len(preview_words) < len(new_content.split()) else "")
                        print(f"{GOLD}Preview: {RESET}{preview_text}")

                    userContinue = timeoutInput(
                        f"{GOLD}\nPress 'enter' to return to menu or 'r' to retry editing...{RESET}"
                    )
                    if userContinue == "" or userContinue == timeoutGlobalCode:
                        return False if userContinue != timeoutGlobalCode else True
                    elif userContinue.lower() == "r":
                        break  # Exit the inner loop and restart the process
                    else:
                        print(f"{RED}** ALERT: Invalid input. Returning to menu. **{RESET}")
                        return False

                except KeyError as e:
                    print(
                        f"{RED}** ALERT: Note '{selected_index}' not found in database. Error: {safe_error(e)} **{RESET}"
                    )
                    userContinue = timeoutInput(
                        f"{GOLD}\nPress 'enter' to return to menu or 'r' to retry editing...{RESET}"
                    )
                    if userContinue == "" or userContinue == timeoutGlobalCode:
                        return False if userContinue != timeoutGlobalCode else True
                    elif userContinue.lower() == "r":
                        break  # Exit the inner loop and restart the process
                    else:
                        print(f"{RED}** ALERT: Invalid input. Returning to menu. **{RESET}")
                        return False

                except Exception as e:
                    print(
                        f"{RED}** ALERT: Failed to edit note '{selected_index}'. Error: {safe_error(e)} **{RESET}"
                    )
                    userContinue = timeoutInput(
                        f"{GOLD}\nPress 'enter' to return to menu or 'r' to retry editing...{RESET}"
                    )
                    if userContinue == "" or userContinue == timeoutGlobalCode:
                        return False if userContinue != timeoutGlobalCode else True
                    elif userContinue.lower() == "r":
                        break  # Exit the inner loop and restart the process
                    else:
                        print(f"{RED}** ALERT: Invalid input. Returning to menu. **{RESET}")
                        return False
                        
    except Exception as e:
        print(f"{RED}** ALERT: Failed to edit note: {safe_error(e)} **{RESET}")
        return False
        
    finally:
        # Clean up sensitive data
        if 'curr_title' in locals(): del curr_title
        if 'curr_content' in locals(): del curr_content
        if 'new_title' in locals(): del new_title
        if 'new_content' in locals(): del new_content
        if 'hashed_pass' in locals(): del hashed_pass
        vault.secure_wipe()

def findNoteData(hashed_pass, db):
    """Find note data with enhanced security"""
    try:
        while True:
            displayHeader(f"{CYAN}🔍  FIND A NOTE BY TITLE{RESET}")
            print(f"{GOLD}Type (.c) to cancel.{RESET}")
            note_title = timeoutInput(
                f"{GOLD}Enter a word or exact title of the note you would like to search for: {RESET}"
            )

            if note_title == ".c" or note_title == timeoutGlobalCode:
                print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                return False if note_title != timeoutGlobalCode else True

            try:
                if not note_title.strip():
                    print(
                        f"{RED}\n ** ALERT: Please enter a valid note title or type (.c) to cancel. **{RESET}"
                    )
                    timeoutInput(f"\n{GOLD}Press 'enter' to return to menu...{RESET}")
                    return False

                clear_screen()
                displayHeader(f"{CYAN}🔍  FIND A NOTE BY TITLE{RESET}")
                print(f"{GOLD}Searching titles for... '{note_title}':{RESET}")

                # Case-insensitive substring search for notes (excluding profiles)
                matches = []
                for note_id, note_info in db.items():
                    if "title" in note_info and "password" not in note_info:
                        try:
                            # Use decryption helper for title
                            decrypted_title = decode_and_decrypt("title", note_info, hashed_pass).lower()
                            
                            if note_title.lower() in decrypted_title:
                                matches.append((note_id, note_info))
                        except Exception:
                            continue

                if matches:
                    print(
                        f"{GOLD}\nClosest match{'es' if len(matches) > 1 else ''}:{RESET}"
                    )
                    decrypted_notes = []
                    for idx, (note_id, note_info) in enumerate(matches, 1):
                        try:
                            # Get note properties
                            is_private = note_info.get("private", False)
                            is_favorite = "⭐" if note_info.get("favorite", False) else ""
                            
                            # Decrypt title, content, and tags with helpers
                            decrypted_title = decode_and_decrypt("title", note_info, hashed_pass)
                            content = decode_and_decrypt("content", note_info, hashed_pass)
                            tags = [decode_and_decrypt_tag(tag, hashed_pass) for tag in note_info.get("tags", [])]
                            tags_str = ", ".join(tags)

                            # Store decrypted note data
                            decrypted_notes.append(
                                (note_id, decrypted_title, tags_str, content, is_favorite, is_private)
                            )

                            # Display note based on privacy setting
                            print(
                                f"\n{L_CYAN}Note {idx} {is_favorite} {GOLD}| {LPURPLE}Tags: {tags_str}{RESET}"
                            )
                            if is_private:
                                print(f"{L_CYAN}Data: {RED}🔒[PRIVATE]{RESET}")
                            else:
                                preview_words = content.split()[:3]
                                preview_text = " ".join(preview_words) + (
                                    "..." if len(preview_words) < len(content.split()) else ""
                                )
                                print(
                                    f"{L_CYAN}Title: {RESET}{decrypted_title} {GOLD}, {DBLUE}Preview:{RESET} {preview_text}"
                                )

                        except Exception as e:
                            print(
                                f"{RED} ** ALERT: Error displaying note {idx}: {safe_error(e)} **{RESET}"
                            )

                    while True:
                        selected_note_index = timeoutInput(
                            f"\n{GOLD}Enter the note number (1-{len(decrypted_notes)}) to view full content, 'r' to retry, or press 'enter' to return to menu: {RESET}"
                        ).lower()

                        if selected_note_index == timeoutGlobalCode:
                            return True
                        elif selected_note_index.isdigit() and 1 <= int(selected_note_index) <= len(decrypted_notes):
                            selected_note = decrypted_notes[int(selected_note_index) - 1]
                            note_id, decrypted_title, tags_str, content, is_favorite, is_private = selected_note

                            while True:
                                clear_screen()
                                displayHeader(f"{CYAN}📝 VIEW NOTE CONTENT{RESET}")

                                if is_private:
                                    print(f"{RED}🔒 PRIVATE NOTE ACCESS{RESET}")
                                    verify = timeoutInput(
                                        f"{GOLD}This is a private note. Type 'view' to show content or '.c' to cancel: {RESET}"
                                    ).lower()
                                    if verify == ".c" or verify == timeoutGlobalCode:
                                        return False if verify != timeoutGlobalCode else True
                                    elif verify != "view":
                                        print(f"{RED}** ALERT: Invalid input. Type 'view' to show content or '.c' to cancel. **{RESET}")
                                        continue

                                    # After verification, show real note details
                                    clear_screen()
                                    displayHeader(f"{CYAN}📝 VIEW NOTE CONTENT{RESET}")
                                    print(f"{GOLD}You selected note (#{selected_note_index}):\n{RESET}")
                                    print(f"{CYAN}Note {selected_note_index} {is_favorite}{RESET}")
                                    print(f"{GOLD}Title: {RESET}{decrypted_title}")
                                    print(f"{GOLD}Tags: {RESET}{tags_str}\n")
                                else:
                                    print(f"{GOLD}You selected note (#{selected_note_index}):\n{RESET}")
                                    print(
                                        f"{CYAN}Note {selected_note_index} {is_favorite} {GOLD}| {LPURPLE}Tags: {tags_str}{RESET}"
                                    )
                                    print(f"{L_CYAN}Title: {RESET}{decrypted_title}")

                                action = timeoutInput(
                                    f"{GOLD}\nType 'v' to view full content, 'c' to copy content, 'r' to retry, or '.c' to cancel: {RESET}"
                                ).lower()

                                if action == "v":
                                    if is_private:
                                        clear_screen()
                                        displayHeader(f"{CYAN}📝 VIEW NOTE CONTENT{RESET}")
                                        print(f"{GOLD}Full Note Details:{RESET}\n")
                                        print(f"{CYAN}Note {selected_note_index} {is_favorite}{RESET}")
                                        print(f"{GOLD}Title: {RESET}{decrypted_title}")
                                        print(f"{GOLD}Tags: {RESET}{tags_str}")
                                        reveal_secret(f"{GOLD}Content: {RESET}", f"{content}\n")
                                    else:
                                        reveal_secret(f"\n{GOLD}Full Note Content: {RESET}", f"{content}\n")
                                    break
                                elif action == "c":
                                    _copied = copy_secret(content)
                                    print(
                                        (f"{GREEN}{copy_notice('Note content')}{RESET}\n" if _copied else f"{RED}** ALERT: Could not access the clipboard. **{RESET}\n")
                                    )
                                    break
                                elif action == "r":
                                    break
                                elif action == ".c" or action == timeoutGlobalCode:
                                    return False if action != timeoutGlobalCode else True
                                else:
                                    print(
                                        f"{RED} ** ALERT: Invalid option. Please enter 'v' to view, 'c' to copy, 'r' to retry, or '.c' to cancel. **{RESET}"
                                    )

                            user_input = timeoutInput(
                                f"{GOLD}Press 'enter' to return to menu or 'r' to retry... {RESET}"
                            ).lower()
                            if user_input == "r":
                                break
                            elif user_input == timeoutGlobalCode:
                                return True
                            return False

                        elif selected_note_index == "r":
                            break
                        elif selected_note_index == "":
                            return False
                        else:
                            print(
                                f"{RED} ** ALERT: Invalid input. Please enter a valid note number, 'r' to retry, or press 'enter' to return to menu. **{RESET}"
                            )

                else:
                    print(
                        f"\n{RED} ** ALERT: Could not find a match for '{note_title}'. **{RESET}"
                    )
                    print(
                        f"{RED} ** ALERT: Please try again with a different title. **{RESET}"
                    )

            except Exception as e:
                print(f"{RED} ** ALERT: Error finding note. Error: {safe_error(e)} **{RESET}")

            userContinue = timeoutInput(
                f"{GOLD}\nPress 'enter' to return to menu or 'r' to retry: {RESET}"
            )
            if userContinue == timeoutGlobalCode:
                return True
            elif userContinue.lower() == "r":
                continue
            return False
            
    except Exception as e:
        print(f"{RED}** ALERT: Failed to find note: {safe_error(e)} **{RESET}")
        return False
        
    finally:
        # Clean up sensitive data
        if 'content' in locals(): del content
        if 'decrypted_title' in locals(): del decrypted_title
        if 'hashed_pass' in locals(): del hashed_pass
        if 'decrypted_notes' in locals(): del decrypted_notes
        vault.secure_wipe()

def manageNotes(hashed_pass, db):
    """Manage notes export/import with enhanced security"""
    try:
        displayHeader(f"{CYAN}⬆️ EXPORT/IMPORT NOTES{RESET}")

        while True:
            choice = timeoutInput(
                f"{GOLD}Would you like to export or import notes? (type 'e' for export, 'i' for import, or (.c) to cancel): {RESET}"
            ).lower()
            if choice == ".c" or choice == timeoutGlobalCode:
                print("Returning to menu")
                return False if choice != timeoutGlobalCode else True

            if choice == "e":
                return exportNotes(hashed_pass, db)
            elif choice == "i":
                return importNotes(hashed_pass, db)
            else:
                print(
                    f"\n{RED}Invalid choice. Please type 'e' to export or 'i' to import.\n{RESET}"
                )
                
    except Exception as e:
        print(f"{RED}** ALERT: Failed to manage notes: {safe_error(e)} **{RESET}")
        return False
        
    finally:
        # Clean up sensitive data
        if 'hashed_pass' in locals(): del hashed_pass
        vault.secure_wipe()

def exportNotes(hashed_pass, db):
    """Export notes with enhanced security using AES-GCM and export passphrase."""
    try:
        displayHeader(f"{CYAN}⬆️  EXPORT NOTES{RESET}")
        valid_notes = {
            note_id: info
            for note_id, info in db.items()
            if (
                isinstance(info, dict)
                and "title" in info
                and "content" in info
                and "password" not in info
            )
        }
        if not valid_notes:
            print(f"{RED} ** ALERT: No notes available to export. ADD OR EDIT A NOTE! **{RESET}")
            timeoutInput(f"{GOLD}\nPress 'enter' to return to menu...{RESET}")
            return False

        # Ask whether to export all or selected
        while True:
            export_all = timeoutInput(
                f"{GOLD}Do you want to export all notes? (y/n) (type (.c) to cancel): {RESET}"
            ).lower()
            if export_all == ".c" or export_all == timeoutGlobalCode:
                print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                return False if export_all != timeoutGlobalCode else True
            if export_all not in ["y", "n"]:
                print(f"{RED} ** ALERT: Please enter 'y' for yes or 'n' for no. **{RESET}")
                continue
            notes_to_export = {}
            if export_all == "y":
                notes_to_export = valid_notes.copy()
                break
            else:
                clear_screen()
                displayHeader(f"{CYAN}⬆️  EXPORT NOTES{RESET}")
                print(f"{CYAN}Available Notes:{RESET}")
                note_list = []
                for note_id, note_data in valid_notes.items():
                    try:
                        decrypted_title = decode_and_decrypt("title", note_data, hashed_pass)
                        is_private = note_data.get("private", False)
                        is_favorite = "⭐" if note_data.get("favorite", False) else ""
                        decrypted_tags = [decode_and_decrypt_tag(tag, hashed_pass) for tag in note_data.get("tags", [])]
                        print(f"{CYAN}Note {len(note_list) + 1} {is_favorite} {GOLD}| {LPURPLE}Tags: {', '.join(decrypted_tags)}{RESET}")
                        if is_private:
                            print(f"{L_CYAN}Data: {RED}🔒[PRIVATE]{RESET}\n")
                        else:
                            print(f"{L_CYAN}Title: {RESET}{decrypted_title}\n")
                        note_list.append(note_id)
                    except Exception as e:
                        print(f"{RED}Error decrypting note {note_id}: {safe_error(e)}{RESET}\n")
                if not note_list:
                    print(f"{RED}No decryptable notes available for export.{RESET}")
                    return False
                while True:
                    selected_notes = timeoutInput(
                        f"{GOLD}\nEnter the numbers of the notes to export, separated by commas (type (.c) to cancel): {RESET}"
                    )
                    if selected_notes == ".c" or selected_notes == timeoutGlobalCode:
                        print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                        return False if selected_notes != timeoutGlobalCode else True
                    try:
                        selected_indices = [
                            int(idx.strip()) - 1 for idx in selected_notes.split(",") if idx.strip().isdigit()
                        ]
                        if all(0 <= i < len(note_list) for i in selected_indices):
                            notes_to_export = {note_list[i]: valid_notes[note_list[i]] for i in selected_indices}
                            break
                        else:
                            print(f"{RED} ** ALERT: Please enter valid note numbers. **{RESET}")
                    except ValueError:
                        print(f"{RED} ** ALERT: Please enter valid note numbers. **{RESET}")
                break

        # Ask if user wants to export encrypted JSON or plain text JSON
        while True:
            export_encrypted = timeoutInput(
                f"{GOLD}Do you want to export as encrypted (y) or plain text (n)? (y/n) (type (.c) to cancel): {RESET}"
            ).lower()
            if export_encrypted == ".c" or export_encrypted == timeoutGlobalCode:
                print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                return False if export_encrypted != timeoutGlobalCode else True
            if export_encrypted in ["y", "n"]:
                export_encrypted = (export_encrypted == "y")
                break
            print(f"{RED} ** ALERT: Please enter 'y' for encrypted or 'n' for plain text. **{RESET}")

        # Ask for filename
        while True:
            file_name = timeoutInput(
                f"{GOLD}Enter the file name to save notes (e.g., export_notes.json) (type (.c) to cancel): {RESET}"
            )
            if file_name == ".c" or file_name == timeoutGlobalCode:
                print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                return False if file_name != timeoutGlobalCode else True
            if not file_name.strip():
                print(f"{RED}** ALERT: Invalid filename. **{RESET}")
                continue
            if not file_name.endswith(".json"):
                file_name += ".json"
            if os.path.isfile(file_name):
                overwrite = timeoutInput(
                    f"{RED}File '{file_name}' already exists. Overwrite? (y/n) (.c to cancel): {RESET}"
                ).lower()
                if overwrite == ".c" or overwrite == timeoutGlobalCode:
                    print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                    return False if overwrite != timeoutGlobalCode else True
                if overwrite != "y":
                    continue
            break

        # Prompt for passphrase if exporting encrypted
        export_key = None
        salt = None
        verifier = None
        generated_passphrase = None
        if export_encrypted:
            timeout = vault.manage_config(hashed_pass).get("timeout_value", 60)
            while True:
                show_password = timeoutInput(
                    f"{GOLD}Do you want to see the password as you type? (y/n) (type (.c) to cancel): {RESET}"
                ).lower()
                if show_password == ".c" or show_password == timeoutGlobalCode:
                    print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                    return False if show_password != timeoutGlobalCode else True
                if show_password not in ["y", "n"]:
                    print(f"{RED} ** ALERT: Please enter 'y' for yes or 'n' for no. **{RESET}")
                    continue
                if show_password == "y":
                    print(f"{RED}⚠️  ** Your passphrase will be shown as you type. ** ⚠️{RESET}")
                    passphrase = timeoutInput(
                        f"{GOLD}Enter a passphrase for encryption (type (.g) to generate, type (.c) to cancel): {RESET}",
                        timeout
                    )
                else:
                    passphrase = timeout_getpass(
                        f"{GOLD}Enter a passphrase for encryption (type (.g) to generate, type (.c) to cancel): {RESET}",
                        timeout
                    )
                if passphrase == timeoutGlobalCode:
                    print(f"{RED} ** ALERT: Operation canceled due to timeout. **{RESET}")
                    return True
                if passphrase == ".c":
                    print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                    return False
                if passphrase == ".g":
                    print(f"\n{GREEN}** SUCCESS: Passphrase generated! **{RESET}")
                    generated_passphrase = generate_password(16)
                    passphrase = generated_passphrase
                    confirm_passphrase = passphrase
                else:
                    if show_password == "y":
                        confirm_passphrase = timeoutInput(
                            f"{GOLD}Confirm passphrase: {RESET}", timeout
                        )
                    else:
                        confirm_passphrase = timeout_getpass(
                            f"{GOLD}Confirm passphrase: {RESET}", timeout
                        )
                    if confirm_passphrase == timeoutGlobalCode:
                        print(f"{RED} ** ALERT: Operation canceled due to timeout. **{RESET}")
                        return True
                    if passphrase != confirm_passphrase:
                        print(f"{RED} ** ALERT: Passphrases do not match. Please try again. **{RESET}")
                        continue
                if len(passphrase) < 8:
                    print(f"{RED} ** ALERT: Passphrase must be at least 8 characters long. **{RESET}")
                    continue
                export_key, salt, verifier = generate_export_encryption(passphrase)
                if export_key is None:
                    print(f"{RED} ** ALERT: Failed to generate encryption key. **{RESET}")
                    continue
                break

        # Decrypt notes for export
        decrypted_notes = {}
        note_counter = 0
        error_counter = 0
        print(f"\n{CYAN}Processing notes...{RESET}")
        for note_id, note_data in notes_to_export.items():
            try:
                dec_title = decode_and_decrypt("title", note_data, hashed_pass)
                dec_content = decode_and_decrypt("content", note_data, hashed_pass)
                dec_tags = [decode_and_decrypt_tag(tag, hashed_pass) for tag in note_data.get("tags", [])]
                minimal_note = {
                    "title": dec_title,
                    "content": dec_content,
                    "favorite": note_data.get("favorite", False),
                    "private": note_data.get("private", False),
                    "tags": dec_tags if dec_tags else ["N/A"],
                }
                note_counter += 1
                decrypted_notes[str(note_counter)] = minimal_note
            except Exception as e:
                error_counter += 1
                print(f"{RED}Note {note_id} failed: {safe_error(e)}{RESET}")

        print(f"\n{CYAN}Note processing complete.{RESET}")
        if note_counter == 0:
            print(f"{RED} ** ALERT: No notes were successfully processed for export. **{RESET}")
            return False

        if error_counter > 0:
            print(f"\n{GOLD}Notes processed: {note_counter} successful, {error_counter} failed{RESET}")
            proceed = timeoutInput(
                f"{GOLD}Continue with export? (y/n) (type (.c) to cancel): {RESET}"
            ).lower()
            if proceed == ".c" or proceed == timeoutGlobalCode:
                print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                return False if proceed != timeoutGlobalCode else True
            if proceed != "y":
                return False

        file_structure = {
            "watermark": "### Property of ZEROMARKSLLC - EXPORTED with BUNKER ###",
            "notes": decrypted_notes
        }

        if not export_encrypted:
            with open_private(file_name) as out_file:
                json.dump(file_structure, out_file, indent=4, ensure_ascii=False)
        else:
            file_json_bytes = json.dumps(file_structure).encode("utf-8")
            encrypted_output = vault.encrypt_data(file_json_bytes, export_key)
            exported_encrypted_object = {
                "watermark": "### Property of ZEROMARKSLLC - EXPORTED with BUNKER ###",
                "salt": base64.b64encode(salt).decode("utf-8"),
                "verifier": base64.b64encode(verifier).decode("utf-8"),
                "data": base64.b64encode(encrypted_output).decode("utf-8"),
            }
            with open_private(file_name) as out_file:
                json.dump(exported_encrypted_object, out_file, indent=4, ensure_ascii=False)

        print(f"\n{GREEN}===== EXPORT SUMMARY ====={RESET}")
        print(f"{GREEN}File: {file_name}{RESET}")
        print(f"{GREEN}Type: {'Encrypted' if export_encrypted else 'Plain text'}{RESET}")
        print(f"{GREEN}Notes exported: {note_counter}{RESET}")
        if error_counter > 0:
            print(f"{RED}Notes failed: {error_counter}{RESET}")

        if export_encrypted and generated_passphrase:
            print(f"\n{RED}╔══════════════════════════════════════════════════════╗{RESET}")
            print(f"{RED}║              SECURITY NOTICE                         ║{RESET}")
            print(f"{RED}╠══════════════════════════════════════════════════════╣{RESET}")
            print(f"{RED}║We have generated a passphrase:                       ║{RESET}")
            print(f"{RED}║                                                      ║{RESET}")
            reveal_secret(f"{RED}║{CYAN}  ", f"{generated_passphrase:<52}{RED}║{RESET}")
            print(f"{RED}║                                                      ║{RESET}")
            print(f"{RED}║ ** IMPORTANT: Store this passphrase securely! **     ║{RESET}")
            print(f"{RED}║ You will need it to decrypt and import notes.        ║{RESET}")
            print(f"{RED}╚══════════════════════════════════════════════════════╝{RESET}")
        elif export_encrypted:
            print(f"\n{RED}╔══════════════════════════════════════════════════════╗{RESET}")
            print(f"{RED}║              SECURITY NOTICE                         ║{RESET}")
            print(f"{RED}╠══════════════════════════════════════════════════════╣{RESET}")
            print(f"{RED}║ ** IMPORTANT: Store your passphrase securely! **     ║{RESET}")
            print(f"{RED}║ You will need it to decrypt and import notes.        ║{RESET}")
            print(f"{RED}╚══════════════════════════════════════════════════════╝{RESET}")

        timeoutInput(f"\n{GOLD}Press 'enter' to continue...{RESET}")
        return True

    except Exception as e:
        print(f"{RED}** ALERT: Failed to export notes: {safe_error(e)} **{RESET}")
        return False
    finally:
        if 'hashed_pass' in locals(): del hashed_pass
        vault.secure_wipe()
def importNotes(hashed_pass, db):
    """Import notes with enhanced security using AES-GCM re-encryption for each note field."""
    try:
        displayHeader(f"{CYAN}⬇️  IMPORT NOTES{RESET}")

        # Gather all .json files from working directory.
        json_files = [f for f in os.listdir('.') if f.endswith('.json')]
        if json_files:
            print(f"\n{CYAN}Available .json files in current directory:{RESET}\n")
            for i, filename in enumerate(json_files, 1):
                print(f"{GOLD}{i}. {filename}{RESET}")
            print(f"\n{GOLD}Enter a number to select a file, or type a filename manually (.c to cancel){RESET}\n")

        while True:
            file_input = timeoutInput(
                f"{GOLD}Choose file to import (1-{len(json_files)} or filename) (.c to cancel): {RESET}"
            )
            if file_input == ".c" or file_input == timeoutGlobalCode:
                print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                return False if file_input != timeoutGlobalCode else True

            # Numeric selection.
            if file_input.isdigit():
                idx = int(file_input) - 1
                if 0 <= idx < len(json_files):
                    file_name = json_files[idx]
                else:
                    print(f"{RED} ** ALERT: Invalid selection. **{RESET}")
                    continue
            else:
                # Manual filename input.
                file_name = file_input if file_input.endswith(".json") else f"{file_input}.json"

            if not os.path.isfile(file_name):
                print(f"{RED} ** ALERT: File '{file_name}' does not exist. **{RESET}")
                continue

            break  # Valid file selected.

        # Load JSON from file.
        try:
            with open(file_name, "r", encoding="utf-8") as f:
                import_data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"{RED}** ALERT: Invalid JSON file format: {safe_error(e)} **{RESET}")
            return False

        # Determine if file is encrypted (has salt/verifier/data) or plain text.
        if (
            isinstance(import_data, dict)
            and "watermark" in import_data
            and import_data["watermark"] == "### Property of ZEROMARKSLLC - EXPORTED with BUNKER ###"
            and "salt" in import_data
            and "verifier" in import_data
            and "data" in import_data
        ):
            print(f"\n{CYAN}Detected: {GREEN}Encrypted BUNKER File{RESET}")
            try:
                salt = base64.b64decode(import_data["salt"])
                verifier = base64.b64decode(import_data["verifier"])
                # Prompt for passphrase
                while True:
                    show_password = timeoutInput(
                        f"{GOLD}Do you want to show your password while typing? (y/n) (type (.c) to cancel): {RESET}"
                    ).lower()
                    if show_password == ".c" or show_password == timeoutGlobalCode:
                        print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                        return False if show_password != timeoutGlobalCode else True
                    if show_password in ["y", "n"]:
                        break
                    print(f"{RED} ** ALERT: Please enter 'y' or 'n'. **{RESET}")
                timeout = vault.manage_config(hashed_pass).get("timeout_value", 60)
                while True:
                    if show_password == "n":
                        passphrase = timeout_getpass(f"{GOLD}Enter the passphrase used for encryption(type (.c) to cancel): {RESET}", timeout)
                    else:
                        print(f"{RED}⚠️  ** Your passphrase will be shown as you type. ** ⚠️{RESET}")
                        passphrase = timeoutInput(f"{GOLD}Enter the passphrase used for encryption(type (.c) to cancel): {RESET}")
                    if passphrase == timeoutGlobalCode:
                        print(f"{RED} ** ALERT: Operation canceled due to timeout. **{RESET}")
                        return True
                    elif passphrase == ".c":
                        print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                        return False
                    export_key = verify_export_encryption(passphrase, salt, verifier)
                    if export_key:
                        break
                    print(f"{RED} ** ALERT: Invalid passphrase. Please try again. **{RESET}")
                b64_data = import_data["data"]
                ciphertext = base64.b64decode(b64_data)
                decrypted_bytes = vault.decrypt_data(ciphertext, export_key)
                file_structure = json.loads(decrypted_bytes.decode("utf-8"))
            except Exception as e:
                print(f"{RED}** ALERT: Failed to decrypt file: {safe_error(e)} **{RESET}")
                return False
        else:
            print(f"\n{CYAN}Detected: {GREEN}Plain text BUNKER File{RESET}")
            file_structure = import_data

        if "notes" not in file_structure:
            print(f"{RED}** ALERT: Invalid file. Missing 'notes' section. **{RESET}")
            return False

        notes_to_import = file_structure["notes"]
        if not notes_to_import:
            print(f"{RED}** ALERT: No notes to import. **{RESET}")
            return False

        # Preview the notes for verification.
        print(f"{CYAN}Notes to be imported:{RESET}\n")
        valid_notes = []
        for idx, (k, note_obj) in enumerate(notes_to_import.items(), start=1):
            if not isinstance(note_obj, dict) or "title" not in note_obj or "content" not in note_obj:
                print(f"{RED}** ALERT: Note {idx} is missing required fields. Skipping... **{RESET}")
                continue

            title_str = note_obj["title"]
            content_str = note_obj["content"]
            is_private = note_obj.get("private", False)
            favorite = "⭐" if note_obj.get("favorite", False) else ""
            tags = note_obj.get("tags", ["N/A"])
            if not isinstance(tags, list) or not tags:
                tags = ["N/A"]
            content_preview_parts = content_str.split()
            content_preview_str = " ".join(content_preview_parts[:3])
            if len(content_preview_parts) > 3:
                content_preview_str += "..."
            print(f"{CYAN}Note {idx} {favorite}{RESET} {GOLD}|{RESET} {LPURPLE}Tags: {', '.join(tags)}{RESET}")
            if is_private:
                print(f"{L_CYAN}Data: {RED}🔒[PRIVATE]{RESET}\n")
            else:
                print(f"{L_CYAN}Title: {RESET}{title_str} {DBLUE}| Preview: {RESET}{content_preview_str}\n")
            valid_notes.append({
                "title": title_str,
                "content": content_str,
                "tags": tags,
                "private": is_private,
                "favorite": note_obj.get("favorite", False)
            })

        if not valid_notes:
            print(f"{RED}** ALERT: No valid notes found to import. **{RESET}")
            return False

        # Confirm import.
        while True:
            confirm = timeoutInput(f"{GOLD}Do you want to import these notes? (y/n) (.c to cancel): {RESET}").lower()
            if confirm == ".c" or confirm == timeoutGlobalCode:
                print(f"{RED}** ALERT: Operation canceled. **{RESET}")
                return False if confirm != timeoutGlobalCode else True
            if confirm in ["y", "n"]:
                break
            print(f"{RED}** ALERT: Please enter 'y' or 'n' or '.c'. **{RESET}")

        if confirm == "n":
            print(f"{RED}** ALERT: Import canceled by user. **{RESET}")
            return False

        if not isinstance(db, dict):
            print(f"{RED}** ALERT: The database is not valid. Creating a new one... **{RESET}")
            db = {}

        imported_count = 0
        for note_obj in valid_notes:
            try:
                note_uuid = str(uuid.uuid4())
                title_str = note_obj["title"]
                content_str = note_obj["content"]
                is_private = note_obj.get("private", False)
                is_favorite = note_obj.get("favorite", False)
                # Encrypt fields and base64 encode for JSON
                enc_title = base64.b64encode(vault.encrypt_data(title_str.encode(), hashed_pass)).decode('utf-8')
                enc_content = base64.b64encode(vault.encrypt_data(content_str.encode(), hashed_pass)).decode('utf-8')
                tags = []
                if is_private:
                    private_tag = base64.b64encode(vault.encrypt_data("PRIVATE".encode(), hashed_pass)).decode('utf-8')
                    tags = [private_tag]
                else:
                    tag_list = note_obj.get("tags", ["N/A"])
                    if not tag_list or not isinstance(tag_list, list):
                        tag_list = ["N/A"]
                    for tag in tag_list:
                        tag_stripped = tag.strip()
                        if tag_stripped:
                            enc_tag = base64.b64encode(vault.encrypt_data(tag_stripped.encode(), hashed_pass)).decode('utf-8')
                            tags.append(enc_tag)
                    if not tags:
                        na_tag = base64.b64encode(vault.encrypt_data("N/A".encode(), hashed_pass)).decode('utf-8')
                        tags = [na_tag]
                db[note_uuid] = {
                    "title": enc_title,
                    "content": enc_content,
                    "tags": tags,
                    "favorite": is_favorite,
                    "private": is_private
                }
                imported_count += 1
            except Exception as e:
                print(f"{RED}** ALERT: Failed to import a note: {safe_error(e)} **{RESET}")
                continue

        if saveDatabase(db, hashed_pass):
            print(f"\n{GREEN}** SUCCESS: Import completed. **{RESET}")
            print(f"{GOLD}Notes imported: {imported_count}{RESET}")
            timeoutInput(f"\n{GOLD}Press 'enter' to return to menu...{RESET}")
            return False
        else:
            print(f"{RED}** ALERT: Failed to save updated database **{RESET}")
            return False

    except Exception as e:
        print(f"{RED}** ALERT: Failed to import notes: {safe_error(e)} **{RESET}")
        return False

    finally:
        if 'hashed_pass' in locals():
            del hashed_pass
        vault.secure_wipe()  
# import/export
def manageProfiles(hashed_pass, db):
    """Manage profiles export/import with enhanced security"""
    try:
        displayHeader(f"{CYAN}⬆️   EXPORT/IMPORT PROFILES{RESET}")
    
        while True:
            choice = timeoutInput(
                f"{GOLD}Would you like to export or import profiles? (type 'e' for export, 'i' for import, or (.c) to cancel): {RESET}"
            ).lower()
            if choice == ".c" or choice == timeoutGlobalCode:
                print("Returning to menu")
                return False if choice != timeoutGlobalCode else True
    
            if choice == "e":
                return exportProfiles(hashed_pass, db)
            elif choice == "i":
                return importProfiles(hashed_pass, db)
            else:
                print(
                    f"{RED}Invalid choice. Please type 'e' to export or 'i' to import.{RESET}"
                )
                
    except Exception as e:
        print(f"{RED}** ALERT: Failed to manage profiles: {safe_error(e)} **{RESET}")
        return False
        
    finally:
        # Clean up sensitive data
        if 'hashed_pass' in locals(): del hashed_pass
        vault.secure_wipe()

def exportProfiles(hashed_pass, db):
    """Export profiles with enhanced security"""
    try:
        displayHeader(f"{CYAN}⬆️  EXPORT PROFILES{RESET}")
        
        # Check for valid profiles first (using same logic as deleteProfileData)
        valid_profiles = {
            profile_id: info
            for profile_id, info in db.items()
            if "domain" in info and "password" in info  # Check for minimal requirements
        }
        
        if not valid_profiles:
            print(f"{GOLD}Searching for... 'All Profiles':{RESET}\n")
            print(f"{RED} ** ALERT: No profiles available to export. ADD OR EDIT A PROFILE! **{RESET}")
            userContinue = timeoutInput(f"{GOLD}\nPress 'enter' to return to menu...{RESET}")
            return False if userContinue != timeoutGlobalCode else True
        
        while True:
            export_all = timeoutInput(
                f"{GOLD}Do you want to export all profiles? (y/n) (type (.c) to cancel): {RESET}"
            ).lower()
            if export_all == ".c" or export_all == timeoutGlobalCode:
                print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                return False if export_all != timeoutGlobalCode else True
    
            profiles_to_export = {}
    
            if export_all == "y":
                profiles_to_export = valid_profiles.copy()
                if not profiles_to_export:
                    print(f"{RED}No profiles available for export.{RESET}")
                    return False
                break
            elif export_all == "n":
                clear_screen()
                displayHeader(f"{CYAN}⬆️  EXPORT PROFILES{RESET}")
    
                # Display available profiles
                print(f"{CYAN}Available Profiles:{RESET}")
                profile_list = []
                for profile_id, profile_data in valid_profiles.items():
                    try:
                        # Use decryption helpers for display
                        decrypted_domain = decode_and_decrypt("domain", profile_data, hashed_pass)
                        decrypted_username = decode_and_decrypt("username", profile_data, hashed_pass)
                        decrypted_email = decode_and_decrypt("email", profile_data, hashed_pass)
                        favorite = "⭐" if profile_data.get("favorite", False) else ""
                        print(f"{CYAN}\nProfile {len(profile_list) + 1} {favorite} {GOLD}| {LPURPLE}Domain: {decrypted_domain}{RESET}")
                        print(f"{DBLUE}Username:{RESET} {decrypted_username} {GOLD}, {DBLUE}Email:{RESET} {decrypted_email}")
                        profile_list.append(profile_id)
                    except Exception as e:
                        print(
                            f"{RED}Error decrypting profile {profile_id}: {safe_error(e)}{RESET}"
                        )
                        continue
    
                if not profile_list:
                    print(f"{RED}No profiles available for export.{RESET}")
                    return False
    
                while True:
                    selected_profiles = timeoutInput(
                        f"{GOLD}\nEnter the numbers of the profiles to export, separated by commas (type (.c) to cancel): {RESET}"
                    )
                    if selected_profiles == ".c" or selected_profiles == timeoutGlobalCode:
                        print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                        return False if selected_profiles != timeoutGlobalCode else True
    
                    try:
                        selected_indices = [
                            int(index.strip()) - 1 for index in selected_profiles.split(",") if index.strip().isdigit()
                        ]
                        if all(
                            0 <= index < len(profile_list) for index in selected_indices
                        ):
                            profiles_to_export = {
                                profile_list[i]: valid_profiles[profile_list[i]]
                                for i in selected_indices
                            }
                            break
                        else:
                            print(
                                f"{RED} ** ALERT: Please enter valid profile numbers between 1 and {len(profile_list)}. **{RESET}"
                            )
                    except ValueError:
                        print(
                            f"{RED} ** ALERT: Please enter valid numbers separated by commas. **{RESET}"
                        )
                break
            else:
                print(f"{RED} ** ALERT: Please enter 'y' for yes or 'n' for no. **{RESET}")
    
        # Ask if user wants to export as encrypted or plain text
        while True:
            export_encrypted = timeoutInput(
                f"{GOLD}Do you want to export as encrypted (y) or plain text (n)? (y/n) (type (.c) to cancel): {RESET}"
            ).lower()
            if export_encrypted == ".c" or export_encrypted == timeoutGlobalCode:
                print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                return False if export_encrypted != timeoutGlobalCode else True
            if export_encrypted in ["y", "n"]:
                export_encrypted = export_encrypted == "y"
                break
            print(f"{RED} ** ALERT: Please enter 'y' for encrypted or 'n' for plain text. **{RESET}")
    
        while True:
            file_name = timeoutInput(
                f"{GOLD}Enter the file name to save profiles (e.g., export_profiles.json) (type (.c) to cancel): {RESET}"
            )
            if file_name == ".c" or file_name == timeoutGlobalCode:
                print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                return False if file_name != timeoutGlobalCode else True
            if not file_name.endswith(".json"):
                file_name += ".json"
            if os.path.isfile(file_name):
                overwrite = timeoutInput(
                    f"{RED}File '{file_name}' already exists. Do you want to overwrite it? (y/n) (type (.c) to cancel): {RESET}"
                ).lower()
                if overwrite == ".c" or overwrite == timeoutGlobalCode:
                    print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                    return False if overwrite != timeoutGlobalCode else True
                if overwrite != "y":
                    continue
            break
    
        # Get passphrase for encryption if needed
        export_key = None
        salt = None
        verifier = None
        generated_passphrase = None
    
        if export_encrypted:
            #temp
            timeout = vault.manage_config(hashed_pass).get("timeout_value", 60)
            #timeout = vault.manage_config(hashed_pass)["timeout_value"]  # Get the timeout value
            while True:
                show_password = timeoutInput(
                    f"{GOLD}Do you want to see the password as you type? (y/n) (type (.c) to cancel): {RESET}"
                ).lower()
                if show_password == ".c" or show_password == timeoutGlobalCode:
                    print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                    return False if show_password != timeoutGlobalCode else True
                if show_password not in ["y", "n"]:
                    print(f"{RED} ** ALERT: Please enter 'y' for yes or 'n' for no. **{RESET}")
                    continue
                if show_password == "y":
                    print(f"{RED}⚠️  ** Your passphrase will be shown as you type. ** ⚠️{RESET}")
                    passphrase = timeoutInput(
                        f"{GOLD}Enter a passphrase for encryption (type (.g) to generate, type (.c) to cancel): {RESET}",
                        timeout
                    )
                else:
                    passphrase = timeout_getpass(
                        f"{GOLD}Enter a passphrase for encryption (type (.g) to generate, type (.c) to cancel): {RESET}",
                        timeout
                    )
                if passphrase == timeoutGlobalCode:
                    print(f"{RED} ** ALERT: Operation canceled due to timeout. **{RESET}")
                    return True
                if passphrase == ".c":
                    print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                    return False
                if passphrase == ".g":
                    print(f"\n{GREEN}** SUCCESS: Passphrase generated! **{RESET}")
                    generated_passphrase = generate_password(16)
                    passphrase = generated_passphrase
                    confirm_passphrase = passphrase
                else:
                    if show_password == "y":
                        confirm_passphrase = timeoutInput(
                            f"{GOLD}Confirm passphrase: {RESET}", timeout
                        )
                    else:
                        confirm_passphrase = timeout_getpass(
                            f"{GOLD}Confirm passphrase: {RESET}", timeout
                        )
                    if confirm_passphrase == timeoutGlobalCode:
                        print(f"{RED} ** ALERT: Operation canceled due to timeout. **{RESET}")
                        return True
                    if passphrase != confirm_passphrase:
                        print(f"{RED} ** ALERT: Passphrases do not match. Please try again. **{RESET}")
                        continue
                if len(passphrase) < 8:
                    print(f"{RED} ** ALERT: Passphrase must be at least 8 characters long. **{RESET}")
                    continue
                export_key, salt, verifier = generate_export_encryption(passphrase)
                if export_key is None:
                    print(f"{RED} ** ALERT: Failed to generate encryption key. **{RESET}")
                    continue
                break
            
        try:
            # First decrypt all profiles using the main encryption
            decrypted_profiles = {}
            profile_counter = 1
            error_counter = 0
    
            print(f"\n{CYAN}Processing profiles...{RESET}")
            for profile_id, profile_data in profiles_to_export.items():
                try:
                    # Verify the profile data structure
                    if not isinstance(profile_data, dict):
                        print(
                            f"{RED}Profile {profile_id} failed: Not a valid dictionary{RESET}"
                        )
                        error_counter += 1
                        continue
    
                    # Verify required fields exist
                    if "domain" not in profile_data or "password" not in profile_data:
                        print(
                            f"{RED}Profile {profile_id} failed: Missing required fields{RESET}"
                        )
                        print(f"Available fields: {', '.join(profile_data.keys())}{RESET}")
                        error_counter += 1
                        continue
    
                    # Attempt to decrypt domain and password with enhanced security
                    try:
                        # Use decryption helpers for domain and password
                        decrypted_domain = decode_and_decrypt("domain", profile_data, hashed_pass)
                        decrypted_password = decode_and_decrypt("password", profile_data, hashed_pass)
                    except Exception as e:
                        print(f"{RED}Profile {profile_id} failed: Decryption error{RESET}")
                        print(f"Error details: {safe_error(e)}{RESET}")
                        error_counter += 1
                        continue
    
                    # Create the minimal profile with verified data
                    minimal_profile = {
                        "domain": decode_and_decrypt("domain", profile_data, hashed_pass),
                        "password": decode_and_decrypt("password", profile_data, hashed_pass),
                        "favorite": profile_data.get("favorite", False),
                    }
    
                    # Handle optional fields
                    for field in ["email", "username"]:   
                        # Use decryption helper for optional fields
                        if field in profile_data and profile_data[field]:
                            decrypted_value = decode_and_decrypt(field, profile_data, hashed_pass)
                            if decrypted_value and decrypted_value != "N/A":
                                minimal_profile[field] = decrypted_value
                    decrypted_profiles[str(profile_counter)] = minimal_profile
                    profile_counter += 1
                except Exception as e:
                    print(
                        f"{GOLD}Warning: Could not decrypt {field} for profile {profile_id}: {safe_error(e)}{RESET}"
                    )
                    error_counter += 1
                    continue
                                # Continue processing - optional fields can fail

    
                except Exception as e:
                    print(f"{RED}Profile {profile_id} failed: Unexpected error{RESET}")
                    print(f"Error details: {safe_error(e)}{RESET}")
                    error_counter += 1
                    continue
    
            print(f"\n{CYAN}Profile processing complete.{RESET}")
            if error_counter > 0:
                print(f"\n{GOLD}Profiles processed: {profile_counter - 1} successful, {error_counter} failed{RESET}")
                proceed = timeoutInput(f"{GOLD}Continue with export? (y/n) (type (.c) to cancel): {RESET}").lower()
                if proceed == ".c" or proceed == timeoutGlobalCode:
                    print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                    return False if proceed != timeoutGlobalCode else True
                if proceed != "y":
                    return False
    
            if profile_counter == 1:
                print(
                    f"{RED} ** ALERT: No profiles were successfully processed for export. **{RESET}"
                )
                return False
    
            # Create the file structure
            file_structure = {
                "watermark": "### Property of ZEROMARKSLLC - EXPORTED with BUNKER ###",
                "profiles": decrypted_profiles
            }
    
            if export_encrypted:
                try:
                    encrypted_export = {
                        "watermark": "### Property of ZEROMARKSLLC - EXPORTED with BUNKER ###",
                        "salt": base64.b64encode(salt).decode("utf-8"),
                        "verifier": base64.b64encode(verifier).decode("utf-8"),
                    }
                    # AES-GCM encrypt the file structure as JSON
                    structure_json = json.dumps(file_structure)
                    encrypted_data = vault.encrypt_data(structure_json.encode(), export_key)
                    encrypted_export["data"] = base64.b64encode(encrypted_data).decode("utf-8")
                    with open_private(file_name) as file:
                        json.dump(encrypted_export, file, indent=4, ensure_ascii=False)
                except Exception as e:
                    print(f"{RED} ** ALERT: Failed to encrypt data. Error: {safe_error(e)} **{RESET}")
                    return False
            else:
                with open_private(file_name) as file:
                    json.dump(file_structure, file, indent=4, ensure_ascii=False)

    
            # Simplified summary display
            print(f"\n{GREEN}╔══════════════════════════════════════════╗{RESET}")
            print(f"{GREEN}║           Export Summary                 ║{RESET}")
            print(f"{GREEN}╠══════════════════════════════════════════╣{RESET}")
            print(f"{GREEN}║ Status: Successfully exported            ║{RESET}")
            print(f"{GREEN}║ File: {file_name:<31}    ║{RESET}")
            print(f"{GREEN}║ Type: {'Encrypted' if export_encrypted else 'Plain text':<31}    ║{RESET}")
            print(f"{GREEN}║ Profiles: {str(profile_counter - 1):<28}   ║{RESET}")
            if error_counter > 0:
                print(f"{RED}║ Failed profiles: {str(error_counter):<24} ║{RESET}")
            print(f"{GREEN}╚══════════════════════════════════════════╝{RESET}")
    
            if export_encrypted and generated_passphrase:
                print(f"\n{RED}╔══════════════════════════════════════════════════════╗{RESET}")
                print(f"{RED}║              SECURITY NOTICE                         ║{RESET}")
                print(f"{RED}╠══════════════════════════════════════════════════════╣{RESET}")
                print(f"{RED}║We have generated a passphrase:                       ║{RESET}")
                print(f"{RED}║                                                      ║{RESET}")
                reveal_secret(f"{RED}║{CYAN}  ", f"{generated_passphrase:<52}{RED}║{RESET}")
                print(f"{RED}║                                                      ║{RESET}")
                print(f"{RED}║ ** IMPORTANT: Store this passphrase securely! **     ║{RESET}")
                print(f"{RED}║ You will need it to decrypt and import profiles.     ║{RESET}")
                print(f"{RED}╚══════════════════════════════════════════════════════╝{RESET}")
            elif export_encrypted:
                print(f"\n{RED}╔══════════════════════════════════════════════════════╗{RESET}")
                print(f"{RED}║              SECURITY NOTICE                         ║{RESET}")
                print(f"{RED}╠══════════════════════════════════════════════════════╣{RESET}")
                print(f"{RED}║ ** IMPORTANT: Store your passphrase securely! **     ║{RESET}")
                print(f"{RED}║ You will need it to decrypt and import profiles.     ║{RESET}")
                print(f"{RED}╚══════════════════════════════════════════════════════╝{RESET}")
    
            userContinue = timeoutInput(f"\n{GOLD}Press 'enter' to continue...{RESET}")
            return False if userContinue != timeoutGlobalCode else True
    
        except Exception as e:
            print(f"{RED} ** ALERT: Failed to export profiles. Error: {safe_error(e)} **{RESET}")
            return False
            
    except Exception as e:
        print(f"{RED} ** ALERT: Failed to export profiles. Error: {safe_error(e)} **{RESET}")
        return False
        
    finally:
        # Clean up sensitive data
        if 'passphrase' in locals(): del passphrase
        if 'confirm_passphrase' in locals(): del confirm_passphrase
        if 'export_key' in locals(): del export_key
        if 'decrypted_domain' in locals(): del decrypted_domain
        if 'decrypted_password' in locals(): del decrypted_password
        if 'decrypted_value' in locals(): del decrypted_value
        if 'decrypted_profiles' in locals(): del decrypted_profiles
        if 'hashed_pass' in locals(): del hashed_pass
        vault.secure_wipe()

def importProfiles(hashed_pass, db):
    """Import profiles with enhanced security and passphrase support."""
    try:
        displayHeader(f"{CYAN}⬇️  IMPORT PROFILES{RESET}")

        # Get all .json files in current directory
        json_files = [f for f in os.listdir('.') if f.endswith('.json')]
        if json_files:
            print(f"\n{CYAN}Available JSON files in current directory:{RESET}\n")
            for i, file in enumerate(json_files, 1):
                print(f"{GOLD}{i}. {file}{RESET}")
            print(f"\n{GOLD}Enter a number to select a file, or type a filename manually (.c to cancel){RESET}\n")

        while True:
            file_input = timeoutInput(
                f"{GOLD}Choose file to import (1-{len(json_files)} or filename): {RESET}"
            )
            if file_input == ".c" or file_input == timeoutGlobalCode:
                print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                return False if file_input != timeoutGlobalCode else True

            # Handle numeric choice
            if file_input.isdigit():
                index = int(file_input) - 1
                if 0 <= index < len(json_files):
                    file_name = json_files[index]
                else:
                    print(f"{RED} ** ALERT: Invalid number. Please choose between 1 and {len(json_files)}. **{RESET}")
                    continue
            else:
                file_name = file_input if file_input.endswith('.json') else f"{file_input}.json"

            if not os.path.isfile(file_name):
                print(f"{RED} ** ALERT: File '{file_name}' does not exist. **{RESET}")
                continue
            break

        try:
            with open(file_name, "r", encoding="utf-8") as file:
                import_data = json.load(file)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"{RED} ** ALERT: Invalid JSON file format: {safe_error(e)} **{RESET}")
            return False

        # Check if this is an encrypted file by looking for salt and verifier
        if (
            "watermark" in import_data and 
            import_data["watermark"] == "### Property of ZEROMARKSLLC - EXPORTED with BUNKER ###" and
            "salt" in import_data and 
            "verifier" in import_data and 
            "data" in import_data
        ):
            print(f"\n{CYAN}Detected: {GREEN}Encrypted BUNKER file{RESET}")
            try:
                salt = base64.b64decode(import_data["salt"])
                verifier = base64.b64decode(import_data["verifier"])
                # Ask about password visibility first
                while True:
                    show_password = timeoutInput(
                        f"{GOLD}Do you want to show your password while typing? (y/n) (type (.c) to cancel): {RESET}"
                    ).lower()
                    if show_password == ".c" or show_password == timeoutGlobalCode:
                        print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                        return False if show_password != timeoutGlobalCode else True
                    if show_password in ["y", "n"]:
                        break
                    print(f"{RED} ** ALERT: Please enter 'y' or 'n'. **{RESET}")
                timeout = vault.manage_config(hashed_pass).get("timeout_value", 60)
                while True:
                    if show_password == "n":
                        passphrase = timeout_getpass(f"{GOLD}Enter the passphrase used for encryption (type (.c) to cancel): {RESET}", timeout)
                    else:
                        print(f"{RED}⚠️  ** Your passphrase will be shown as you type. ** ⚠️{RESET}")
                        passphrase = timeoutInput(f"{GOLD}Enter the passphrase used for encryption (type (.c) to cancel): {RESET}")
                    if passphrase == timeoutGlobalCode:
                        print(f"{RED} ** ALERT: Operation canceled due to timeout. **{RESET}")
                        return True
                    elif passphrase == ".c":
                        print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                        return False
                    export_key = verify_export_encryption(passphrase, salt, verifier)
                    if export_key:
                        break
                    print(f"{RED} ** ALERT: Invalid passphrase. Please try again. **{RESET}")
                encrypted_data = base64.b64decode(import_data["data"])
                decrypted_data = vault.decrypt_data(encrypted_data, export_key)
                file_structure = json.loads(decrypted_data)
                profiles_to_import = file_structure.get("profiles", {})
            except Exception as e:
                print(f"{RED} ** ALERT: Failed to decrypt file. File may be corrupted. Error: {safe_error(e)} **{RESET}")
                userContinue = timeoutInput(f"{GOLD}\nPress 'enter' to try another file or type (.c) to cancel...{RESET}")
                if userContinue == ".c" or userContinue == timeoutGlobalCode:
                    return False if userContinue != timeoutGlobalCode else True
        else:
            if "profiles" in import_data:
                print(f"\n{CYAN}Detected: {GREEN}Plain text BUNKER file{RESET}")
                profiles_to_import = import_data["profiles"]
            else:
                print(f"{RED} ** ALERT: Invalid file format. **{RESET}")
                userContinue = timeoutInput(f"{GOLD}\nPress 'enter' to try another file or type (.c) to cancel...{RESET}")
                if userContinue == ".c" or userContinue == timeoutGlobalCode:
                    return False if userContinue != timeoutGlobalCode else True

        if not profiles_to_import:
            print(f"{RED} ** ALERT: No profiles found in the import file. **{RESET}")
            return False

        # Ask if user wants to display passwords
        show_passwords = timeoutInput(f"{GOLD}Do you want to display passwords? (y/n): {RESET}").lower()
        while True:
            if show_passwords in ['y', 'n']:
                show_passwords = (show_passwords == 'y')
                break
            print(f"{RED} ** ALERT: Please enter 'y' for yes or 'n' for no. **{RESET}")
            show_passwords = timeoutInput(f"{GOLD}Do you want to display passwords? (y/n): {RESET}").lower()

        # Show profiles to be imported
        print(f"\n{CYAN}Profiles to be imported:{RESET}\n")
        for idx, (_, profile_data) in enumerate(profiles_to_import.items(), 1):
            try:
                if "domain" not in profile_data or "password" not in profile_data:
                    print(f"{RED}** ALERT: Profile {idx} missing required fields. Skipping... **{RESET}")
                    continue

                domain = profile_data["domain"]
                email = profile_data.get("email", "N/A")
                username = profile_data.get("username", "N/A")
                password = profile_data["password"] if show_passwords else "********"
                favorite = "⭐" if profile_data.get("favorite", False) else ""

                # Compose tags for display (use domain, email, username as tags for demo, or adjust as needed)
                tags = []
                if email and email != "N/A":
                    tags.append(email)
                if username and username != "N/A":
                    tags.append(username)
                if not tags:
                    tags = ["N/A"]

                # Compose preview (first 3 words of password, or masked)
                if show_passwords:
                    pw_preview = " ".join(password.split()[:3])
                    if len(password.split()) > 3:
                        pw_preview += "..."
                else:
                    pw_preview = "********"

                print(f"{CYAN}Profile {idx} {favorite} {GOLD}| Tags: {', '.join(tags)}{RESET}")
                print(f"{L_CYAN}Domain: {RESET}{domain}")
                reveal_secret(f"{L_CYAN}Password: {RESET}", f"{pw_preview}\n")

            except Exception as e:
                print(f"{RED}Error processing profile {idx}: {safe_error(e)}{RESET}")
                continue
        # Confirm import
        while True:
            confirm = timeoutInput(
                f"\n{GOLD}Do you want to import these profiles? (y/n) (type (.c) to cancel): {RESET}"
            ).lower()
            if confirm == ".c" or confirm == timeoutGlobalCode:
                print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                return False if confirm != timeoutGlobalCode else True
            elif confirm in ['y', 'n']:
                if confirm == 'n':
                    print(f"{RED} ** ALERT: Import canceled by user. **{RESET}")
                    return False
                break
            else:
                print(f"{RED} ** ALERT: Please enter 'y' for yes, 'n' for no, or '.c' to cancel. **{RESET}")

        # Import profiles with enhanced security
        imported_count = 0
        for _, profile_data in profiles_to_import.items():
            try:
                if "domain" not in profile_data or "password" not in profile_data:
                    continue
                profile_id = str(uuid.uuid4())
                encrypted_profile = {
                    "domain": base64.b64encode(vault.encrypt_data(str(profile_data["domain"]).encode(), hashed_pass)).decode("utf-8"),
                    "password": base64.b64encode(vault.encrypt_data(str(profile_data["password"]).encode(), hashed_pass)).decode("utf-8"),
                    "favorite": profile_data.get("favorite", False),
                    "email": base64.b64encode(vault.encrypt_data(str(profile_data.get("email", "N/A")).encode(), hashed_pass)).decode("utf-8"),
                    "username": base64.b64encode(vault.encrypt_data(str(profile_data.get("username", "N/A")).encode(), hashed_pass)).decode("utf-8"),
                }
                db[profile_id] = encrypted_profile
                imported_count += 1
            except Exception as e:
                print(f"{RED} ** ALERT: Error importing profile: {safe_error(e)} **{RESET}")
                continue

        encrypted_db = vault.encrypt_data(json.dumps(db).encode(), hashed_pass)
        write_bytes_atomic("Bunker.mmf", encrypted_db)

        print(f"\n{GREEN}** SUCCESS: Import completed **{RESET}")
        print(f"{GOLD}Profiles imported: {imported_count}{RESET}")
        timeoutInput(f"{GOLD}\nPress 'enter' to return to menu...{RESET}")
        return False

    except Exception as e:
        print(f"{RED} ** ALERT: Failed to import profiles: {safe_error(e)} **{RESET}")
        return False

    finally:
        if 'passphrase' in locals(): del passphrase
        if 'export_key' in locals(): del export_key
        if 'decrypted_data' in locals(): del decrypted_data
        if 'file_structure' in locals(): del file_structure
        if 'profiles_to_import' in locals(): del profiles_to_import
        if 'hashed_pass' in locals(): del hashed_pass
        vault.secure_wipe()

def tagNotes(hashed_pass, db):
    """Sort and find notes by tags with enhanced security"""
    try:
        while True:
            displayHeader(f"{CYAN}🏷️  SORT AND FIND NOTES{RESET}")

            # Ensure db is properly loaded as a dictionary
            if isinstance(db, bytes):
                try:
                    decrypted_data = vault.decrypt_data(db, hashed_pass)
                    db = json.loads(decrypted_data.decode("utf-8"))
                except Exception as e:
                    print(f"{RED} ** ALERT: Error loading database: {safe_error(e)} **{RESET}")
                    return False

            # Collect all tags from the database (excluding profiles)
            all_tags = {}
            for note_id, note in db.items():
                if "password" not in note and "title" in note:  # Ensure it's a note, not a profile
                    for encrypted_tag in note.get("tags", []):
                        try:
                            # Use enhanced security for decryption
                            decrypted_tag = decode_and_decrypt_tag(encrypted_tag, hashed_pass)
                            if decrypted_tag in all_tags:
                                all_tags[decrypted_tag].append(note_id)
                            else:
                                all_tags[decrypted_tag] = [note_id]
                        except Exception as e:
                            print(f"{RED} ** ALERT: Error decrypting tag: {safe_error(e)} **{RESET}")
                            continue

            if not all_tags:
                print(f"{GOLD}Searching for... 'All Note Tags':{RESET}\n")
                print(
                    f"{GOLD}Found {len(all_tags)} note tag{'s' if len(all_tags) != 1 else ''}:\n{RESET}"
                )
                print(
                    f"{RED} ** ALERT: No tags available to display. ADD OR EDIT A NOTE! **{RESET}"
                )
                userContinue = timeoutInput(
                    f"{GOLD}\nPress 'enter' to return to menu...{RESET}"
                )
                return False if userContinue != timeoutGlobalCode else True

            # Display all available tags
            print(f"{GOLD}Searching for... 'All Note Tags':{RESET}\n")
            print(
                f"{GOLD}Found {len(all_tags)} note tag{'s' if len(all_tags) != 1 else ''}:\n{RESET}"
            )
            tags_list = list(all_tags.keys())
            for i, tag in enumerate(tags_list, 1):
                note_count = len(all_tags[tag])
                print(f"{CYAN}Tag {i} {GOLD}| {LPURPLE}Tag: {tag} ({note_count} note{'s' if note_count != 1 else ''}){RESET}")

            # Modified tag selection - removed 'r' to retry option
            while True:  # Loop until valid input is provided
                selected_tag_index = timeoutInput(
                    f"{GOLD}\nEnter a number to filter notes by tag (type (.c) to cancel): {RESET}"
                )
                if selected_tag_index == ".c" or selected_tag_index == timeoutGlobalCode:
                    print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                    return False if selected_tag_index != timeoutGlobalCode else True

                try:
                    selected_tag_index = int(selected_tag_index) - 1
                    if selected_tag_index < 0 or selected_tag_index >= len(tags_list):
                        print(
                            f"{RED} ** ALERT: Invalid selection. Please select a valid tag number.{RESET}"
                        )
                    else:
                        break  # Break the loop if input is valid
                except ValueError:
                    print(f"{RED} ** ALERT: Invalid input. Please enter a number.{RESET}")

            selected_tag = tags_list[selected_tag_index]
            clear_screen()
            displayHeader(f"{CYAN}🏷️ SORT AND FIND NOTES{RESET}")

            # Get the IDs of the notes containing the selected tag
            note_ids_with_selected_tag = all_tags[selected_tag]

            # Find notes that contain the selected tag
            matching_notes = [
                (note_id, note)
                for note_id, note in db.items()
                if note_id in note_ids_with_selected_tag
            ]

            decrypted_notes = []
            for idx, (note_id, info) in enumerate(matching_notes, 1):
                try:
                    is_favorite = "⭐" if info.get("favorite", False) else ""
                    is_private = info.get("private", False)

                    # Decrypt note title with enhanced security
                    decrypted_title = decode_and_decrypt("title", info, hashed_pass)

                    # Decrypt note content for preview (if not private) with enhanced security
                    if not is_private:
                        decrypted_content_preview = decode_and_decrypt("content", info, hashed_pass)
                        preview_words = decrypted_content_preview.split()[:3]
                        preview_text = " ".join(preview_words) + (
                        "..." if len(preview_words) < len(decrypted_content_preview.split()) else ""
                        )
                    else:
                        preview_text = "🔒[PRIVATE]"

                    # Decrypt tags with enhanced security
                    tags = [decode_and_decrypt_tag(tag, hashed_pass) for tag in info.get("tags", [])]

                    decrypted_notes.append(
                        (
                            idx,
                            note_id,
                            decrypted_title,
                            preview_text,
                            tags,
                            info.get("content", ""),
                            is_favorite,
                            is_private
                        )
                    )
                except Exception as e:
                    print(f"{RED}Error decrypting note {idx}: {safe_error(e)}{RESET}")
                    continue

            num_matching_notes = len(decrypted_notes)
            if num_matching_notes == 0:
                print(f"\n{RED} ** ALERT: No notes found with tag '{selected_tag}'.{RESET}")
                userContinue = timeoutInput(
                    f"{GOLD}\nPress 'enter' to return to menu...{RESET}"
                )
                return False if userContinue != timeoutGlobalCode else True
            else:
                # Display matching notes
                print(f"{GOLD}Searching tags for... '{selected_tag}':{RESET}")
                print(
                    f"{GOLD}Found {len(decrypted_notes)} matching note{'s' if len(decrypted_notes) > 1 else ''}:{RESET}\n"
                )
                for idx, _, title, preview, tags, _, is_favorite, is_private in decrypted_notes:
                    print(
                        f"{L_CYAN}Note {idx} {is_favorite} {GOLD}| {LPURPLE}Tags: {', '.join(tags)}{RESET}"
                    )
                    if is_private:
                        print(f"{L_CYAN}Data: {RED}🔒[PRIVATE]{RESET}")
                    else:
                        print(
                            f"{L_CYAN}Title: {RESET}{title} {GOLD}, {DBLUE}Preview:{RESET} {preview}"
                        )
                    print()  # Add line break after each note

                # Handle note selection and viewing - kept 'r' to retry option here
                while True:
                    note_range = f"1-{len(decrypted_notes)}" if len(decrypted_notes) > 1 else "1"
                    view_note = timeoutInput(
                        f"{GOLD}Select the note to view its full content ({note_range}) or type (.c) to cancel, 'r' to retry: {RESET}"
                    )
                    if view_note == ".c":
                        return False
                    elif view_note == timeoutGlobalCode:
                        return True
                    elif view_note.lower() == "r":
                        break
                    elif view_note.isdigit():
                        selected_index = int(view_note)
                        if 1 <= selected_index <= len(decrypted_notes):
                            selected_note = decrypted_notes[selected_index - 1]
                            _, note_id, title, _, tags, encrypted_content, is_favorite, is_private = selected_note

                            try:
                                while True:
                                    clear_screen()
                                    displayHeader(f"{CYAN}🏷️ VIEW NOTE CONTENT{RESET}")
                                    
                                    if is_private:
                                        print(f"{RED}🔒 PRIVATE NOTE ACCESS{RESET}")
                                        verify = timeoutInput(
                                            f"{GOLD}This is a private note. Type 'view' to show content or '.c' to cancel: {RESET}"
                                        ).lower()
                                        if verify == ".c":
                                            return False
                                        elif verify == timeoutGlobalCode:
                                            return True
                                        elif verify != "view":
                                            print(f"{RED}** ALERT: Invalid input. Type 'view' to show content or '.c' to cancel. **{RESET}")
                                            continue

                                        # After verification, show real note details
                                        clear_screen()
                                        displayHeader(f"{CYAN}🏷️ VIEW NOTE CONTENT{RESET}")
                                        print(f"{GOLD}You selected note (#{selected_index}):\n{RESET}")
                                        print(f"{CYAN}Note {selected_index} {is_favorite}{RESET}")
                                        print(f"{GOLD}Title: {RESET}{title}")
                                        print(f"{GOLD}Tags: {RESET}{', '.join(tags)}\n")
                                    else:
                                        print(f"{GOLD}You selected note (#{selected_index}):\n{RESET}")
                                        print(
                                            f"{CYAN}Note {selected_index} {is_favorite} {GOLD}| {LPURPLE}Tags: {', '.join(tags)}{RESET}"
                                        )
                                        print(f"{L_CYAN}Title: {RESET}{title}")
                                    
                                    copy_choice = timeoutInput(
                                        f"{GOLD}\nType 'v' to view full content, 'c' to copy content, or '.c' to cancel\nWhat do you want to do?: {RESET}"
                                    ).lower()
                                    if copy_choice == "v":
                                        # Decrypt the content with enhanced security
                                        decrypted_content = decode_and_decrypt("content", info, hashed_pass)
                                        
                                        if is_private:
                                            clear_screen()
                                            displayHeader(f"{CYAN}🏷️ VIEW NOTE CONTENT{RESET}")
                                            print(f"{GOLD}Full Note Details:{RESET}\n")
                                            print(f"{CYAN}Note {selected_index} {is_favorite}{RESET}")
                                            print(f"{GOLD}Title: {RESET}{title}")
                                            print(f"{GOLD}Tags: {RESET}{', '.join(tags)}")
                                            reveal_secret(f"{GOLD}Content: {RESET}", f"{decrypted_content}\n")
                                        else:
                                            reveal_secret(f"\n{GOLD}Full Note Content: {RESET}", f"{decrypted_content}\n")
                                        break
                                    
                                    elif copy_choice == "c":
                                        # Decrypt the content with enhanced security for copying
                                        decrypted_content = decode_and_decrypt("content", info, hashed_pass)
                                        
                                        _copied = copy_secret(decrypted_content)
                                        print(
                                            (f"{GREEN}{copy_notice('Note content')}{RESET}\n" if _copied else f"{RED}** ALERT: Could not access the clipboard. **{RESET}\n")
                                        )
                                        break
                                    elif copy_choice == ".c":
                                        return False
                                    elif copy_choice == timeoutGlobalCode:
                                        return True
                                    else:
                                        print(
                                            f"{RED} ** ALERT: Invalid option. Please enter 'v' to view, 'c' to copy, or '.c' to cancel. **{RESET}"
                                        )

                                # Kept 'r' to retry option here
                                while True:
                                    user_choice = timeoutInput(
                                        f"{GOLD}Press 'enter' to return to the main menu or type 'r' to retry... {RESET}"
                                    )
                                    if user_choice == "r":
                                        return tagNotes(hashed_pass, db)
                                    elif user_choice == "":
                                        return False  # Return to the main menu
                                    elif user_choice == timeoutGlobalCode:
                                        return True
                                    else:
                                        print(
                                            f"{RED} ** ALERT: Invalid input. Please press 'enter' to return to the main menu or type 'r' to retry. **{RESET}"
                                        )
                            except Exception as e:
                                print(
                                    f"{RED} ** ALERT: Error decrypting content for note '{selected_index}': {safe_error(e)} **{RESET}"
                                )
                                continue
                        else:
                            print(f"{RED} ** ALERT: Invalid note number. **{RESET}")
                    else:
                        print(
                            f"{RED} ** ALERT: Invalid input. Please enter a valid note number or '.c' to cancel. **{RESET}"
                        )

            userContinue = timeoutInput(f"{GOLD}\nPress 'enter' to return to menu...{RESET}")
            return False if userContinue != timeoutGlobalCode else True
            
    except Exception as e:
        print(f"{RED}** ALERT: Failed to tag notes: {safe_error(e)} **{RESET}")
        return False
        
    finally:
        # Clean up sensitive data
        if 'decrypted_content' in locals(): del decrypted_content
        if 'hashed_pass' in locals(): del hashed_pass
        if 'decrypted_notes' in locals(): del decrypted_notes
        vault.secure_wipe()

def deleteNoteData(hashed_pass, db):
    """Delete note data with enhanced security"""
    try:
        while True:
            displayHeader(f"{CYAN}🗑️  DELETE A NOTE{RESET}")
            
            del_title = timeoutInput(
                f"{GOLD}Enter a word or exact title of the note you would like to search for. (leave empty to show all, type (.c) to cancel): {RESET}"
            )
            if del_title == ".c":
                print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                print("Returning to menu")
                return False
            elif del_title == timeoutGlobalCode:
                return True
            
            if del_title.strip() == "":
                matching_notes = {k: v for k, v in db.items() if "title" in v and "content" in v and "password" not in v}
                clear_screen()
                displayHeader(f"{CYAN}🗑️  DELETE A NOTE{RESET}")
                print(f"{GOLD}Showing all notes as no title was provided.{RESET}\n")
            else:
                matching_notes = {}
                for note_id, info in db.items():
                    try:
                        if "title" in info and "content" in info and "password" not in info:
                            # Use decryption helper for title
                            decrypted_title = decode_and_decrypt("title", info, hashed_pass)
                            
                            if del_title.lower() in decrypted_title.lower():
                                matching_notes[note_id] = info
                    except Exception as e:
                        print(f"{RED} ** ALERT: Error decrypting note {note_id}: {safe_error(e)} **{RESET}")
                
                clear_screen()
                displayHeader(f"{CYAN}🗑️  DELETE A NOTE{RESET}")
                print(f"{GOLD}Searching titles for... '{del_title}':{RESET}\n")
            
            if not matching_notes:
                print(f"{RED}\n ** ALERT: No notes available to display. ADD A NOTE! **{RESET}")
                userContinue = timeoutInput(f"\n{GOLD}Press 'enter' to return to menu... {RESET}")
                if userContinue == timeoutGlobalCode:
                    return True
                continue
            
            print(f"{GOLD}Found {len(matching_notes)} matching note{'s' if len(matching_notes) != 1 else ''}:\n{RESET}")
            for i, (note_id, info) in enumerate(matching_notes.items(), 1):
                try:
                    is_private = info.get("private", False)
                    is_favorite = "⭐" if info.get("favorite", False) else ""
                    
                    # Use decryption helper for title
                    decrypted_title = decode_and_decrypt("title", info, hashed_pass)
                    # Decrypt tags with helper
                    decrypted_tags = [decode_and_decrypt_tag(tag, hashed_pass) for tag in info.get("tags", [])]
                    tags_str = ", ".join(decrypted_tags)
                    print(f"{CYAN}Note {i} {is_favorite} {GOLD}| {LPURPLE}Tags: {tags_str}{RESET}")
                    if is_private:
                        print(f"{L_CYAN}Data: {RED}🔒[PRIVATE]{RESET}\n")
                    else:
                    # Use decryption helper for content
                        content = decode_and_decrypt("content", info, hashed_pass)
                        preview_words = content.split()[:3]
                        preview_text = " ".join(preview_words) + ("..." if len(preview_words) < len(content.split()) else "")
                        print(f"{L_CYAN}Title:{RESET} {decrypted_title} {GOLD}, {DBLUE}Content Preview: {RESET}{preview_text}\n")

                except Exception as e:
                    print(f"{RED} ** ALERT: Error displaying note {note_id}: {safe_error(e)} **{RESET}\n")
            
            delete_choice = timeoutInput(
                f"\n{GOLD}Delete all {len(matching_notes)} notes? (type 'a' to delete all, 's' to choose notes, or (.c) to cancel): {RESET}"
            ).lower()
            if delete_choice == ".c":
                print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                print("Returning to menu")
                return False
            elif delete_choice == timeoutGlobalCode:
                return True
            
            keys_to_delete = list(matching_notes.keys()) if delete_choice == "a" else []
            if delete_choice == "s":
                while True:
                    note_nums = timeoutInput(f"{GOLD}\nEnter numbers of notes to delete, separated by commas (type (.c) to cancel): {RESET}")
                    if note_nums == ".c":
                        print(f"{RED} ** ALERT: Operation canceled. **{RESET}")
                        return False
                    elif note_nums == timeoutGlobalCode:
                        return True
                    
                    selected_indices = [n.strip() for n in note_nums.split(",") if n.strip().isdigit()]
                    if all(1 <= int(index) <= len(matching_notes) for index in selected_indices):
                        keys_to_delete = [list(matching_notes.keys())[int(index)-1] for index in selected_indices]
                        break
                    else:
                        print(f"{RED} ** ALERT: Invalid input. Please enter valid note numbers. **{RESET}")
            
            for note_id in keys_to_delete:
                try:
                    del db[note_id]
                except KeyError:
                    print(f"{RED} ** ALERT: Note '{note_id}' not found in database. **{RESET}")
            
            if keys_to_delete:
                clear_screen()
                displayHeader(f"{CYAN}🗑️  DELETE A NOTE{RESET}")
                print(f"{GREEN}** SUCCESS: All selected notes have been deleted! **{RESET}")
                for index, note_id in enumerate(keys_to_delete, 1):
                    try:
                        note_info = matching_notes[note_id]
                        # Use decryption helper for title
                        decrypted_title = decode_and_decrypt("title", note_info, hashed_pass)
                        is_favorite = "⭐" if note_info.get("favorite", False) else ""
                        is_private = note_info.get("private", False)
                        print(f"{CYAN}Note {index} {is_favorite} {GOLD}| {'🔒 PRIVATE NOTE' if is_private else f'Title: {decrypted_title}'}{RESET}")
                    except Exception as e:
                        print(f"{RED} ** ALERT: Error displaying deleted note {index}: {safe_error(e)} **{RESET}")
            
            try:
                # Use enhanced security for encryption and save as binary
                encrypted_db = vault.encrypt_data(json.dumps(db).encode(), hashed_pass)
                write_bytes_atomic("Bunker.mmf", encrypted_db)
            except Exception as e:
                print(f"{RED} ** ALERT: Failed to update database. Error: {safe_error(e)} **{RESET}")
            
            userContinue = timeoutInput(f"{GOLD}\nPress 'enter' to return or type 'r' to retry...{RESET}")
            if userContinue == "r":
                continue
            elif userContinue == timeoutGlobalCode:
                return True
            else:
                return False
                
    except Exception as e:
        print(f"{RED}** ALERT: Failed to delete note: {safe_error(e)} **{RESET}")
        return False
        
    finally:
        # Clean up sensitive data
        if 'decrypted_title' in locals(): del decrypted_title
        if 'content' in locals(): del content
        if 'hashed_pass' in locals(): del hashed_pass
        vault.secure_wipe()
 
def displayAllNotes(hashed_pass, db):
    """Display all notes with enhanced security"""
    try:
        displayHeader(f"{CYAN}📖 VIEW ALL NOTES{RESET}")
        print(f"{GOLD}Searching for... 'All Notes':{RESET}")

        # Modified note filtering to exclude profiles and check for note structure
        notes = {
            note_id: info 
            for note_id, info in db.items() 
            if "title" in info and "content" in info and "tags" in info  # Notes must have title, content and tags
            and "password" not in info  # Exclude profiles (which have password field)
        }
        
        note_count = len(notes)
        print(
            f"\n{GOLD}Found {note_count} matching note{'s' if note_count != 1 else ''}:{RESET}\n"
        )

        decrypted_notes = []
        for idx, (note_id, info) in enumerate(notes.items(), 1):
            if "content" in info:
                try:
                    # Check if note is private
                    is_private = info.get("private", False)

                    # Decrypt the note title and content with helpers
                    decrypted_title = decode_and_decrypt("title", info, hashed_pass)
                    decrypted_content_preview = decode_and_decrypt("content", info, hashed_pass)

                    # Preview only the first few words (if not private)
                    if not is_private:
                        preview_length = 3
                        preview_words = decrypted_content_preview.split()[:preview_length]
                        preview_text = " ".join(preview_words) + (
                            "..."
                            if len(preview_words) < len(decrypted_content_preview.split())
                            else ""
                        )
                    else:
                        preview_text = "🔒 Private Content"

                    # Decrypt tags with enhanced security
                    tags = [decode_and_decrypt_tag(tag, hashed_pass) for tag in info.get("tags", [])]

                    is_favorite = "⭐" if info.get("favorite", False) else ""
                    decrypted_notes.append(
                    (
                    idx,
                    note_id,
                    decrypted_title,
                    preview_text,
                    tags,
                    info,  # store the info dict for later decryption
                    is_favorite,
                    is_private
                    )
                    )
                except Exception as e:
                    print(f"{RED}Error decrypting note {idx}: {safe_error(e)}{RESET}")

        if note_count == 0:
            print(f"{RED} ** ALERT: No notes available to display. ADD A NOTE! **{RESET}")
            userContinue = timeoutInput(f"{GOLD}\nPress 'enter' to return to menu...{RESET}")
            return False if userContinue != timeoutGlobalCode else True
        else:
            for idx, _, title, preview, tags, _, is_favorite, is_private in decrypted_notes:
                tags_str = ", ".join(tags)
                if is_private:
                    print(f"{CYAN}\nNote {idx} {is_favorite} {GOLD}| {LPURPLE}Tags: {tags_str}{RESET}")
                    print(f"{L_CYAN}Data: {RED}🔒[PRIVATE]{RESET}")
                else:
                    print(f"{CYAN}\nNote {idx} {is_favorite} {GOLD}| {LPURPLE}Tags: {tags_str}{RESET}")
                    print(f"{L_CYAN}Title: {RESET}{title} {GOLD}, {DBLUE}Preview:{RESET} {preview}")

            while True:
                note_range = f"1-{note_count}" if note_count > 1 else "1"
                view_note = timeoutInput(
                    f"{GOLD}Select the note to view its full content ({note_range}) or type .c to cancel: {RESET}"
                )
                if view_note == ".c":
                    return False
                elif view_note == timeoutGlobalCode:
                    return True
                elif view_note.isdigit():
                    selected_index = int(view_note)
                    if 1 <= selected_index <= note_count:
                        selected_note = decrypted_notes[selected_index - 1]
                        _, note_id, title, _, tags, info, is_favorite, is_private = selected_note
                        
                        try:
                        # Decrypt content with enhanced security
                            decrypted_content = decode_and_decrypt("content", info, hashed_pass)

                            while True:
                                clear_screen()
                                displayHeader(f"{CYAN}📖 VIEW NOTE CONTENT{RESET}")
                                
                                if is_private:
                                    print(f"{RED}🔒 PRIVATE NOTE ACCESS{RESET}")
                                    verify = timeoutInput(
                                        f"{GOLD}This is a private note. Type 'view' to show content or '.c' to cancel: {RESET}"
                                    ).lower()
                                    if verify == ".c":
                                        return False
                                    elif verify == timeoutGlobalCode:
                                        return True
                                    elif verify != "view":
                                        print(f"{RED}** ALERT: Invalid input. Type 'view' to show content or '.c' to cancel. **{RESET}")
                                        continue
                                    
                                    # After verification, show real note details
                                    clear_screen()
                                    displayHeader(f"{CYAN}📖 VIEW NOTE CONTENT{RESET}")
                                    print(f"{GOLD}You selected note (#{selected_index}):\n{RESET}")
                                    print(f"{CYAN}Note {selected_index} {is_favorite}{RESET}")
                                    print(f"{GOLD}Title: {RESET}{title}")
                                    print(f"{GOLD}Tags: {RESET}{', '.join(tags)}\n")
                                else:
                                    print(f"{GOLD}You selected note (#{selected_index}):\n{RESET}")
                                    print(
                                        f"{CYAN}Note {selected_index} {is_favorite} {GOLD}| {LPURPLE}Tags: {', '.join(tags)}{RESET}"
                                    )
                                    print(f"{L_CYAN}Title: {RESET}{title}")

                                copy_choice = timeoutInput(
                                    f"{GOLD}\nType 'v' to view full content, 'c' to copy content, or '.c' to cancel\nWhat do you want to do?: {RESET}"
                                ).lower()
                                if copy_choice == "v":
                                    # For private notes, show full details with content
                                    if is_private:
                                        clear_screen()
                                        displayHeader(f"{CYAN}📖 VIEW NOTE CONTENT{RESET}")
                                        print(f"{GOLD}Full Note Details:{RESET}\n")
                                        print(f"{CYAN}Note {selected_index} {is_favorite}{RESET}")
                                        print(f"{GOLD}Title: {RESET}{title}")
                                        print(f"{GOLD}Tags: {RESET}{', '.join(tags)}")
                                        reveal_secret(f"{GOLD}Content: {RESET}", f"{decrypted_content}\n")
                                    else:
                                        clear_screen()
                                        displayHeader(f"{CYAN}📖 VIEW NOTE CONTENT{RESET}")
                                        print(f"{GOLD}Full Note Details:{RESET}\n")
                                        print(f"{CYAN}Note {selected_index} {is_favorite}{RESET}")
                                        print(f"{GOLD}Title: {RESET}{title}")
                                        print(f"{GOLD}Tags: {RESET}{', '.join(tags)}")
                                        reveal_secret(f"{GOLD}Content: {RESET}", f"{decrypted_content}\n")
                                    break
                                elif copy_choice == "c":
                                    _copied = copy_secret(decrypted_content)
                                    print(
                                        (f"{GREEN}{copy_notice('Note content')}{RESET}\n" if _copied else f"{RED}** ALERT: Could not access the clipboard. **{RESET}\n")
                                    )
                                    break
                                elif copy_choice == ".c":
                                    return False
                                elif copy_choice == timeoutGlobalCode:
                                    return True
                                else:
                                    print(
                                        f"{RED} ** ALERT: Invalid option. Please enter 'v' to view, 'c' to copy, or '.c' to cancel. **{RESET}"
                                    )

                            while True:
                                user_choice = timeoutInput(
                                    f"{GOLD}Press 'enter' to return to the main menu or type 'r' to retry... {RESET}"
                                )
                                if user_choice == "r":
                                    return displayAllNotes(hashed_pass, db)
                                elif user_choice == "":
                                    return False  # Return to the main menu
                                elif user_choice == timeoutGlobalCode:
                                    return True
                                else:
                                    print(
                                        f"{RED} ** ALERT: Invalid input. Please press 'enter' to return to the main menu or type 'r' to retry. **{RESET}"
                                    )
                        except Exception as e:
                            print(
                                f"{RED} ** ALERT: Error decrypting content for note '{selected_index}': {safe_error(e)}{RESET}"
                            )
                            continue
                    else:
                        print(f"{RED} ** ALERT: Invalid note number. **{RESET}")
                else:
                    print(
                        f"{RED} ** ALERT: Invalid input. Please enter a valid note number or '.c' to cancel. **{RESET}"
                    )

            userContinue = timeoutInput(f"{GOLD}\nPress 'enter' to return to menu...{RESET}")
            return False if userContinue != timeoutGlobalCode else True
            
    except Exception as e:
        print(f"{RED}** ALERT: Failed to display notes: {safe_error(e)} **{RESET}")
        return False
        
    finally:
        # Clean up sensitive data
        if 'decrypted_content' in locals(): del decrypted_content
        if 'decrypted_title' in locals(): del decrypted_title
        if 'hashed_pass' in locals(): del hashed_pass
        if 'decrypted_notes' in locals(): del decrypted_notes
        vault.secure_wipe()

def display_network_information():
    """Display network information with enhanced security and error handling"""
    try:
        print("\n🔹 Network Interfaces:")
        # Use the enhanced get_network_interfaces function for better security
        interfaces = get_network_interfaces()
        
        if not interfaces:
            print(f"{RED}No network interfaces found or access denied{RESET}")
        else:
            for interface, addrs in interfaces.items():
                # Filter out potentially sensitive information
                filtered_addresses = []
                for addr in addrs:
                    if hasattr(addr, 'address') and addr.address:
                        # Mask local IPv4 addresses for security
                        if hasattr(addr, 'family') and addr.family == socket.AF_INET:
                            parts = addr.address.split('.')
                            if len(parts) == 4 and parts[0] in ('10', '172', '192'):
                                filtered_addresses.append(f"{parts[0]}.{parts[1]}.*.*")
                            else:
                                filtered_addresses.append(addr.address)
                        else:
                            filtered_addresses.append(addr.address)
                
                print(f"🔹 {interface}: {', '.join(filtered_addresses)}")
    except Exception as e:
        print(f"{RED} ** ALERT: Error fetching network interfaces: {safe_error(e)} **{RESET}")

    try:
        displaySection("Detailed Network Connection")
        print(f"\n⚠️  ** BEWARE PAGE DOES NOT TIME OUT ** ⚠️ \n")
        
        # Use timeoutInput for consistent timeout handling
        while True:
            user_choice = timeoutInput(
                f"{GOLD}Do you want to see detailed network connections? (y/n) (type (.c) to cancel): {RESET}"
            ).strip().lower()
            
            if user_choice == timeoutGlobalCode:
                return True
            elif user_choice in ["y", "n", ".c"]:
                if user_choice == ".c":
                    print("Returning to menu")
                    return False
                break
            else:
                print(
                    f"{RED} ** ALERT: Invalid input. Please enter 'y', 'n', or '.c' to cancel. **{RESET}"
                )

        detailed = user_choice == "y"
        
        # Use a shorter timeout for better responsiveness
        connections, error = get_network_connections(timeout=3)

        if error:
            print(
                f"{RED} ** ALERT: {error} Try running the script with administrator/root privileges. (pid={os.getpid()}) **{RESET}"
            )
        else:
            if detailed:
                formatted_connections = format_connections(connections, detailed)
                for conn in formatted_connections:
                    print(conn)
                    
                # Add option to filter connections
                filter_option = timeoutInput(
                    f"\n{GOLD}Do you want to filter connections by port or IP? (y/n): {RESET}"
                ).strip().lower()
                
                if filter_option == "y":
                    filter_type = timeoutInput(
                        f"{GOLD}Filter by (p)ort or (i)p?: {RESET}"
                    ).strip().lower()
                    
                    if filter_type == "p":
                        port = timeoutInput(f"{GOLD}Enter port number: {RESET}").strip()
                        if port.isdigit():
                            print(f"\n{CYAN}Connections filtered by port {port}:{RESET}")
                            filtered = [
                                conn for conn in formatted_connections 
                                if f":{port}" in conn
                            ]
                            for conn in filtered:
                                print(conn)
                            if not filtered:
                                print(f"{GOLD}No connections found on port {port}{RESET}")
                    
                    elif filter_type == "i":
                        ip = timeoutInput(f"{GOLD}Enter IP address (partial match allowed): {RESET}").strip()
                        if ip:
                            print(f"\n{CYAN}Connections filtered by IP {ip}:{RESET}")
                            filtered = [
                                conn for conn in formatted_connections 
                                if ip in conn
                            ]
                            for conn in filtered:
                                print(conn)
                            if not filtered:
                                print(f"{GOLD}No connections found with IP {ip}{RESET}")
            else:
                display_network_summary(connections)
                
        # Add option to save network information to file
        save_option = timeoutInput(
            f"\n{GOLD}Do you want to save this network information to a file? (y/n): {RESET}"
        ).strip().lower()
        
        if save_option == "y":
            try:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"network_info_{timestamp}.txt"
                
                with open(filename, "w") as f:
                    f.write("=== NETWORK INFORMATION ===\n")
                    f.write(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    
                    f.write("Network Interfaces:\n")
                    for interface, addrs in get_network_interfaces().items():
                        f.write(f"{interface}: {', '.join(addr.address for addr in addrs if hasattr(addr, 'address'))}\n")
                    
                    f.write("\nNetwork Connections:\n")
                    if connections:
                        for conn in format_connections(connections, detailed=True):
                            f.write(f"{conn}\n")
                    else:
                        f.write("No connection data available\n")
                
                print(f"{GREEN}** SUCCESS: Network information saved to {filename} **{RESET}")
            except Exception as e:
                print(f"{RED} ** ALERT: Error saving network information: {safe_error(e)} **{RESET}")
                
    except Exception as e:
        print(
            f"{RED} ** ALERT: Error displaying network information: {safe_error(e)}. Try running with administrator/root privileges. (pid={os.getpid()}) **{RESET}"
        )
    
    # Wait for user input before returning
    userContinue = timeoutInput(f"{GOLD}\nPress 'enter' to return to menu...{RESET}")
    return False if userContinue != timeoutGlobalCode else True



if __name__ == "__main__":
    main()
