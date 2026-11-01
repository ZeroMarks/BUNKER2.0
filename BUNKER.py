
"""
BUNKER - Cross-platform password manager
This is the main entry point that handles platform detection and routing
"""

import os
import time
import importlib.util
import sys

# Add main directory to Python path to ensure imports work correctly
main_dir = os.path.join(os.path.dirname(__file__), 'main')
if main_dir not in sys.path:
    sys.path.insert(0, main_dir)

# Import shared resources
from SHARED_RESOURCES_MOBILE import (
    L_CYAN, GOLD, GREEN, RED, RESET, DPURPLE,
    MUSTARD, VINTAGE, LPURPLE, PURPLE, CYAN,
    clear_screen, ModernUI, detect_device
)
from main.SECURE_IO import install_exit_signal_handlers

def load_interface_module(module_name):
    """Safely load a Python module by name"""
    try:
        module_path = os.path.join(os.path.dirname(__file__), module_name)
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        print(f"{RED}Failed to load {module_name}: {str(e)}{RESET}")
        return None

# BUNKER.py

# DETECT AND ROUTE TO APPROPRIATE INTERFACE
def main():
    try:
        # Clear any copied secret if the terminal is closed or BUNKER is
        # told to stop (SIGHUP/SIGTERM skip the normal cleanup otherwise).
        install_exit_signal_handlers()

        # First detect device type and set up UI preference
        clear_screen()
        
        ui = ModernUI()
        device_type = detect_device()
        
        # Import appropriate interface based on device type
        if device_type in ['mobile', 'tablet']:
            print(f"{GREEN}Detected {device_type} device. Launching mobile-friendly interface...{RESET}")
            try:
                from MOBILE import main as mobile_main
                time.sleep(1)
                return mobile_main(device_type)
            except Exception as e:
                print(f"{RED}Failed to load mobile interface: {str(e)}{RESET}")
                return False
        else:
            print(f"{GREEN}Detected desktop device. Using standard interface...{RESET}")
            try:
                from DESKTOP import main as desktop_main
                time.sleep(1)
                return desktop_main(device_type)
            except Exception as e:
                print(f"{RED}Failed to load desktop interface: {str(e)}{RESET}")
                return False
                
    except Exception as e:
        print(f"{RED}An error occurred: {str(e)}{RESET}")
        return False

# RUN PROGRAM
if __name__ == "__main__":
    main()