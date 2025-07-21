"""Simple troubleshooting script for Voicemeeter MCP Server.

This script can be requested by users from AI agents for debugging connection issues.
It provides detailed output with print statements for easy troubleshooting.
"""

import sys
import os
import platform
import ctypes

# Add the source directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from voicemeeter_mcp_server.voicemeeter_api import VoicemeeterAPI


def check_system_info():
    """Check and display system information."""
    print("=" * 60)
    print("SYSTEM INFORMATION")
    print("=" * 60)
    
    print(f"Operating System: {platform.system()} {platform.release()}")
    print(f"Architecture: {platform.machine()}")
    print(f"Python Version: {platform.python_version()}")
    print(f"Python Architecture: {platform.architecture()[0]}")
    
    # Detect if we should use 64-bit or 32-bit DLL
    is_64bit = platform.machine().endswith('64') or platform.architecture()[0] == '64bit'
    print(f"Expected DLL Type: {'64-bit' if is_64bit else '32-bit'}")
    print()


def check_voicemeeter_processes():
    """Check if Voicemeeter processes are running."""
    print("=" * 60)
    print("VOICEMEETER PROCESS CHECK")
    print("=" * 60)
    
    import subprocess
    
    processes_to_check = [
        ("voicemeeter.exe", "Voicemeeter Standard"),
        ("voicemeeterpro.exe", "Voicemeeter Banana"),
        ("voicemeeter8.exe", "Voicemeeter Potato")
    ]
    
    running_processes = []
    
    for process_name, display_name in processes_to_check:
        try:
            result = subprocess.run(['tasklist', '/FI', f'IMAGENAME eq {process_name}'], 
                                  capture_output=True, text=True)
            if process_name in result.stdout:
                print(f"[OK] {display_name} is running ({process_name})")
                running_processes.append(display_name)
            else:
                print(f"[ERROR] {display_name} is not running ({process_name})")
        except Exception as e:
            print(f"[ERROR] Error checking {process_name}: {e}")
    
    if not running_processes:
        print("\n[WARNING]️  WARNING: No Voicemeeter processes detected!")
        print("   Please start Voicemeeter before testing the MCP server.")
    else:
        print(f"\n[OK] Found running Voicemeeter: {', '.join(running_processes)}")
    
    print()
    return len(running_processes) > 0


def check_dll_paths():
    """Check for Voicemeeter DLL files."""
    print("=" * 60)
    print("VOICEMEETER DLL CHECK")
    print("=" * 60)
    
    # Detect system architecture
    is_64bit = platform.machine().endswith('64') or platform.architecture()[0] == '64bit'
    
    dll_paths = []
    
    if is_64bit:
        print("Checking for 64-bit DLLs first...")
        dll_paths.extend([
            ("VoicemeeterRemote64.dll", "System PATH"),
            (os.path.join(os.environ.get("PROGRAMFILES", ""), "VB", "Voicemeeter", "VoicemeeterRemote64.dll"), "Program Files"),
            (os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "VB", "Voicemeeter", "VoicemeeterRemote64.dll"), "Program Files (x86)"),
            (os.path.join(os.environ.get("WINDIR", ""), "System32", "VoicemeeterRemote64.dll"), "System32"),
        ])
        print("Checking for 32-bit DLLs as fallback...")
        dll_paths.extend([
            ("VoicemeeterRemote.dll", "System PATH"),
            (os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "VB", "Voicemeeter", "VoicemeeterRemote.dll"), "Program Files (x86)"),
            (os.path.join(os.environ.get("WINDIR", ""), "SysWOW64", "VoicemeeterRemote.dll"), "SysWOW64"),
        ])
    else:
        print("Checking for 32-bit DLLs...")
        dll_paths.extend([
            ("VoicemeeterRemote.dll", "System PATH"),
            (os.path.join(os.environ.get("PROGRAMFILES", ""), "VB", "Voicemeeter", "VoicemeeterRemote.dll"), "Program Files"),
            (os.path.join(os.environ.get("WINDIR", ""), "System32", "VoicemeeterRemote.dll"), "System32"),
        ])
    
    found_dlls = []
    
    for dll_path, location in dll_paths:
        print(f"\nChecking: {dll_path}")
        print(f"Location: {location}")
        
        # Check if file exists (for absolute paths)
        if os.path.isabs(dll_path):
            if os.path.exists(dll_path):
                print(f"[OK] File exists: {dll_path}")
                found_dlls.append(dll_path)
            else:
                print(f"[ERROR] File not found: {dll_path}")
                continue
        else:
            print(f"🔍 Checking system PATH for: {dll_path}")
        
        # Try to load the DLL
        try:
            dll = ctypes.CDLL(dll_path)
            print(f"[OK] Successfully loaded DLL!")
            print(f"   DLL Handle: {dll}")
            
            # Check for required functions
            required_functions = ['VBVMR_Login', 'VBVMR_Logout', 'VBVMR_GetParameterFloat']
            for func_name in required_functions:
                if hasattr(dll, func_name):
                    print(f"   [OK] Function {func_name} found")
                else:
                    print(f"   [ERROR] Function {func_name} missing")
            
            found_dlls.append(dll_path)
            print(f"   🎯 This DLL should work!")
            break  # Use the first working DLL
            
        except OSError as e:
            print(f"[ERROR] Failed to load DLL: {e}")
            if "193" in str(e):
                print("   (This is usually a 32-bit/64-bit architecture mismatch)")
        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}")
    
    print(f"\nSummary: Found {len(found_dlls)} working DLL(s)")
    return len(found_dlls) > 0


def test_api_connection():
    """Test the Voicemeeter API connection."""
    print("=" * 60)
    print("API CONNECTION TEST")
    print("=" * 60)
    
    print("Creating VoicemeeterAPI instance...")
    api = VoicemeeterAPI()
    
    print("Attempting to connect to Voicemeeter...")
    success = api.login()
    
    if success:
        print("[OK] Successfully connected to Voicemeeter!")
        print(f"   Connection Status: {api.is_connected}")
        print(f"   Voicemeeter Type: {api.voicemeeter_type.name if api.voicemeeter_type else 'Unknown'}")
        
        # Test version
        version = api.get_version()
        print(f"   Voicemeeter Version: {version}")
        
        # Test parameter reading
        print("\nTesting parameter reading...")
        test_params = ["Strip[0].mute", "Strip[0].gain", "Strip[0].label"]
        for param in test_params:
            if "label" in param:
                value = api.get_parameter_string(param)
            else:
                value = api.get_parameter_float(param)
            print(f"   {param}: {value}")
        
        # Test parameter setting (safe test)
        print("\nTesting parameter setting...")
        original_mute = api.get_parameter_float("Strip[0].mute")
        print(f"   Original Strip[0].mute: {original_mute}")
        
        # Toggle mute briefly
        new_mute = 1.0 if original_mute == 0.0 else 0.0
        if api.set_parameter_float("Strip[0].mute", new_mute):
            print(f"   [OK] Successfully set Strip[0].mute to {new_mute}")
            
            # Restore original value
            if api.set_parameter_float("Strip[0].mute", original_mute):
                print(f"   [OK] Successfully restored Strip[0].mute to {original_mute}")
            else:
                print(f"   [ERROR] Failed to restore Strip[0].mute")
        else:
            print(f"   [ERROR] Failed to set Strip[0].mute")
        
        # Test audio levels
        print("\nTesting audio level monitoring...")
        for i in range(4):  # Test first 4 channels
            level = api.get_level(0, i)  # Input levels
            if level is not None:
                print(f"   Input Channel {i}: {level:.3f}")
        
        # Disconnect
        print("\nDisconnecting...")
        logout_success = api.logout()
        print(f"   Logout: {'[OK] Success' if logout_success else '[ERROR] Failed'}")
        
        return True
    else:
        print("[ERROR] Failed to connect to Voicemeeter")
        print("\nPossible causes:")
        print("   1. Voicemeeter is not running")
        print("   2. Another application is using the Voicemeeter Remote API")
        print("   3. DLL loading failed")
        print("   4. Permission issues")
        return False


def main():
    """Main troubleshooting function."""
    print("VOICEMEETER MCP SERVER TROUBLESHOOTING")
    print("This script helps diagnose connection issues with Voicemeeter")
    print("Run this script when the MCP server is not working properly")
    print()
    
    # Step 1: Check system info
    check_system_info()
    
    # Step 2: Check if Voicemeeter is running
    vm_running = check_voicemeeter_processes()
    
    # Step 3: Check DLL availability
    dll_available = check_dll_paths()
    
    # Step 4: Test API connection (only if Voicemeeter is running)
    if vm_running and dll_available:
        api_working = test_api_connection()
    else:
        api_working = False
        print("=" * 60)
        print("SKIPPING API TEST")
        print("=" * 60)
        print("Cannot test API connection because:")
        if not vm_running:
            print("   [ERROR] Voicemeeter is not running")
        if not dll_available:
            print("   [ERROR] No working DLL found")
        print()
    
    # Final summary
    print("=" * 60)
    print("TROUBLESHOOTING SUMMARY")
    print("=" * 60)
    
    if vm_running and dll_available and api_working:
        print("🎉 ALL TESTS PASSED!")
        print("   The Voicemeeter MCP Server should work correctly.")
        print("   If you're still having issues, check your MCP client configuration.")
    else:
        print("[ERROR] ISSUES DETECTED:")
        if not vm_running:
            print("   • Voicemeeter is not running - Please start Voicemeeter")
        if not dll_available:
            print("   • No working Voicemeeter DLL found - Check Voicemeeter installation")
        if vm_running and dll_available and not api_working:
            print("   • API connection failed - Try restarting Voicemeeter")
        
        print("\nRecommended actions:")
        print("   1. Make sure Voicemeeter is installed and running")
        print("   2. Close any other applications using Voicemeeter Remote API")
        print("   3. Try running this script as Administrator")
        print("   4. Restart Voicemeeter and try again")
    
    print("\nFor more help, check the README.md and DEVELOPMENT.md files.")


if __name__ == "__main__":
    main()
