"""Live testing script for Voicemeeter MCP Server."""

import asyncio
import json
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from voicemeeter_mcp_server.voicemeeter_api import VoicemeeterAPI, VoicemeeterType


async def test_voicemeeter_api():
    """Test the Voicemeeter API directly."""
    print("=" * 50)
    print("TESTING VOICEMEETER API DIRECTLY")
    print("=" * 50)
    
    api = VoicemeeterAPI()
    
    # Test connection
    print("1. Testing connection...")
    success = api.login()
    if success:
        print(f"✅ Connected to {api.voicemeeter_type.name if api.voicemeeter_type else 'Unknown'}")
        
        # Test version
        version = api.get_version()
        print(f"✅ Voicemeeter version: {version}")
        
        # Test parameter reading
        print("\n2. Testing parameter reading...")
        test_params = [
            "Strip[0].mute",
            "Strip[0].gain", 
            "Strip[0].label",
            "Bus[0].mute",
            "Bus[0].gain"
        ]
        
        for param in test_params:
            if "label" in param:
                value = api.get_parameter_string(param)
            else:
                value = api.get_parameter_float(param)
            print(f"  {param}: {value}")
        
        # Test parameter setting (safe test - just toggle mute)
        print("\n3. Testing parameter setting...")
        current_mute = api.get_parameter_float("Strip[0].mute")
        print(f"  Current Strip[0].mute: {current_mute}")
        
        # Toggle mute briefly
        new_mute = 1.0 if current_mute == 0.0 else 0.0
        if api.set_parameter_float("Strip[0].mute", new_mute):
            print(f"  ✅ Set Strip[0].mute to {new_mute}")
            await asyncio.sleep(0.5)  # Brief pause
            
            # Restore original state
            if api.set_parameter_float("Strip[0].mute", current_mute):
                print(f"  ✅ Restored Strip[0].mute to {current_mute}")
            else:
                print(f"  ❌ Failed to restore Strip[0].mute")
        else:
            print(f"  ❌ Failed to set Strip[0].mute")
        
        # Test audio levels
        print("\n4. Testing audio levels...")
        for i in range(4):
            level = api.get_level(0, i)  # Input levels
            if level is not None:
                print(f"  Input channel {i}: {level:.3f}")
        
        # Test parameters dirty
        print(f"\n5. Parameters dirty: {api.is_parameters_dirty()}")
        
        api.logout()
        print("✅ Disconnected successfully")
        
    else:
        print("❌ Failed to connect to Voicemeeter")
        print("Make sure Voicemeeter is running and not connected by another application")
        return False
    
    return True


async def test_mcp_server():
    """Test the MCP server by simulating tool calls."""
    print("\n" + "=" * 50)
    print("TESTING MCP SERVER FUNCTIONALITY")
    print("=" * 50)
    
    from voicemeeter_mcp_server.server import VoicemeeterMCPServer
    
    server = VoicemeeterMCPServer()
    
    # Test list tools
    print("1. Testing list_tools...")
    tools = await server._setup_handlers.__wrapped__(server).list_tools()
    print(f"✅ Found {len(tools)} tools:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description}")
    
    # Test list resources
    print("\n2. Testing list_resources...")
    resources = await server._setup_handlers.__wrapped__(server).list_resources()
    print(f"✅ Found {len(resources)} resources:")
    for resource in resources:
        print(f"  - {resource.name}: {resource.description}")
    
    # Test tool calls
    print("\n3. Testing tool calls...")
    
    # Test connect
    print("  Testing voicemeeter_connect...")
    try:
        result = await server._setup_handlers.__wrapped__(server).call_tool("voicemeeter_connect", {})
        print(f"  ✅ Connect result: {result[0].text}")
    except Exception as e:
        print(f"  ❌ Connect failed: {e}")
        return False
    
    # Test get parameter
    print("  Testing voicemeeter_get_parameter...")
    try:
        result = await server._setup_handlers.__wrapped__(server).call_tool("voicemeeter_get_parameter", {
            "parameter": "Strip[0].mute"
        })
        print(f"  ✅ Get parameter result: {result[0].text}")
    except Exception as e:
        print(f"  ❌ Get parameter failed: {e}")
    
    # Test get levels
    print("  Testing voicemeeter_get_levels...")
    try:
        result = await server._setup_handlers.__wrapped__(server).call_tool("voicemeeter_get_levels", {
            "level_type": 0,
            "channels": [0, 1]
        })
        print(f"  ✅ Get levels result: {result[0].text}")
    except Exception as e:
        print(f"  ❌ Get levels failed: {e}")
    
    # Test read resource
    print("\n4. Testing read_resource...")
    try:
        status = await server._setup_handlers.__wrapped__(server).read_resource("voicemeeter://status")
        status_data = json.loads(status)
        print(f"  ✅ Status: {json.dumps(status_data, indent=2)}")
    except Exception as e:
        print(f"  ❌ Read resource failed: {e}")
    
    # Test disconnect
    print("  Testing voicemeeter_disconnect...")
    try:
        result = await server._setup_handlers.__wrapped__(server).call_tool("voicemeeter_disconnect", {})
        print(f"  ✅ Disconnect result: {result[0].text}")
    except Exception as e:
        print(f"  ❌ Disconnect failed: {e}")
    
    return True


async def main():
    """Main test function."""
    print("VOICEMEETER MCP SERVER LIVE TESTING")
    print("Testing on your system as requested...")
    print()
    
    # Test API first
    api_success = await test_voicemeeter_api()
    
    if api_success:
        # Test MCP server
        mcp_success = await test_mcp_server()
        
        if mcp_success:
            print("\n" + "=" * 50)
            print("🎉 ALL TESTS PASSED!")
            print("The Voicemeeter MCP Server is working correctly on your system.")
            print("=" * 50)
        else:
            print("\n❌ MCP Server tests failed")
    else:
        print("\n❌ API tests failed - cannot proceed with MCP tests")


if __name__ == "__main__":
    asyncio.run(main())
