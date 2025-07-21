# Installation Guide for AI Agents (Cline)

This guide is specifically designed for AI agents like Cline to automatically install and configure the Voicemeeter MCP Server.

## Prerequisites Check

Before installation, verify these requirements:

1. **Operating System**: Windows (required for Voicemeeter)
2. **Python**: Version 3.8 or higher
3. **Voicemeeter**: Must be installed on the system
   - Download from: https://vb-audio.com/Voicemeeter/
   - Any version works: Standard, Banana, or Potato

## Installation Steps

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/voicemeeter-mcp-server.git
cd voicemeeter-mcp-server

# Install the package in development mode
pip install -e .
```

### 2. Verify Installation

Run the automated installer to check everything:

```bash
python install.py
```

This will:
- Check Python version compatibility
- Verify Voicemeeter installation
- Test DLL loading
- Validate MCP dependencies
- Run basic functionality tests

### 3. Test the Server

Run the simple test to ensure everything works:

```bash
python test_mcp_simple.py
```

Expected output should show:
- ✅ Server initialized successfully
- ✅ Connected to Voicemeeter [TYPE]
- ✅ Parameter access working
- ✅ Version detection working

### 4. Troubleshooting

If installation fails, run the diagnostic script:

```bash
python troubleshoot.py
```

This provides detailed diagnostics including:
- System architecture detection
- Voicemeeter process verification
- DLL path checking
- API connection testing

## MCP Client Configuration

Add this configuration to the MCP client (e.g., Cline settings):

```json
{
  "mcpServers": {
    "voicemeeter": {
      "command": "python",
      "args": ["-m", "voicemeeter_mcp_server.main"],
      "cwd": "/path/to/voicemeeter-mcp-server"
    }
  }
}
```

Replace `/path/to/voicemeeter-mcp-server` with the actual installation path.

## Verification

After configuration, test the MCP server:

1. **Connect**: Use `voicemeeter_connect` tool
2. **Test Parameter**: Try `voicemeeter_get_parameter` with `Strip[0].mute`
3. **Test Levels**: Use `voicemeeter_get_levels` to check audio monitoring

## Common Issues and Solutions

### "Failed to connect to Voicemeeter"
- **Solution**: Ensure Voicemeeter application is running
- **Command**: Launch Voicemeeter manually or use `voicemeeter_run` tool

### "Failed to load DLL"
- **Solution**: Verify Voicemeeter installation path
- **Check**: Run `troubleshoot.py` for detailed DLL diagnostics

### "Permission denied"
- **Solution**: Run installation as Administrator
- **Alternative**: Check Windows UAC settings

## Audio Testing

Generate test audio files for verification:

```bash
python generate_audio_samples.py
```

This creates 15 test files in `audio_samples/` for:
- Basic tone testing
- Stereo channel verification
- Frequency response testing
- Multi-channel identification

## Success Indicators

Installation is successful when:
- ✅ `python test_mcp_simple.py` passes all tests
- ✅ MCP client can connect to the server
- ✅ `voicemeeter_connect` tool works
- ✅ Parameter get/set operations function
- ✅ Audio level monitoring is active

## Support

If you encounter issues:
1. Run `troubleshoot.py` for diagnostics
2. Check the `README.md` for detailed documentation
3. Review `DEVELOPMENT.md` for advanced configuration
4. Ensure Voicemeeter is properly installed and running

The server provides comprehensive error messages and diagnostic information to help resolve any installation issues.
