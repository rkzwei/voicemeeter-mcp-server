# Voicemeeter MCP Server

A Model Context Protocol (MCP) server that provides AI agents with the ability to control and monitor Voicemeeter audio mixer through the Voicemeeter Remote API.

## Features

- **Full Voicemeeter Control**: Connect to and control all versions of Voicemeeter (Standard, Banana, Potato)
- **Parameter Management**: Get and set any Voicemeeter parameter (mute, gain, routing, etc.)
- **Audio Level Monitoring**: Real-time audio level monitoring for all channels
- **Preset Loading**: Load Voicemeeter presets from XML files
- **Dynamic Resources**: Automatically adapts to the connected Voicemeeter type
- **Application Launching**: Start Voicemeeter applications programmatically

## Supported Voicemeeter Versions

- **Voicemeeter Standard**: 2 hardware inputs + 1 virtual input, 3 outputs
- **Voicemeeter Banana**: 3 hardware inputs + 2 virtual inputs, 5 outputs  
- **Voicemeeter Potato**: 5 hardware inputs + 3 virtual inputs, 8 outputs

## Installation

### Prerequisites

- Python 3.8 or higher
- Voicemeeter installed on Windows
- MCP-compatible client (like Claude Desktop)

### Install from Source

```bash
git clone <repository-url>
cd voicemeeter-mcp-server
pip install -e .
```

### Install Development Dependencies

```bash
pip install -e ".[dev]"
```

## Usage

### Running the Server

```bash
voicemeeter-mcp-server
```

Or directly with Python:

```bash
python -m voicemeeter_mcp_server.main
```

### MCP Client Configuration

Add to your MCP client configuration (e.g., Claude Desktop):

```json
{
  "mcpServers": {
    "voicemeeter": {
      "command": "voicemeeter-mcp-server",
      "args": []
    }
  }
}
```

## Available Tools

### Connection Management

- **voicemeeter_connect**: Connect to Voicemeeter Remote API
- **voicemeeter_disconnect**: Disconnect from Voicemeeter Remote API
- **voicemeeter_run**: Launch Voicemeeter application (standard/banana/potato)

### Parameter Control

- **voicemeeter_get_parameter**: Get any Voicemeeter parameter value
- **voicemeeter_set_parameter**: Set any Voicemeeter parameter value

### Audio Monitoring

- **voicemeeter_get_levels**: Get real-time audio levels for specified channels

### Preset Management

- **voicemeeter_load_preset**: Load settings from Voicemeeter XML preset files

## Available Resources

### Static Resources

- **voicemeeter://status**: Connection status and Voicemeeter type information
- **voicemeeter://version**: Voicemeeter version and API information
- **voicemeeter://levels**: Current audio levels for all channels

### Dynamic Resources (when connected)

- **voicemeeter://strip/{id}**: Individual input strip parameters
- **voicemeeter://bus/{id}**: Individual output bus parameters

## Parameter Examples

### Common Strip Parameters

```
Strip[0].mute          # Mute strip 0 (0.0 = unmuted, 1.0 = muted)
Strip[0].gain          # Gain in dB (-60.0 to +12.0)
Strip[0].A1            # Route to Bus A1 (0.0 = off, 1.0 = on)
Strip[0].label         # Strip label (string)
Strip[0].device.name   # Input device name (string)
```

### Common Bus Parameters

```
Bus[0].mute            # Mute bus 0
Bus[0].gain            # Bus gain in dB
Bus[0].eq.on           # EQ on/off
Bus[1].mono            # Mono mode
```

## Example Usage

### Connect and Control

```python
# Connect to Voicemeeter
await mcp_client.call_tool("voicemeeter_connect")

# Mute input strip 0
await mcp_client.call_tool("voicemeeter_set_parameter", {
    "parameter": "Strip[0].mute",
    "value": 1.0
})

# Set gain on bus 1
await mcp_client.call_tool("voicemeeter_set_parameter", {
    "parameter": "Bus[1].gain", 
    "value": -6.0
})

# Get current levels
await mcp_client.call_tool("voicemeeter_get_levels", {
    "level_type": 0,
    "channels": [0, 1, 2, 3]
})
```

### Load Preset

```python
# Load a preset configuration
await mcp_client.call_tool("voicemeeter_load_preset", {
    "preset_path": "C:/path/to/preset.xml"
})
```

## Development

### Project Structure

```
voicemeeter-mcp-server/
├── src/
│   └── voicemeeter_mcp_server/
│       ├── __init__.py
│       ├── main.py           # Entry point
│       ├── server.py         # MCP server implementation
│       └── voicemeeter_api.py # Voicemeeter API wrapper
├── tests/                    # Test files
├── presets/                  # Example presets
├── samples/                  # Documentation and samples (not in git)
├── pyproject.toml           # Project configuration
└── README.md
```

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black src/ tests/
isort src/ tests/
```

### Type Checking

```bash
mypy src/
```

## API Reference

### Voicemeeter Remote API

This server wraps the official Voicemeeter Remote API. For detailed parameter documentation, refer to:

- Voicemeeter Remote API documentation (included in samples/)
- [Official Voicemeeter website](https://vb-audio.com/Voicemeeter/)

### Level Types

- `0`: Input levels (pre-fader)
- `1`: Output levels (pre-fader) 
- `2`: Output levels (post-fader)
- `3`: Output levels (post-mute)

## Troubleshooting

### Automated Troubleshooting

Run the comprehensive troubleshooting script:

```bash
python troubleshoot.py
```

This script will:
- Check system architecture and Python version
- Verify Voicemeeter processes are running
- Test DLL loading and API functions
- Provide detailed diagnostic information

### Common Issues

1. **"Failed to connect to Voicemeeter"**
   - Ensure Voicemeeter is installed and running
   - Try running as administrator
   - Check that no other applications are using the Remote API

2. **"Failed to load DLL"**
   - Verify Voicemeeter installation
   - Check if running 32-bit vs 64-bit Python matches Voicemeeter version

3. **Parameter not found**
   - Verify parameter name syntax: `Strip[0].mute`, `Bus[1].gain`
   - Check if parameter exists for your Voicemeeter version
   - Some parameters are version-specific

### Debug Mode

Set environment variable for verbose logging:

```bash
set VOICEMEETER_DEBUG=1
voicemeeter-mcp-server
```

## Audio Test Samples

Generate audio test files for testing Voicemeeter functionality:

```bash
python generate_audio_samples.py
```

This creates various test files in `audio_samples/`:
- **Basic tones**: 440Hz, 100Hz, 8kHz test tones
- **Stereo test**: Different frequencies in left/right channels
- **Frequency sweep**: 20Hz to 20kHz sweep for frequency response testing
- **Channel identification**: Individual tones for multi-channel testing
- **White noise**: For general audio testing

Use these files to:
- Test audio routing through Voicemeeter
- Verify real-time level monitoring
- Check stereo separation
- Test parameter changes while audio is playing

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Run the test suite
6. Submit a pull request

## Acknowledgments

- VB-Audio Software for Voicemeeter and the Remote API
- Anthropic for the Model Context Protocol specification
- The MCP community for tools and examples
