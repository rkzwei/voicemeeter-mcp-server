"""Installation script for Voicemeeter MCP Server."""

import subprocess
import sys
import os
from pathlib import Path


def run_command(command, description):
    """Run a command and handle errors."""
    print(f"\n{description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"[OK] {description} completed successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed")
        print(f"Error: {e.stderr}")
        return False


def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"✗ Python 3.8+ required, found {version.major}.{version.minor}")
        return False
    print(f"[OK] Python {version.major}.{version.minor}.{version.micro} is compatible")
    return True


def check_voicemeeter():
    """Check if Voicemeeter is installed."""
    possible_paths = [
        r"C:\Program Files\VB\Voicemeeter\voicemeeter.exe",
        r"C:\Program Files (x86)\VB\Voicemeeter\voicemeeter.exe",
        r"C:\Program Files\VB\Voicemeeter\voicemeeterpro.exe",
        r"C:\Program Files (x86)\VB\Voicemeeter\voicemeeterpro.exe",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"[OK] Found Voicemeeter at: {path}")
            return True
    
    print("[WARNING] Voicemeeter not found in standard locations")
    print("Please ensure Voicemeeter is installed from: https://vb-audio.com/Voicemeeter/")
    return False


def main():
    """Main installation process."""
    print("Voicemeeter MCP Server Installation")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Check Voicemeeter installation
    check_voicemeeter()
    
    # Install package in development mode
    if not run_command("pip install -e .", "Installing Voicemeeter MCP Server"):
        sys.exit(1)
    
    # Install development dependencies (optional)
    install_dev = input("\nInstall development dependencies? (y/N): ").lower().strip()
    if install_dev in ['y', 'yes']:
        run_command("pip install -e \".[dev]\"", "Installing development dependencies")
    
    print("\n" + "=" * 40)
    print("Installation completed!")
    print("\nNext steps:")
    print("1. Add the server to your MCP client configuration")
    print("2. Test the connection with: voicemeeter-mcp-server")
    print("3. Check the README.md for usage examples")
    
    # Show example MCP configuration
    print("\nExample MCP client configuration:")
    print("""
{
  "mcpServers": {
    "voicemeeter": {
      "command": "voicemeeter-mcp-server",
      "args": []
    }
  }
}
""")


if __name__ == "__main__":
    main()
