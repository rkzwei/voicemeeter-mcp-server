"""Simple MCP server test."""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from voicemeeter_mcp_server.server import VoicemeeterMCPServer


async def test_mcp_server_simple():
    """Test MCP server with simple method calls."""
    print("=" * 50)
    print("TESTING MCP SERVER SIMPLE")
    print("=" * 50)
    
    server = VoicemeeterMCPServer()
    
    # Test the server initialization
    print("1. Server initialized successfully")
    
    # Test that we can access the API
    print("2. Testing Voicemeeter API access...")
    api = server.vm_api
    
    # Test connection
    print("3. Testing connection...")
    success = api.login()
    if success:
        print(f"[OK] Connected to {api.voicemeeter_type.name}")
        
        # Test parameter access
        print("4. Testing parameter access...")
        mute_value = api.get_parameter_float("Strip[0].mute")
        print(f"  Strip[0].mute: {mute_value}")
        
        # Test version
        version = api.get_version()
        print(f"  Version: {version}")
        
        # Test disconnect
        api.logout()
        print("[OK] Disconnected successfully")
        
        return True
    else:
        print("[ERROR] Failed to connect")
        return False


async def main():
    """Main test function."""
    print("SIMPLE MCP SERVER TEST")
    print("Testing basic server functionality...")
    print()
    
    success = await test_mcp_server_simple()
    
    if success:
        print("\n" + "=" * 50)
        print("🎉 MCP SERVER IS WORKING!")
        print("The Voicemeeter MCP Server is functional on your system.")
        print("=" * 50)
        
        print("\nNext steps:")
        print("1. Add the server to your MCP client configuration:")
        print('   "voicemeeter": {')
        print('     "command": "python",')
        print('     "args": ["-m", "voicemeeter_mcp_server.main"],')
        print(f'     "cwd": "{os.path.dirname(os.path.abspath(__file__))}"')
        print('   }')
        print("\n2. The server provides these capabilities:")
        print("   - Connect/disconnect from Voicemeeter")
        print("   - Get/set any Voicemeeter parameter")
        print("   - Real-time audio level monitoring")
        print("   - Load XML preset configurations")
        print("   - Launch Voicemeeter applications")
        
    else:
        print("\n[ERROR] MCP Server test failed")


if __name__ == "__main__":
    asyncio.run(main())
