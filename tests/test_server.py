"""Tests for MCP Server implementation."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from mcp.types import Resource, TextContent, Tool

from voicemeeter_mcp_server.server import VoicemeeterMCPServer
from voicemeeter_mcp_server.voicemeeter_api import VoicemeeterType


class TestVoicemeeterMCPServer:
    """Test cases for VoicemeeterMCPServer."""

    def setup_method(self):
        """Setup test fixtures."""
        self.server = VoicemeeterMCPServer()

    def test_init(self):
        """Test server initialization."""
        assert self.server.server is not None
        assert self.server.vm_api is not None

    def test_is_valid_parameter_name_valid(self):
        """Test valid parameter name validation."""
        valid_names = [
            "Strip[0].mute",
            "Bus[1].gain",
            "Strip[2].device.name",
            "Bus[0].eq.on",
            "Strip[7].A1",
        ]

        for name in valid_names:
            assert self.server._is_valid_parameter_name(
                name
            ), f"Should be valid: {name}"

    def test_is_valid_parameter_name_invalid(self):
        """Test invalid parameter name validation."""
        invalid_names = [
            "invalid",
            "Strip.mute",  # Missing index
            "Strip[].mute",  # Empty index
            "Strip[0]",  # Missing property
            "Strip[0].mute; DROP TABLE",  # SQL injection attempt
            "Strip[0]." + "x" * 100,  # Too long
            "Strip[-1].mute",  # Negative index
        ]

        for name in invalid_names:
            assert not self.server._is_valid_parameter_name(
                name
            ), f"Should be invalid: {name}"

    @pytest.mark.asyncio
    async def test_list_resources_disconnected(self):
        """Test listing resources when disconnected."""
        # Mock the VoicemeeterAPI to be disconnected
        mock_api = Mock()
        mock_api.is_connected = False
        self.server.vm_api = mock_api

        resources = await self.server.list_resources()

        # Should have basic resources
        assert len(resources) >= 3
        resource_uris = [str(r.uri) for r in resources]
        assert "voicemeeter://status" in resource_uris
        assert "voicemeeter://version" in resource_uris
        assert "voicemeeter://levels" in resource_uris

    @pytest.mark.asyncio
    async def test_list_resources_connected_voicemeeter(self):
        """Test listing resources when connected to Voicemeeter Standard."""
        # Mock the VoicemeeterAPI to be connected with Standard type
        mock_api = Mock()
        mock_api.is_connected = True
        mock_api.voicemeeter_type = VoicemeeterType.VOICEMEETER
        self.server.vm_api = mock_api

        resources = await self.server.list_resources()

        # Should have basic + dynamic resources
        resource_uris = [str(r.uri) for r in resources]
        assert "voicemeeter://status" in resource_uris
        assert "voicemeeter://strip/0" in resource_uris
        assert "voicemeeter://strip/2" in resource_uris  # 3 strips total
        assert "voicemeeter://bus/0" in resource_uris
        assert "voicemeeter://bus/2" in resource_uris  # 3 buses total

    @pytest.mark.asyncio
    async def test_list_resources_connected_banana(self):
        """Test listing resources when connected to Voicemeeter Banana."""
        # Mock the VoicemeeterAPI to be connected with Banana type
        mock_api = Mock()
        mock_api.is_connected = True
        mock_api.voicemeeter_type = VoicemeeterType.VOICEMEETER_BANANA
        self.server.vm_api = mock_api

        resources = await self.server.list_resources()

        # Should have basic + dynamic resources for Banana
        resource_uris = [str(r.uri) for r in resources]
        assert "voicemeeter://strip/4" in resource_uris  # 5 strips total
        assert "voicemeeter://bus/4" in resource_uris  # 5 buses total

    @pytest.mark.asyncio
    async def test_list_resources_connected_potato(self):
        """Test listing resources when connected to Voicemeeter Potato."""
        # Mock the VoicemeeterAPI to be connected with Potato type
        mock_api = Mock()
        mock_api.is_connected = True
        mock_api.voicemeeter_type = VoicemeeterType.VOICEMEETER_POTATO
        self.server.vm_api = mock_api

        resources = await self.server.list_resources()

        # Should have basic + dynamic resources for Potato
        resource_uris = [str(r.uri) for r in resources]
        assert "voicemeeter://strip/7" in resource_uris  # 8 strips total
        assert "voicemeeter://bus/7" in resource_uris  # 8 buses total

    @pytest.mark.asyncio
    async def test_read_resource_status(self):
        """Test reading status resource."""
        # Mock the VoicemeeterAPI
        mock_api = Mock()
        mock_api.is_connected = True
        mock_api.voicemeeter_type = VoicemeeterType.VOICEMEETER
        mock_api.is_parameters_dirty.return_value = False
        self.server.vm_api = mock_api

        result = await self.server.read_resource("voicemeeter://status")

        data = json.loads(result)
        assert data["connected"] is True
        assert data["type"] == "VOICEMEETER"
        assert "parameters_dirty" in data

    @pytest.mark.asyncio
    async def test_read_resource_version(self):
        """Test reading version resource."""
        # Mock the VoicemeeterAPI
        mock_api = Mock()
        mock_api.is_connected = True
        mock_api.get_version.return_value = "2.1.0.8"
        self.server.vm_api = mock_api

        result = await self.server.read_resource("voicemeeter://version")

        data = json.loads(result)
        assert data["version"] == "2.1.0.8"
        assert data["api_version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_read_resource_levels(self):
        """Test reading levels resource."""
        # Mock the VoicemeeterAPI
        mock_api = Mock()
        mock_api.is_connected = True

        def mock_get_level(level_type, channel):
            if level_type == 0 and channel < 2:  # Input levels
                return -20.5 + channel
            elif level_type == 3 and channel < 2:  # Output levels
                return -15.0 + channel
            return None

        mock_api.get_level.side_effect = mock_get_level
        self.server.vm_api = mock_api

        result = await self.server.read_resource("voicemeeter://levels")

        data = json.loads(result)
        assert "input_0" in data
        assert "input_1" in data
        assert "output_0" in data
        assert "output_1" in data
        assert data["input_0"] == -20.5
        assert data["output_0"] == -15.0

    @pytest.mark.asyncio
    async def test_read_resource_strip(self):
        """Test reading strip resource."""
        # Mock the VoicemeeterAPI
        mock_api = Mock()
        mock_api.is_connected = True

        def mock_get_parameter_float(param):
            if "mute" in param:
                return 0.0
            elif "gain" in param:
                return -6.0
            return None

        def mock_get_parameter_string(param):
            if "label" in param:
                return "Test Strip"
            elif "device.name" in param:
                return "Test Device"
            return None

        mock_api.get_parameter_float.side_effect = mock_get_parameter_float
        mock_api.get_parameter_string.side_effect = mock_get_parameter_string
        self.server.vm_api = mock_api

        result = await self.server.read_resource("voicemeeter://strip/0")

        data = json.loads(result)
        assert data["mute"] == 0.0
        assert data["gain"] == -6.0
        assert data["label"] == "Test Strip"
        assert data["device.name"] == "Test Device"

    @pytest.mark.asyncio
    async def test_read_resource_bus(self):
        """Test reading bus resource."""
        # Mock the VoicemeeterAPI
        mock_api = Mock()
        mock_api.is_connected = True

        def mock_get_parameter_float(param):
            if "mute" in param:
                return 1.0
            elif "gain" in param:
                return -3.0
            elif "eq.on" in param:
                return 1.0
            return None

        mock_api.get_parameter_float.side_effect = mock_get_parameter_float
        self.server.vm_api = mock_api

        result = await self.server.read_resource("voicemeeter://bus/1")

        data = json.loads(result)
        assert data["mute"] == 1.0
        assert data["gain"] == -3.0
        assert data["eq.on"] == 1.0

    @pytest.mark.asyncio
    async def test_read_resource_unknown(self):
        """Test reading unknown resource."""
        # Mock the VoicemeeterAPI
        mock_api = Mock()
        mock_api.is_connected = True
        self.server.vm_api = mock_api

        result = await self.server.read_resource("voicemeeter://unknown")

        data = json.loads(result)
        assert "error" in data
        assert "Unknown resource" in data["error"]

    @pytest.mark.asyncio
    async def test_read_resource_auto_connect(self):
        """Test auto-connect when reading resource while disconnected."""
        # Mock the VoicemeeterAPI
        mock_api = Mock()
        mock_api.is_connected = False
        mock_api.login.return_value = True
        mock_api.voicemeeter_type = VoicemeeterType.VOICEMEETER
        mock_api.is_parameters_dirty.return_value = False
        self.server.vm_api = mock_api

        result = await self.server.read_resource("voicemeeter://status")

        # Should not return error since login succeeded
        data = json.loads(result)
        assert "error" not in data
        mock_api.login.assert_called_once()

    @pytest.mark.asyncio
    async def test_read_resource_auto_connect_fail(self):
        """Test auto-connect failure when reading resource while disconnected."""
        # Mock the VoicemeeterAPI
        mock_api = Mock()
        mock_api.is_connected = False
        mock_api.login.return_value = False
        self.server.vm_api = mock_api

        result = await self.server.read_resource("voicemeeter://status")

        data = json.loads(result)
        assert "error" in data
        assert "Failed to connect" in data["error"]

    @pytest.mark.asyncio
    async def test_list_tools(self):
        """Test listing available tools."""
        tools = await self.server.list_tools()

        # Should have all expected tools
        tool_names = [t.name for t in tools]
        expected_tools = [
            "voicemeeter_connect",
            "voicemeeter_disconnect",
            "voicemeeter_run",
            "voicemeeter_get_parameter",
            "voicemeeter_set_parameter",
            "voicemeeter_get_levels",
            "voicemeeter_load_preset",
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    @pytest.mark.asyncio
    async def test_call_tool_connect_success(self):
        """Test successful connection tool call."""
        # Mock the VoicemeeterAPI
        mock_api = Mock()
        mock_api.login.return_value = True
        mock_api.voicemeeter_type = VoicemeeterType.VOICEMEETER
        self.server.vm_api = mock_api

        result = await self.server.call_tool("voicemeeter_connect", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Successfully connected" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_connect_failure(self):
        """Test failed connection tool call."""
        # Mock the VoicemeeterAPI
        mock_api = Mock()
        mock_api.login.return_value = False
        self.server.vm_api = mock_api

        result = await self.server.call_tool("voicemeeter_connect", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Failed to connect" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_disconnect(self):
        """Test disconnect tool call."""
        # Mock the VoicemeeterAPI
        mock_api = Mock()
        mock_api.logout.return_value = True
        self.server.vm_api = mock_api

        result = await self.server.call_tool("voicemeeter_disconnect", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Disconnected from Voicemeeter" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_run_voicemeeter(self):
        """Test run Voicemeeter tool call."""
        # Mock the VoicemeeterAPI
        mock_api = Mock()
        mock_api.run_voicemeeter.return_value = True
        self.server.vm_api = mock_api

        result = await self.server.call_tool("voicemeeter_run", {"type": "voicemeeter"})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Successfully launched" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_run_invalid_type(self):
        """Test run Voicemeeter with invalid type."""
        result = await self.server.call_tool("voicemeeter_run", {"type": "invalid"})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Invalid Voicemeeter type" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_get_parameter_float(self):
        """Test get parameter tool call for float."""
        # Mock the VoicemeeterAPI
        mock_api = Mock()
        mock_api.is_connected = True
        mock_api.get_parameter_float.return_value = 0.5
        self.server.vm_api = mock_api

        result = await self.server.call_tool(
            "voicemeeter_get_parameter", {"parameter": "Strip[0].mute", "type": "float"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Strip[0].mute" in result[0].text
        assert "0.5" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_get_parameter_string(self):
        """Test get parameter tool call for string."""
        # Mock the VoicemeeterAPI
        mock_api = Mock()
        mock_api.is_connected = True
        mock_api.get_parameter_string.return_value = "Test Label"
        self.server.vm_api = mock_api

        result = await self.server.call_tool(
            "voicemeeter_get_parameter",
            {"parameter": "Strip[0].label", "type": "string"},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Strip[0].label" in result[0].text
        assert "Test Label" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_get_parameter_not_connected(self):
        """Test get parameter when not connected."""
        # Mock the VoicemeeterAPI
        mock_api = Mock()
        mock_api.is_connected = False
        mock_api.login.return_value = True
        mock_api.get_parameter_float.return_value = 1.0
        self.server.vm_api = mock_api

        result = await self.server.call_tool(
            "voicemeeter_get_parameter", {"parameter": "Strip[0].mute"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "1.0" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_get_parameter_connect_fail(self):
        """Test get parameter when connection fails."""
        # Mock the VoicemeeterAPI
        mock_api = Mock()
        mock_api.is_connected = False
        mock_api.login.return_value = False
        self.server.vm_api = mock_api

        result = await self.server.call_tool(
            "voicemeeter_get_parameter", {"parameter": "Strip[0].mute"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Failed to connect" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_get_parameter_none(self):
        """Test get parameter returning None."""
        # Mock the VoicemeeterAPI
        mock_api = Mock()
        mock_api.is_connected = True
        mock_api.get_parameter_float.return_value = None
        self.server.vm_api = mock_api

        result = await self.server.call_tool(
            "voicemeeter_get_parameter", {"parameter": "Strip[0].invalid"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Failed to get parameter" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_set_parameter_float(self):
        """Test set parameter tool call for float."""
        # Mock the VoicemeeterAPI
        mock_api = Mock()
        mock_api.is_connected = True
        mock_api.set_parameter_float.return_value = True
        self.server.vm_api = mock_api

        result = await self.server.call_tool(
            "voicemeeter_set_parameter",
            {"parameter": "Strip[0].mute", "value": 1.0, "type": "float"},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Successfully set" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_set_parameter_string(self):
        """Test set parameter tool call for string."""
        # Mock the VoicemeeterAPI
        mock_api = Mock()
        mock_api.is_connected = True
        mock_api.set_parameter_string.return_value = True
        self.server.vm_api = mock_api

        result = await self.server.call_tool(
            "voicemeeter_set_parameter",
            {"parameter": "Strip[0].label", "value": "New Label", "type": "string"},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Successfully set" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_get_levels(self):
        """Test get levels tool call."""
        # Mock the VoicemeeterAPI
        mock_api = Mock()
        mock_api.is_connected = True

        def mock_get_level(level_type, channel):
            return -10.0 - channel

        mock_api.get_level.side_effect = mock_get_level
        self.server.vm_api = mock_api

        result = await self.server.call_tool(
            "voicemeeter_get_levels", {"level_type": 0, "channels": [0, 1]}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Audio levels" in result[0].text
        assert "channel_0" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_load_preset_success(self):
        """Test successful preset loading."""
        # Mock the VoicemeeterAPI
        mock_api = Mock()
        mock_api.is_connected = True
        mock_api.set_parameter_float.return_value = True
        self.server.vm_api = mock_api

        with patch("os.path.exists", return_value=True), patch(
            "os.path.getsize", return_value=1024
        ), patch("defusedxml.ElementTree.parse") as mock_parse:

            # Mock XML parsing
            mock_root = Mock()
            mock_param1 = Mock()
            mock_param1.get.return_value = "Strip[0].mute"
            mock_param1.text = "1.0"
            mock_param2 = Mock()
            mock_param2.get.return_value = "Strip[0].gain"
            mock_param2.text = "-6.0"
            mock_root.findall.return_value = [mock_param1, mock_param2]

            mock_tree = Mock()
            mock_tree.getroot.return_value = mock_root
            mock_parse.return_value = mock_tree

            result = await self.server.call_tool(
                "voicemeeter_load_preset", {"preset_path": "/path/to/preset.xml"}
            )

            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert "Successfully applied 2 parameters" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_load_preset_file_not_found(self):
        """Test preset loading with file not found."""
        # Mock the VoicemeeterAPI
        mock_api = Mock()
        mock_api.is_connected = True
        self.server.vm_api = mock_api

        with patch("os.path.exists", return_value=False):
            result = await self.server.call_tool(
                "voicemeeter_load_preset", {"preset_path": "/nonexistent/preset.xml"}
            )

            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert "Preset file not found" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_load_preset_invalid_extension(self):
        """Test preset loading with invalid file extension."""
        # Mock the VoicemeeterAPI
        mock_api = Mock()
        mock_api.is_connected = True
        self.server.vm_api = mock_api

        with patch("os.path.exists", return_value=True):
            result = await self.server.call_tool(
                "voicemeeter_load_preset", {"preset_path": "/path/to/preset.txt"}
            )

            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert "Invalid file type" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_load_preset_file_too_large(self):
        """Test preset loading with file too large."""
        # Mock the VoicemeeterAPI
        mock_api = Mock()
        mock_api.is_connected = True
        self.server.vm_api = mock_api

        with patch("os.path.exists", return_value=True), patch(
            "os.path.getsize", return_value=20 * 1024 * 1024
        ):  # 20MB

            result = await self.server.call_tool(
                "voicemeeter_load_preset", {"preset_path": "/path/to/preset.xml"}
            )

            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert "Preset file too large" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_load_preset_xml_parse_error(self):
        """Test preset loading with XML parse error."""
        # Mock the VoicemeeterAPI
        mock_api = Mock()
        mock_api.is_connected = True
        self.server.vm_api = mock_api

        with patch("os.path.exists", return_value=True), patch(
            "os.path.getsize", return_value=1024
        ), patch("defusedxml.ElementTree.parse", side_effect=Exception("Parse error")):

            result = await self.server.call_tool(
                "voicemeeter_load_preset", {"preset_path": "/path/to/preset.xml"}
            )

            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert "Failed to load preset" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_load_preset_invalid_parameter(self):
        """Test preset loading with invalid parameter names."""
        # Mock the VoicemeeterAPI
        mock_api = Mock()
        mock_api.is_connected = True
        self.server.vm_api = mock_api

        with patch("os.path.exists", return_value=True), patch(
            "os.path.getsize", return_value=1024
        ), patch("defusedxml.ElementTree.parse") as mock_parse:

            # Mock XML parsing with invalid parameter
            mock_root = Mock()
            mock_param = Mock()
            mock_param.get.return_value = "invalid_param"  # Invalid parameter name
            mock_param.text = "1.0"
            mock_root.findall.return_value = [mock_param]

            mock_tree = Mock()
            mock_tree.getroot.return_value = mock_root
            mock_parse.return_value = mock_tree

            result = await self.server.call_tool(
                "voicemeeter_load_preset", {"preset_path": "/path/to/preset.xml"}
            )

            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert "Successfully applied 0 parameters" in result[0].text
            assert "1 parameters failed" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_unknown(self):
        """Test calling unknown tool."""
        result = await self.server.call_tool("unknown_tool", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Unknown tool" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_exception(self):
        """Test tool call with exception."""
        # Mock the VoicemeeterAPI to raise an exception
        mock_api = Mock()
        mock_api.login.side_effect = Exception("Test error")
        self.server.vm_api = mock_api

        result = await self.server.call_tool("voicemeeter_connect", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Error executing tool" in result[0].text
        assert "Test error" in result[0].text

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test async context manager functionality."""
        server = VoicemeeterMCPServer()

        async with server as ctx_server:
            assert ctx_server is server

        # Cleanup should have been called

    @pytest.mark.asyncio
    async def test_cleanup_with_background_tasks(self):
        """Test cleanup with background tasks."""
        server = VoicemeeterMCPServer()

        # Create a real background task that we can cancel
        async def dummy_task():
            try:
                await asyncio.sleep(10)  # Long sleep to ensure it gets cancelled
            except asyncio.CancelledError:
                raise

        task = asyncio.create_task(dummy_task())
        server._background_tasks.add(task)

        # Mock the vm_api to be connected
        mock_api = Mock()
        mock_api.is_connected = True
        mock_api.logout = Mock()
        server.vm_api = mock_api

        with patch("builtins.print") as mock_print:
            await server.cleanup()

            # Verify cleanup was called
            assert task.cancelled()
            mock_api.logout.assert_called_once()
            mock_print.assert_any_call("Cleaning up VoicemeeterMCPServer resources...")

    @pytest.mark.asyncio
    async def test_add_background_task(self):
        """Test adding background task functionality."""
        server = VoicemeeterMCPServer()

        # Create a real task for this test
        async def dummy_task():
            await asyncio.sleep(0.1)

        task = asyncio.create_task(dummy_task())
        server.add_background_task(task)

        assert task in server._background_tasks

        # Wait for task to complete and verify it's removed
        await task
        assert task not in server._background_tasks

    @pytest.mark.asyncio
    async def test_main_function(self):
        """Test the main function."""
        from voicemeeter_mcp_server.server import main

        with patch(
            "voicemeeter_mcp_server.server.VoicemeeterMCPServer"
        ) as mock_server_class:
            mock_server = Mock()
            mock_server.__aenter__ = AsyncMock(return_value=mock_server)
            mock_server.__aexit__ = AsyncMock(return_value=None)
            mock_server.run = AsyncMock()
            mock_server_class.return_value = mock_server

            await main()

            # Verify server was created and run was called
            mock_server_class.assert_called_once()
            mock_server.run.assert_called_once()
