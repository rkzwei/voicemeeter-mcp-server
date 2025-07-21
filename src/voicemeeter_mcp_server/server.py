"""MCP Server for Voicemeeter Remote API."""

import asyncio
import json
from typing import Any, Dict, List, Optional, Union
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel,
)
from pydantic import BaseModel, Field

from .voicemeeter_api import VoicemeeterAPI, VoicemeeterType


class VoicemeeterMCPServer:
    """MCP Server for Voicemeeter Remote API integration."""

    def __init__(self):
        self.server = Server("voicemeeter-mcp-server")
        self.vm_api = VoicemeeterAPI()
        self._setup_handlers()

    def _is_valid_parameter_name(self, param_name: str) -> bool:
        """Validate parameter name format for security."""
        import re
        
        # Allow only valid Voicemeeter parameter patterns
        # Examples: Strip[0].mute, Bus[1].gain, Strip[2].device.name
        pattern = r'^(Strip|Bus)\[\d+\]\.[a-zA-Z][a-zA-Z0-9_.]*$'
        
        if not re.match(pattern, param_name):
            return False
            
        # Additional length check
        if len(param_name) > 100:
            return False
            
        return True

    def _setup_handlers(self):
        """Setup MCP server handlers."""

        @self.server.list_resources()
        async def handle_list_resources() -> List[Resource]:
            """List available Voicemeeter resources."""
            resources = [
                Resource(
                    uri="voicemeeter://status",
                    name="Voicemeeter Status",
                    description="Current status and connection information",
                    mimeType="application/json",
                ),
                Resource(
                    uri="voicemeeter://version",
                    name="Voicemeeter Version",
                    description="Voicemeeter version information",
                    mimeType="application/json",
                ),
                Resource(
                    uri="voicemeeter://levels",
                    name="Audio Levels",
                    description="Current audio levels for all channels",
                    mimeType="application/json",
                ),
            ]

            if self.vm_api.is_connected:
                # Add dynamic resources based on Voicemeeter type
                vm_type = self.vm_api.voicemeeter_type
                if vm_type == VoicemeeterType.VOICEMEETER:
                    # Standard Voicemeeter: 2 inputs, 1 virtual input, 3 outputs
                    for i in range(3):
                        resources.append(
                            Resource(
                                uri=f"voicemeeter://strip/{i}",
                                name=f"Strip {i}",
                                description=f"Input strip {i} parameters",
                                mimeType="application/json",
                            )
                        )
                    for i in range(3):
                        resources.append(
                            Resource(
                                uri=f"voicemeeter://bus/{i}",
                                name=f"Bus {i}",
                                description=f"Output bus {i} parameters",
                                mimeType="application/json",
                            )
                        )
                elif vm_type == VoicemeeterType.VOICEMEETER_BANANA:
                    # Banana: 3 inputs, 2 virtual inputs, 5 outputs
                    for i in range(5):
                        resources.append(
                            Resource(
                                uri=f"voicemeeter://strip/{i}",
                                name=f"Strip {i}",
                                description=f"Input strip {i} parameters",
                                mimeType="application/json",
                            )
                        )
                    for i in range(5):
                        resources.append(
                            Resource(
                                uri=f"voicemeeter://bus/{i}",
                                name=f"Bus {i}",
                                description=f"Output bus {i} parameters",
                                mimeType="application/json",
                            )
                        )
                elif vm_type == VoicemeeterType.VOICEMEETER_POTATO:
                    # Potato: 5 inputs, 3 virtual inputs, 8 outputs
                    for i in range(8):
                        resources.append(
                            Resource(
                                uri=f"voicemeeter://strip/{i}",
                                name=f"Strip {i}",
                                description=f"Input strip {i} parameters",
                                mimeType="application/json",
                            )
                        )
                    for i in range(8):
                        resources.append(
                            Resource(
                                uri=f"voicemeeter://bus/{i}",
                                name=f"Bus {i}",
                                description=f"Output bus {i} parameters",
                                mimeType="application/json",
                            )
                        )

            return resources

        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """Read a Voicemeeter resource."""
            if not self.vm_api.is_connected:
                if not self.vm_api.login():
                    return json.dumps({"error": "Failed to connect to Voicemeeter"})

            if uri == "voicemeeter://status":
                return json.dumps(
                    {
                        "connected": self.vm_api.is_connected,
                        "type": (
                            self.vm_api.voicemeeter_type.name
                            if self.vm_api.voicemeeter_type
                            else None
                        ),
                        "parameters_dirty": self.vm_api.is_parameters_dirty(),
                    }
                )

            elif uri == "voicemeeter://version":
                version = self.vm_api.get_version()
                return json.dumps(
                    {
                        "version": version,
                        "api_version": "1.0.0",
                    }
                )

            elif uri == "voicemeeter://levels":
                levels = {}
                # Get input levels (type 0)
                for i in range(8):  # Max channels
                    level = self.vm_api.get_level(0, i)
                    if level is not None:
                        levels[f"input_{i}"] = level

                # Get output levels (type 3)
                for i in range(8):  # Max channels
                    level = self.vm_api.get_level(3, i)
                    if level is not None:
                        levels[f"output_{i}"] = level

                return json.dumps(levels)

            elif uri.startswith("voicemeeter://strip/"):
                strip_id = int(uri.split("/")[-1])
                strip_data = {}

                # Common strip parameters
                params = [
                    "mute",
                    "mono",
                    "solo",
                    "gain",
                    "comp",
                    "gate",
                    "limit",
                    "A1",
                    "A2",
                    "A3",
                    "A4",
                    "A5",
                    "B1",
                    "B2",
                    "B3",
                    "label",
                    "device.name",
                ]

                for param in params:
                    param_name = f"Strip[{strip_id}].{param}"
                    if param in ["label", "device.name"]:
                        value = self.vm_api.get_parameter_string(param_name)
                    else:
                        value = self.vm_api.get_parameter_float(param_name)

                    if value is not None:
                        strip_data[param] = value

                return json.dumps(strip_data)

            elif uri.startswith("voicemeeter://bus/"):
                bus_id = int(uri.split("/")[-1])
                bus_data = {}

                # Common bus parameters
                params = [
                    "mute",
                    "mono",
                    "gain",
                    "eq.on",
                    "eq.ab",
                    "sel",
                    "returnreverb",
                    "returndelay",
                    "returnfx1",
                    "returnfx2",
                ]

                for param in params:
                    param_name = f"Bus[{bus_id}].{param}"
                    value = self.vm_api.get_parameter_float(param_name)
                    if value is not None:
                        bus_data[param] = value

                return json.dumps(bus_data)

            return json.dumps({"error": f"Unknown resource: {uri}"})

        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available Voicemeeter tools."""
            return [
                Tool(
                    name="voicemeeter_connect",
                    description="Connect to Voicemeeter Remote API",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                ),
                Tool(
                    name="voicemeeter_disconnect",
                    description="Disconnect from Voicemeeter Remote API",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                ),
                Tool(
                    name="voicemeeter_run",
                    description="Launch Voicemeeter application",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["voicemeeter", "banana", "potato"],
                                "description": "Type of Voicemeeter to launch",
                            }
                        },
                        "required": ["type"],
                    },
                ),
                Tool(
                    name="voicemeeter_get_parameter",
                    description="Get a Voicemeeter parameter value",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "parameter": {
                                "type": "string",
                                "description": "Parameter name (e.g., 'Strip[0].mute', 'Bus[1].gain')",
                            },
                            "type": {
                                "type": "string",
                                "enum": ["float", "string"],
                                "default": "float",
                                "description": "Parameter type",
                            },
                        },
                        "required": ["parameter"],
                    },
                ),
                Tool(
                    name="voicemeeter_set_parameter",
                    description="Set a Voicemeeter parameter value",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "parameter": {
                                "type": "string",
                                "description": "Parameter name (e.g., 'Strip[0].mute', 'Bus[1].gain')",
                            },
                            "value": {
                                "type": ["number", "string"],
                                "description": "Parameter value",
                            },
                            "type": {
                                "type": "string",
                                "enum": ["float", "string"],
                                "default": "float",
                                "description": "Parameter type",
                            },
                        },
                        "required": ["parameter", "value"],
                    },
                ),
                Tool(
                    name="voicemeeter_get_levels",
                    description="Get audio levels for specified channels",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "level_type": {
                                "type": "integer",
                                "description": "Level type (0=input, 1=output pre-fader, 2=output post-fader, 3=output post-mute)",
                                "default": 0,
                            },
                            "channels": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": "Channel indices to get levels for",
                                "default": [0, 1],
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="voicemeeter_load_preset",
                    description="Load a Voicemeeter preset from XML file",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "preset_path": {
                                "type": "string",
                                "description": "Path to the XML preset file",
                            },
                        },
                        "required": ["preset_path"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: Dict[str, Any]
        ) -> List[TextContent]:
            """Handle tool calls."""
            try:
                if name == "voicemeeter_connect":
                    success = self.vm_api.login()
                    if success:
                        vm_type = self.vm_api.voicemeeter_type
                        return [
                            TextContent(
                                type="text",
                                text=f"Successfully connected to {vm_type.name if vm_type else 'Voicemeeter'}",
                            )
                        ]
                    else:
                        return [
                            TextContent(
                                type="text",
                                text="Failed to connect to Voicemeeter. Make sure Voicemeeter is installed and running.",
                            )
                        ]

                elif name == "voicemeeter_disconnect":
                    success = self.vm_api.logout()
                    return [
                        TextContent(
                            type="text",
                            text=(
                                "Disconnected from Voicemeeter"
                                if success
                                else "Failed to disconnect"
                            ),
                        )
                    ]

                elif name == "voicemeeter_run":
                    vm_type_str = arguments["type"]
                    vm_type_map = {
                        "voicemeeter": VoicemeeterType.VOICEMEETER,
                        "banana": VoicemeeterType.VOICEMEETER_BANANA,
                        "potato": VoicemeeterType.VOICEMEETER_POTATO,
                    }

                    vm_type = vm_type_map.get(vm_type_str)
                    if not vm_type:
                        return [
                            TextContent(
                                type="text",
                                text=f"Invalid Voicemeeter type: {vm_type_str}",
                            )
                        ]

                    success = self.vm_api.run_voicemeeter(vm_type)
                    return [
                        TextContent(
                            type="text",
                            text=f"{'Successfully launched' if success else 'Failed to launch'} {vm_type.name}",
                        )
                    ]

                elif name == "voicemeeter_get_parameter":
                    if not self.vm_api.is_connected:
                        if not self.vm_api.login():
                            return [
                                TextContent(
                                    type="text", text="Failed to connect to Voicemeeter"
                                )
                            ]

                    parameter = arguments["parameter"]
                    param_type = arguments.get("type", "float")

                    if param_type == "string":
                        value = self.vm_api.get_parameter_string(parameter)
                    else:
                        value = self.vm_api.get_parameter_float(parameter)

                    if value is not None:
                        return [
                            TextContent(
                                type="text", text=f"Parameter '{parameter}' = {value}"
                            )
                        ]
                    else:
                        return [
                            TextContent(
                                type="text",
                                text=f"Failed to get parameter '{parameter}'",
                            )
                        ]

                elif name == "voicemeeter_set_parameter":
                    if not self.vm_api.is_connected:
                        if not self.vm_api.login():
                            return [
                                TextContent(
                                    type="text", text="Failed to connect to Voicemeeter"
                                )
                            ]

                    parameter = arguments["parameter"]
                    value = arguments["value"]
                    param_type = arguments.get("type", "float")

                    if param_type == "string":
                        success = self.vm_api.set_parameter_string(
                            parameter, str(value)
                        )
                    else:
                        success = self.vm_api.set_parameter_float(
                            parameter, float(value)
                        )

                    return [
                        TextContent(
                            type="text",
                            text=f"{'Successfully set' if success else 'Failed to set'} parameter '{parameter}' to {value}",
                        )
                    ]

                elif name == "voicemeeter_get_levels":
                    if not self.vm_api.is_connected:
                        if not self.vm_api.login():
                            return [
                                TextContent(
                                    type="text", text="Failed to connect to Voicemeeter"
                                )
                            ]

                    level_type = arguments.get("level_type", 0)
                    channels = arguments.get("channels", [0, 1])

                    levels = {}
                    for channel in channels:
                        level = self.vm_api.get_level(level_type, channel)
                        if level is not None:
                            levels[f"channel_{channel}"] = level

                    return [
                        TextContent(
                            type="text",
                            text=f"Audio levels (type {level_type}): {json.dumps(levels, indent=2)}",
                        )
                    ]

                elif name == "voicemeeter_load_preset":
                    preset_path = arguments["preset_path"]

                    if not self.vm_api.is_connected:
                        if not self.vm_api.login():
                            return [
                                TextContent(
                                    type="text", text="Failed to connect to Voicemeeter"
                                )
                            ]

                    # Load XML preset file and apply settings
                    try:
                        import os
                        import defusedxml.ElementTree as ET
                        
                        # Security: Validate file path and existence
                        if not os.path.exists(preset_path):
                            return [
                                TextContent(
                                    type="text",
                                    text=f"Preset file not found: '{preset_path}'",
                                )
                            ]
                        
                        # Security: Ensure file has .xml extension
                        if not preset_path.lower().endswith('.xml'):
                            return [
                                TextContent(
                                    type="text",
                                    text=f"Invalid file type. Only .xml files are supported: '{preset_path}'",
                                )
                            ]
                        
                        # Security: Check file size (prevent DoS attacks)
                        file_size = os.path.getsize(preset_path)
                        if file_size > 10 * 1024 * 1024:  # 10MB limit
                            return [
                                TextContent(
                                    type="text",
                                    text=f"Preset file too large (max 10MB): '{preset_path}'",
                                )
                            ]

                        # Use defusedxml for secure XML parsing
                        tree = ET.parse(preset_path)
                        root = tree.getroot()

                        applied_count = 0
                        failed_count = 0
                        
                        for param in root.findall(".//param"):
                            name = param.get("name")
                            value = param.text

                            if name and value is not None:
                                # Security: Validate parameter name format
                                if not self._is_valid_parameter_name(name):
                                    failed_count += 1
                                    continue
                                    
                                try:
                                    # Try as float first
                                    float_value = float(value)
                                    if self.vm_api.set_parameter_float(
                                        name, float_value
                                    ):
                                        applied_count += 1
                                    else:
                                        failed_count += 1
                                except ValueError:
                                    # Try as string
                                    if self.vm_api.set_parameter_string(name, str(value)[:256]):  # Limit string length
                                        applied_count += 1
                                    else:
                                        failed_count += 1

                        result_text = f"Successfully applied {applied_count} parameters from preset '{preset_path}'"
                        if failed_count > 0:
                            result_text += f" ({failed_count} parameters failed or were invalid)"
                            
                        return [
                            TextContent(
                                type="text",
                                text=result_text,
                            )
                        ]

                    except ET.ParseError as e:
                        return [
                            TextContent(
                                type="text",
                                text=f"Invalid XML format in preset '{preset_path}': {str(e)}",
                            )
                        ]
                    except Exception as e:
                        return [
                            TextContent(
                                type="text",
                                text=f"Failed to load preset '{preset_path}': {str(e)}",
                            )
                        ]

                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]

            except Exception as e:
                return [
                    TextContent(
                        type="text", text=f"Error executing tool '{name}': {str(e)}"
                    )
                ]

    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="voicemeeter-mcp-server",
                    server_version="0.1.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=None,
                        experimental_capabilities=None,
                    ),
                ),
            )


async def main():
    """Main entry point."""
    server = VoicemeeterMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
