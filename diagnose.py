"""Diagnostic script to troubleshoot Voicemeeter connection issues."""

import ctypes
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from voicemeeter_mcp_server.voicemeeter_api import VoicemeeterAPI


def diagnose_dll_loading():
    """Diagnose DLL loading issues."""
    print("=" * 50)
    print("DIAGNOSING DLL LOADING")
    print("=" * 50)
    
    # Check possible DLL paths
    dll_paths = [
        "VoicemeeterRemote64.dll",
        "VoicemeeterRemote.dll",
        os.path.join(os.environ.get("PROGRAMFILES", ""), "VB", "Voicemeeter", "VoicemeeterRemote64.dll"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "VB", "Voicemeeter", "VoicemeeterRemote.dll"),
        r"C:\Program Files\VB\Voicemeeter\VoicemeeterRemote64.dll",
        r"C:\Program Files (x86)\VB\Voicemeeter\VoicemeeterRemote.dll",
    ]
    
    print("Checking DLL paths:")
    for dll_path in dll_paths:
        exists = os.path.exists(dll_path) if os.path.isabs(dll_path) else False
        print(f"  {dll_path}: {'✅ EXISTS' if exists else '❌ NOT FOUND'}")
        
        if exists or not os.path.isabs(dll_path):
            try:
                dll = ctypes.CDLL(dll_path)
                print(f"    ✅ Successfully loaded DLL")
                
                # Check if login function exists
                if hasattr(dll, 'VBVMR_Login'):
                    print(f"    ✅ VBVMR_Login function found")
                    
                    # Try to call login
                    login_func = dll.VBVMR_Login
                    login_func.restype = ctypes.c_long
                    result = login_func()
                    print(f"    Login result: {result}")
                    
                    if result == 0:
                        print(f"    ✅ Login successful!")
                        
                        # Try logout
                        if hasattr(dll, 'VBVMR_Logout'):
                            logout_func = dll.VBVMR_Logout
                            logout_func.restype = ctypes.c_long
                            logout_result = logout_func()
                            print(f"    Logout result: {logout_result}")
                        
                        return True
                    else:
                        print(f"    ❌ Login failed with code: {result}")
                        if result == 1:
                            print("      (Code 1: Voicemeeter not running)")
                        elif result == -1:
                            print("      (Code -1: Cannot get client)")
                        elif result == -2:
                            print("      (Code -2: Unexpected login)")
                else:
                    print(f"    ❌ VBVMR_Login function not found")
                    
            except OSError as e:
                print(f"    ❌ Failed to load DLL: {e}")
            except Exception as e:
                print(f"    ❌ Error: {e}")
    
    return False


def diagnose_voicemeeter_process():
    """Check if Voicemeeter process is running."""
    print("\n" + "=" * 50)
    print("CHECKING VOICEMEETER PROCESSES")
    print("=" * 50)
    
    import subprocess
    
    try:
        # Check for Voicemeeter processes
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq voicemeeter.exe'], 
                              capture_output=True, text=True)
        if 'voicemeeter.exe' in result.stdout:
            print("✅ voicemeeter.exe is running")
        else:
            print("❌ voicemeeter.exe is not running")
        
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq voicemeeterpro.exe'], 
                              capture_output=True, text=True)
        if 'voicemeeterpro.exe' in result.stdout:
            print("✅ voicemeeterpro.exe is running")
        else:
            print("❌ voicemeeterpro.exe is not running")
            
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq voicemeeter8.exe'], 
                              capture_output=True, text=True)
        if 'voicemeeter8.exe' in result.stdout:
            print("✅ voicemeeter8.exe is running")
        else:
            print("❌ voicemeeter8.exe is not running")
            
    except Exception as e:
        print(f"❌ Error checking processes: {e}")


def test_api_wrapper():
    """Test the API wrapper with detailed error reporting."""
    print("\n" + "=" * 50)
    print("TESTING API WRAPPER")
    print("=" * 50)
    
    api = VoicemeeterAPI()
    
    # Test DLL loading
    print("1. Testing DLL loading...")
    try:
        success = api._load_dll()
        if success:
            print("✅ DLL loaded successfully")
            print(f"   DLL object: {api._dll}")
        else:
            print("❌ Failed to load DLL")
            return False
    except Exception as e:
        print(f"❌ Exception during DLL loading: {e}")
        return False
    
    # Test login
    print("\n2. Testing login...")
    try:
        success = api.login()
        if success:
            print("✅ Login successful")
            print(f"   Connected: {api.is_connected}")
            print(f"   VM Type: {api.voicemeeter_type}")
            
            # Test logout
            print("\n3. Testing logout...")
            logout_success = api.logout()
            print(f"   Logout: {'✅ Success' if logout_success else '❌ Failed'}")
            
            return True
        else:
            print("❌ Login failed")
            return False
    except Exception as e:
        print(f"❌ Exception during login: {e}")
        return False


def main():
    """Main diagnostic function."""
    print("VOICEMEETER MCP SERVER DIAGNOSTICS")
    print("Diagnosing connection issues...")
    print()
    
    # Check processes first
    diagnose_voicemeeter_process()
    
    # Test DLL loading
    dll_success = diagnose_dll_loading()
    
    if not dll_success:
        # Test API wrapper
        api_success = test_api_wrapper()
        
        if not api_success:
            print("\n" + "=" * 50)
            print("TROUBLESHOOTING SUGGESTIONS")
            print("=" * 50)
            print("1. Make sure Voicemeeter is running")
            print("2. Close any other applications using Voicemeeter Remote API")
            print("3. Try running as Administrator")
            print("4. Restart Voicemeeter")
            print("5. Check if Windows Defender is blocking the DLL")
    else:
        print("\n✅ DLL connection working! The issue might be in the API wrapper.")


if __name__ == "__main__":
    main()
