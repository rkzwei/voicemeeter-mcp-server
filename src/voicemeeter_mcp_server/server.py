"""MCP Server for Voicemeeter Remote API."""

import asyncio
import json
from typing import Any, Dict, List, Optional, Union, cast

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    EmbeddedResource,
    ImageContent,
    LoggingLevel,
    Resource,
    TextContent,
    Tool,
)
from pydantic import AnyUrl, BaseModel, Field

from .preset_manager import PresetManager, PresetValidationError
from .voicemeeter_api import VoicemeeterAPI, VoicemeeterType


class VoicemeeterMCPServer:
    """MCP Server for Voicemeeter Remote API integration."""

    def __init__(self):
        self.server = Server("voicemeeter-mcp-server")
        self.vm_api = VoicemeeterAPI()
        self.preset_manager = PresetManager()
        # Store handler references for testing
        self._list_resources_handler = None
        self._read_resource_handler = None
        self._list_tools_handler = None
        self._call_tool_handler = None
        # Track background tasks for cleanup
        self._background_tasks: set = set()
        self._shutdown_event = asyncio.Event()
        self._setup_handlers()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self.cleanup()

    def add_background_task(self, task: asyncio.Task):
        """Add a background task to be managed."""
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def cleanup(self):
        """Clean up all resources and background tasks."""
        print("Cleaning up VoicemeeterMCPServer resources...")

        # Signal shutdown to any background tasks
        self._shutdown_event.set()

        # Cancel all background tasks
        if self._background_tasks:
            print(f"Cancelling {len(self._background_tasks)} background tasks...")
            for task in self._background_tasks:
                if not task.done():
                    task.cancel()

            # Wait for tasks to complete cancellation
            if self._background_tasks:
                await asyncio.gather(*self._background_tasks, return_exceptions=True)

        # Clean up Voicemeeter API connection
        if self.vm_api.is_connected:
            print("Disconnecting from Voicemeeter...")
            self.vm_api.logout()

        print("VoicemeeterMCPServer cleanup completed.")

    def _is_valid_parameter_name(self, param_name: str) -> bool:
        """Validate parameter name format for security."""
        import re

        # Allow only valid Voicemeeter parameter patterns
        # Examples: Strip[0].mute, Bus[1].gain, Strip[2].device.name
        pattern = r"^(Strip|Bus)\[\d+\]\.[a-zA-Z][a-zA-Z0-9_.]*$"

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
                    uri=AnyUrl("voicemeeter://status"),
                    name="Voicemeeter Status",
                    description="Current status and connection information",
                    mimeType="application/json",
                ),
                Resource(
                    uri=AnyUrl("voicemeeter://version"),
                    name="Voicemeeter Version",
                    description="Voicemeeter version information",
                    mimeType="application/json",
                ),
                Resource(
                    uri=AnyUrl("voicemeeter://levels"),
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
                                uri=AnyUrl(f"voicemeeter://strip/{i}"),
                                name=f"Strip {i}",
                                description=f"Input strip {i} parameters",
                                mimeType="application/json",
                            )
                        )
                    for i in range(3):
                        resources.append(
                            Resource(
                                uri=AnyUrl(f"voicemeeter://bus/{i}"),
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
                                uri=AnyUrl(f"voicemeeter://strip/{i}"),
                                name=f"Strip {i}",
                                description=f"Input strip {i} parameters",
                                mimeType="application/json",
                            )
                        )
                    for i in range(5):
                        resources.append(
                            Resource(
                                uri=AnyUrl(f"voicemeeter://bus/{i}"),
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
                                uri=AnyUrl(f"voicemeeter://strip/{i}"),
                                name=f"Strip {i}",
                                description=f"Input strip {i} parameters",
                                mimeType="application/json",
                            )
                        )
                    for i in range(8):
                        resources.append(
                            Resource(
                                uri=AnyUrl(f"voicemeeter://bus/{i}"),
                                name=f"Bus {i}",
                                description=f"Output bus {i} parameters",
                                mimeType="application/json",
                            )
                        )

            return resources

        # Store handler reference for testing
        self._list_resources_handler = handle_list_resources

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

        # Store handler reference for testing
        self._read_resource_handler = handle_read_resource

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
                                "description": (
                                    "Level type (0=input, 1=output pre-fader, "
                                    "2=output post-fader, 3=output post-mute)"
                                ),
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
                Tool(
                    name="voicemeeter_validate_preset",
                    description="Validate a preset file against schema",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "preset_path": {
                                "type": "string",
                                "description": "Path to the preset file (XML or JSON)",
                            },
                        },
                        "required": ["preset_path"],
                    },
                ),
                Tool(
                    name="voicemeeter_compare_presets",
                    description="Compare two preset files and show differences",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "preset1_path": {
                                "type": "string",
                                "description": "Path to first preset file",
                            },
                            "preset2_path": {
                                "type": "string",
                                "description": "Path to second preset file",
                            },
                        },
                        "required": ["preset1_path", "preset2_path"],
                    },
                ),
                Tool(
                    name="voicemeeter_backup_preset",
                    description="Create a backup of a preset file",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "preset_path": {
                                "type": "string",
                                "description": "Path to the preset file to backup",
                            },
                        },
                        "required": ["preset_path"],
                    },
                ),
                Tool(
                    name="voicemeeter_list_presets",
                    description="List all available preset files",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "extension": {
                                "type": "string",
                                "description": "Filter by file extension (.xml, .json)",
                                "enum": [".xml", ".json"],
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="voicemeeter_create_template",
                    description="Create a preset template for specific Voicemeeter type",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "template_name": {
                                "type": "string",
                                "description": "Name for the template",
                            },
                            "voicemeeter_type": {
                                "type": "string",
                                "enum": ["basic", "banana", "potato"],
                                "default": "potato",
                                "description": "Type of Voicemeeter",
                            },
                            "save_path": {
                                "type": "string",
                                "description": "Path to save the template (optional)",
                            },
                        },
                        "required": ["template_name"],
                    },
                ),
            ]

        # Store handler reference for testing
        self._list_tools_handler = handle_list_tools

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
                                text=(
                                    "Failed to connect to Voicemeeter. "
                                    "Make sure Voicemeeter is installed and running."
                                ),
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
                            text=(
                                f"{'Successfully set' if success else 'Failed to set'} "
                                f"parameter '{parameter}' to {value}"
                            ),
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
                        if not preset_path.lower().endswith(".xml"):
                            return [
                                TextContent(
                                    type="text",
                                    text=(
                                        f"Invalid file type. Only .xml files are "
                                        f"supported: '{preset_path}'"
                                    ),
                                )
                            ]

                        # Security: Check file size (prevent DoS attacks)
                        file_size = os.path.getsize(preset_path)
                        if file_size > 10 * 1024 * 1024:  # 10MB limit
                            return [
                                TextContent(
                                    type="text",
                                    text=(
                                        f"Preset file too large (max 10MB): "
                                        f"'{preset_path}'"
                                    ),
                                )
                            ]

                        # Use defusedxml for secure XML parsing
                        tree = ET.parse(preset_path)
                        root = tree.getroot()

                        applied_count = 0
                        failed_count = 0

                        if root is not None:
                            params = root.findall(".//param")

                            for param in params:
                                param_name: Optional[str] = param.get("name")
                                param_value = param.text

                                if param_name and param_value is not None:
                                    # Security: Validate parameter name format
                                    if not self._is_valid_parameter_name(param_name):
                                        failed_count += 1
                                        continue

                                    # At this point, param_value is guaranteed to be a string
                                    if not isinstance(param_value, str):
                                        raise ValueError(
                                            f"Parameter value must be a string, got {type(param_value)}"
                                        )

                                    try:
                                        # Try as float first
                                        float_value = float(param_value)
                                        if self.vm_api.set_parameter_float(
                                            param_name, float_value
                                        ):
                                            applied_count += 1
                                        else:
                                            failed_count += 1
                                    except ValueError:
                                        # Try as string
                                        if self.vm_api.set_parameter_string(
                                            param_name, param_value[:256]
                                        ):  # Limit string length
                                            applied_count += 1
                                        else:
                                            failed_count += 1

                        result_text = f"Successfully applied {applied_count} parameters from preset '{preset_path}'"
                        if failed_count > 0:
                            result_text += (
                                f" ({failed_count} parameters failed or were invalid)"
                            )

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

                elif name == "voicemeeter_validate_preset":
                    preset_path = arguments["preset_path"]

                    try:
                        if preset_path.lower().endswith(".xml"):
                            preset = self.preset_manager.load_xml_preset(preset_path)
                        elif preset_path.lower().endswith(".json"):
                            preset = self.preset_manager.load_preset_json(preset_path)
                        else:
                            return [
                                TextContent(
                                    type="text",
                                    text="Unsupported file type. Only .xml and .json files are supported.",
                                )
                            ]

                        return [
                            TextContent(
                                type="text",
                                text=(
                                    f"Preset '{preset.metadata.name}' is valid ✅\n"
                                    f"Checksum: {preset.metadata.checksum}"
                                ),
                            )
                        ]

                    except PresetValidationError as e:
                        return [
                            TextContent(
                                type="text",
                                text=f"Preset validation failed ❌: {str(e)}",
                            )
                        ]
                    except Exception as e:
                        return [
                            TextContent(
                                type="text", text=f"Error validating preset: {str(e)}"
                            )
                        ]

                elif name == "voicemeeter_compare_presets":
                    preset1_path = arguments["preset1_path"]
                    preset2_path = arguments["preset2_path"]

                    try:
                        # Load both presets
                        if preset1_path.lower().endswith(".xml"):
                            preset1 = self.preset_manager.load_xml_preset(preset1_path)
                        else:
                            preset1 = self.preset_manager.load_preset_json(preset1_path)

                        if preset2_path.lower().endswith(".xml"):
                            preset2 = self.preset_manager.load_xml_preset(preset2_path)
                        else:
                            preset2 = self.preset_manager.load_preset_json(preset2_path)

                        # Compare presets
                        comparison = self.preset_manager.compare_presets(
                            preset1, preset2
                        )

                        result = f"Preset Comparison: '{preset1.metadata.name}' vs '{preset2.metadata.name}'\n\n"
                        result += "Summary:\n"
                        result += f"- Total changes: {comparison['summary']['total_changes']}\n"
                        result += f"- Strips modified: {comparison['summary']['strips_modified']}\n"
                        result += f"- Buses modified: {comparison['summary']['buses_modified']}\n"
                        result += f"- Scenarios modified: {comparison['summary']['scenarios_modified']}\n\n"

                        if comparison["summary"]["total_changes"] == 0:
                            result += "✅ Presets are identical"
                        else:
                            result += "Detailed comparison:\n"
                            result += json.dumps(comparison, indent=2)

                        return [TextContent(type="text", text=result)]

                    except Exception as e:
                        return [
                            TextContent(
                                type="text", text=f"Error comparing presets: {str(e)}"
                            )
                        ]

                elif name == "voicemeeter_backup_preset":
                    preset_path = arguments["preset_path"]

                    try:
                        backup_path = self.preset_manager.create_backup(preset_path)
                        return [
                            TextContent(
                                type="text",
                                text=f"Backup created successfully: {backup_path}",
                            )
                        ]
                    except Exception as e:
                        return [
                            TextContent(
                                type="text", text=f"Error creating backup: {str(e)}"
                            )
                        ]

                elif name == "voicemeeter_list_presets":
                    extension = arguments.get("extension")

                    try:
                        presets = self.preset_manager.list_presets(extension)

                        if not presets:
                            return [
                                TextContent(type="text", text="No preset files found.")
                            ]

                        result = f"Found {len(presets)} preset file(s):\n\n"
                        for preset in presets:
                            result += f"📄 {preset['name']}{preset['extension']}\n"
                            result += f"   Path: {preset['path']}\n"
                            result += f"   Size: {preset['size']} bytes\n"
                            result += f"   Modified: {preset['modified']}\n\n"

                        return [TextContent(type="text", text=result)]
                    except Exception as e:
                        return [
                            TextContent(
                                type="text", text=f"Error listing presets: {str(e)}"
                            )
                        ]

                elif name == "voicemeeter_create_template":
                    template_name = arguments["template_name"]
                    voicemeeter_type = arguments.get("voicemeeter_type", "potato")
                    save_path = arguments.get("save_path")

                    try:
                        template = self.preset_manager.create_template(
                            template_name, voicemeeter_type
                        )

                        result = f"Created template '{template_name}' for Voicemeeter {voicemeeter_type.title()}\n"
                        result += f"- {len(template.strips)} strips configured\n"
                        result += f"- {len(template.buses)} buses configured\n"
                        result += f"- {len(template.scenarios)} scenarios included\n"

                        if save_path:
                            if save_path.lower().endswith(".json"):
                                self.preset_manager.save_preset_json(
                                    template, save_path
                                )
                                result += f"\n✅ Template saved to: {save_path}"
                            elif save_path.lower().endswith(".xml"):
                                self.preset_manager.export_preset_xml(
                                    template, save_path
                                )
                                result += f"\n✅ Template exported to: {save_path}"
                            else:
                                result += (
                                    "\n⚠️ Invalid file extension. Use .json or .xml"
                                )
                        else:
                            result += "\n💡 Use save_path parameter to save the template to a file"

                        return [TextContent(type="text", text=result)]
                    except Exception as e:
                        return [
                            TextContent(
                                type="text", text=f"Error creating template: {str(e)}"
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

        # Store handler reference for testing
        self._call_tool_handler = handle_call_tool

    async def list_resources(self) -> List[Resource]:
        """Expose list_resources for testing."""
        return await self._list_resources_handler()

    async def read_resource(self, uri: str) -> str:
        """Expose read_resource for testing."""
        return await self._read_resource_handler(uri)

    async def list_tools(self) -> List[Tool]:
        """Expose list_tools for testing."""
        return await self._list_tools_handler()

    async def call_tool(
        self, name: str, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Expose call_tool for testing."""
        return await self._call_tool_handler(name, arguments)

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
    async with VoicemeeterMCPServer() as server:
        await server.run()


if __name__ == "__main__":
    asyncio.run(main())
