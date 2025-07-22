"""Tests for Voicemeeter API wrapper."""

import ctypes
import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from voicemeeter_mcp_server.voicemeeter_api import VoicemeeterAPI, VoicemeeterType


class TestVoicemeeterAPI:
    """Test cases for VoicemeeterAPI."""

    def setup_method(self):
        """Setup test fixtures."""
        self.api = VoicemeeterAPI()

    def test_init(self):
        """Test API initialization."""
        assert self.api._dll is None
        assert self.api._is_connected is False
        assert self.api._vm_type is None

    @patch("ctypes.CDLL")
    def test_load_dll_success(self, mock_cdll):
        """Test successful DLL loading."""
        mock_dll = Mock()
        mock_cdll.return_value = mock_dll

        result = self.api._load_dll()

        assert result is True
        assert self.api._dll == mock_dll

    @patch("ctypes.CDLL")
    def test_load_dll_failure(self, mock_cdll):
        """Test DLL loading failure."""
        mock_cdll.side_effect = OSError("DLL not found")

        result = self.api._load_dll()

        assert result is False
        assert self.api._dll is None

    @patch.object(VoicemeeterAPI, "_load_dll")
    def test_login_success(self, mock_load_dll):
        """Test successful login."""
        # Setup mock DLL
        mock_dll = Mock()
        mock_login_func = Mock()
        mock_login_func.return_value = 0  # Success
        mock_dll.VBVMR_Login = mock_login_func

        mock_load_dll.return_value = True
        self.api._dll = mock_dll

        # Mock get_voicemeeter_type
        with patch.object(
            self.api, "_get_voicemeeter_type", return_value=VoicemeeterType.VOICEMEETER
        ):
            result = self.api.login()

        assert result is True
        assert self.api._is_connected is True
        assert self.api._vm_type == VoicemeeterType.VOICEMEETER
        mock_login_func.assert_called_once()

    @patch.object(VoicemeeterAPI, "_load_dll")
    def test_login_failure(self, mock_load_dll):
        """Test login failure."""
        mock_load_dll.return_value = False

        result = self.api.login()

        assert result is False
        assert self.api._is_connected is False

    def test_logout_success(self):
        """Test successful logout."""
        # Setup mock DLL
        mock_dll = Mock()
        mock_logout_func = Mock()
        mock_logout_func.return_value = 0  # Success
        mock_dll.VBVMR_Logout = mock_logout_func

        self.api._dll = mock_dll
        self.api._is_connected = True

        result = self.api.logout()

        assert result is True
        assert self.api._is_connected is False
        mock_logout_func.assert_called_once()

    def test_logout_no_dll(self):
        """Test logout when no DLL is loaded."""
        result = self.api.logout()
        assert result is False

    def test_get_parameter_float_success(self):
        """Test successful float parameter retrieval."""
        # Setup mock DLL with proper function signature simulation
        mock_dll = Mock()

        # Create a mock function that properly simulates the DLL behavior
        def mock_get_param_func(param_name, value_ptr):
            # Simulate the DLL writing to the pointer
            # Access the original ctypes object through _obj
            if hasattr(value_ptr, "_obj"):
                value_ptr._obj.value = 0.5
            return 0  # Success

        mock_dll.VBVMR_GetParameterFloat = Mock(side_effect=mock_get_param_func)

        self.api._dll = mock_dll
        self.api._is_connected = True

        result = self.api.get_parameter_float("Strip[0].mute")

        assert result == 0.5
        mock_dll.VBVMR_GetParameterFloat.assert_called_once()

    def test_get_parameter_float_not_connected(self):
        """Test float parameter retrieval when not connected."""
        result = self.api.get_parameter_float("Strip[0].mute")
        assert result is None

    def test_set_parameter_float_success(self):
        """Test successful float parameter setting."""
        # Setup mock DLL
        mock_dll = Mock()
        mock_set_param_func = Mock()
        mock_set_param_func.return_value = 0  # Success
        mock_dll.VBVMR_SetParameterFloat = mock_set_param_func

        self.api._dll = mock_dll
        self.api._is_connected = True

        with patch("ctypes.c_float") as mock_c_float:
            result = self.api.set_parameter_float("Strip[0].mute", 1.0)

            assert result is True
            mock_set_param_func.assert_called_once()

    def test_set_parameter_float_not_connected(self):
        """Test float parameter setting when not connected."""
        result = self.api.set_parameter_float("Strip[0].mute", 1.0)
        assert result is False

    def test_is_connected_property(self):
        """Test is_connected property."""
        assert self.api.is_connected is False

        self.api._is_connected = True
        assert self.api.is_connected is True

    def test_voicemeeter_type_property(self):
        """Test voicemeeter_type property."""
        assert self.api.voicemeeter_type is None

        self.api._vm_type = VoicemeeterType.VOICEMEETER_BANANA
        assert self.api.voicemeeter_type == VoicemeeterType.VOICEMEETER_BANANA

    def test_context_manager(self):
        """Test context manager functionality."""
        with patch.object(
            self.api, "login", return_value=True
        ) as mock_login, patch.object(
            self.api, "logout", return_value=True
        ) as mock_logout:

            with self.api as api:
                assert api == self.api
                mock_login.assert_called_once()

            mock_logout.assert_called_once()

    def test_get_parameter_string_success(self):
        """Test successful string parameter retrieval."""
        self.api._dll = Mock()
        self.api._is_connected = True

        # Create a mock function that simulates writing to the buffer
        def mock_get_string(param_name, buffer_ptr):
            # Simulate writing to the buffer
            buffer_ptr.value = b"Test String"
            return 0

        self.api._dll.VBVMR_GetParameterStringA = Mock(side_effect=mock_get_string)

        with patch("ctypes.create_string_buffer") as mock_buffer:
            mock_buffer_instance = Mock()
            mock_buffer_instance.value = b"Test String"
            mock_buffer.return_value = mock_buffer_instance

            result = self.api.get_parameter_string("Strip[0].label")

            assert result == "Test String"
            self.api._dll.VBVMR_GetParameterStringA.assert_called_once()

    def test_get_parameter_string_not_connected(self):
        """Test string parameter retrieval when not connected."""
        self.api._dll = None

        result = self.api.get_parameter_string("Strip[0].label")

        assert result is None

    def test_get_parameter_string_failure(self):
        """Test failed string parameter retrieval."""
        self.api._dll = Mock()
        self.api._dll.VBVMR_GetParameterStringA = Mock(return_value=-1)

        with patch("ctypes.create_string_buffer"):
            result = self.api.get_parameter_string("Strip[0].label")

            assert result is None

    def test_set_parameter_string_success(self):
        """Test successful string parameter setting."""
        self.api._dll = Mock()
        self.api._is_connected = True
        self.api._dll.VBVMR_SetParameterStringA = Mock(return_value=0)

        result = self.api.set_parameter_string("Strip[0].label", "New Label")

        assert result is True
        self.api._dll.VBVMR_SetParameterStringA.assert_called_once()

    def test_set_parameter_string_not_connected(self):
        """Test string parameter setting when not connected."""
        self.api._dll = None

        result = self.api.set_parameter_string("Strip[0].label", "New Label")

        assert result is False

    def test_set_parameter_string_failure(self):
        """Test failed string parameter setting."""
        self.api._dll = Mock()
        self.api._dll.VBVMR_SetParameterStringA = Mock(return_value=-1)

        result = self.api.set_parameter_string("Strip[0].label", "New Label")

        assert result is False

    def test_get_level_success(self):
        """Test successful level retrieval."""
        self.api._dll = Mock()
        self.api._is_connected = True

        # Create a mock function that simulates writing to the ctypes object
        def mock_get_level(level_type, channel, value_ref):
            # The value_ref is created by ctypes.byref(ctypes.c_float())
            # We need to modify the underlying c_float object
            value_ref._obj.value = -20.5
            return 0

        self.api._dll.VBVMR_GetLevel = Mock(side_effect=mock_get_level)

        result = self.api.get_level(0, 1)

        assert result == -20.5
        self.api._dll.VBVMR_GetLevel.assert_called_once()

    def test_get_level_not_connected(self):
        """Test level retrieval when not connected."""
        self.api._dll = None

        result = self.api.get_level(0, 1)

        assert result is None

    def test_get_level_failure(self):
        """Test failed level retrieval."""
        self.api._dll = Mock()
        self.api._dll.VBVMR_GetLevel = Mock(return_value=-1)

        with patch("ctypes.c_float"):
            result = self.api.get_level(0, 1)

            assert result is None

    def test_is_parameters_dirty_success(self):
        """Test successful parameters dirty check."""
        self.api._dll = Mock()
        self.api._is_connected = True
        self.api._dll.VBVMR_IsParametersDirty = Mock(return_value=1)

        result = self.api.is_parameters_dirty()

        assert result is True
        self.api._dll.VBVMR_IsParametersDirty.assert_called_once()

    def test_is_parameters_dirty_not_connected(self):
        """Test parameters dirty check when not connected."""
        self.api._dll = None

        result = self.api.is_parameters_dirty()

        assert result is False

    def test_is_parameters_dirty_clean(self):
        """Test parameters dirty check when clean."""
        self.api._dll = Mock()
        self.api._dll.VBVMR_IsParametersDirty = Mock(return_value=0)

        result = self.api.is_parameters_dirty()

        assert result is False

    def test_get_version_success(self):
        """Test successful version retrieval."""
        self.api._dll = Mock()

        # Create a mock function that simulates writing to the ctypes object
        def mock_get_version(version_ref):
            # The version_ref is created by ctypes.byref(ctypes.c_long())
            # We need to modify the underlying c_long object
            version_ref._obj.value = 0x02010008  # Version 2.1.0.8
            return 0

        self.api._dll.VBVMR_GetVoicemeeterVersion = Mock(side_effect=mock_get_version)

        result = self.api.get_version()

        assert result == "2.1.0.8"
        self.api._dll.VBVMR_GetVoicemeeterVersion.assert_called_once()

    def test_get_version_not_connected(self):
        """Test version retrieval when not connected."""
        self.api._dll = None

        result = self.api.get_version()

        assert result is None

    def test_get_version_failure(self):
        """Test failed version retrieval."""
        self.api._dll = Mock()
        self.api._dll.VBVMR_GetVoicemeeterVersion = Mock(return_value=-1)

        with patch("ctypes.c_long"):
            result = self.api.get_version()

            assert result is None

    def test_run_voicemeeter_success(self):
        """Test successful Voicemeeter launch."""
        self.api._dll = Mock()
        self.api._dll.VBVMR_RunVoicemeeter = Mock(return_value=0)

        result = self.api.run_voicemeeter(VoicemeeterType.VOICEMEETER)

        assert result is True
        self.api._dll.VBVMR_RunVoicemeeter.assert_called_once_with(1)

    def test_run_voicemeeter_not_connected(self):
        """Test Voicemeeter launch when not connected."""
        self.api._dll = None

        result = self.api.run_voicemeeter(VoicemeeterType.VOICEMEETER)

        assert result is False

    def test_run_voicemeeter_failure(self):
        """Test failed Voicemeeter launch."""
        self.api._dll = Mock()
        self.api._dll.VBVMR_RunVoicemeeter = Mock(return_value=-1)

        result = self.api.run_voicemeeter(VoicemeeterType.VOICEMEETER_BANANA)

        assert result is False
        self.api._dll.VBVMR_RunVoicemeeter.assert_called_once_with(2)

    def test_get_voicemeeter_type_success(self):
        """Test successful Voicemeeter type detection."""
        self.api._dll = Mock()

        # Create a mock function that simulates writing to the ctypes object
        def mock_get_type(type_ref):
            # The type_ref is created by ctypes.byref(ctypes.c_long())
            # We need to modify the underlying c_long object
            type_ref._obj.value = 2  # Banana
            return 0

        self.api._dll.VBVMR_GetVoicemeeterType = Mock(side_effect=mock_get_type)

        result = self.api._get_voicemeeter_type()

        assert result == VoicemeeterType.VOICEMEETER_BANANA
        self.api._dll.VBVMR_GetVoicemeeterType.assert_called_once()

    def test_get_voicemeeter_type_not_connected(self):
        """Test Voicemeeter type detection when not connected."""
        self.api._dll = None

        result = self.api._get_voicemeeter_type()

        assert result is None

    def test_get_voicemeeter_type_failure(self):
        """Test failed Voicemeeter type detection."""
        self.api._dll = Mock()
        self.api._dll.VBVMR_GetVoicemeeterType = Mock(return_value=-1)

        with patch("ctypes.c_long"):
            result = self.api._get_voicemeeter_type()

            assert result is None

    def test_get_voicemeeter_type_unknown(self):
        """Test Voicemeeter type detection with unknown type."""
        self.api._dll = Mock()
        self.api._dll.VBVMR_GetVoicemeeterType = Mock(return_value=0)

        # Mock the type pointer with unknown value
        with patch("ctypes.c_long") as mock_long:
            mock_long_instance = Mock()
            mock_long_instance.value = 99  # Unknown type
            mock_long.return_value = mock_long_instance

            result = self.api._get_voicemeeter_type()

            assert result is None


class TestVoicemeeterType:
    """Test cases for VoicemeeterType enum."""

    def test_enum_values(self):
        """Test enum values are correct."""
        assert VoicemeeterType.VOICEMEETER.value == 1
        assert VoicemeeterType.VOICEMEETER_BANANA.value == 2
        assert VoicemeeterType.VOICEMEETER_POTATO.value == 3

    def test_enum_names(self):
        """Test enum names."""
        assert VoicemeeterType.VOICEMEETER.name == "VOICEMEETER"
        assert VoicemeeterType.VOICEMEETER_BANANA.name == "VOICEMEETER_BANANA"
        assert VoicemeeterType.VOICEMEETER_POTATO.name == "VOICEMEETER_POTATO"


class TestVoicemeeterAPIEdgeCases:
    """Test edge cases and error paths for VoicemeeterAPI."""

    def test_load_dll_exception_handling(self):
        """Test exception handling in _load_dll."""
        api = VoicemeeterAPI()

        # Mock platform.machine to raise an exception
        with patch(
            "voicemeeter_mcp_server.voicemeeter_api.platform.machine",
            side_effect=Exception("Platform error"),
        ):
            result = api._load_dll()
            assert result is False

    def test_load_dll_32bit_system(self):
        """Test DLL loading on 32-bit system."""
        api = VoicemeeterAPI()

        with patch(
            "voicemeeter_mcp_server.voicemeeter_api.platform.machine",
            return_value="i386",
        ):
            with patch(
                "voicemeeter_mcp_server.voicemeeter_api.platform.architecture",
                return_value=("32bit", ""),
            ):
                with patch(
                    "voicemeeter_mcp_server.voicemeeter_api.ctypes.CDLL",
                    side_effect=OSError("DLL not found"),
                ):
                    result = api._load_dll()
                    assert result is False

    def test_load_dll_absolute_path_not_exists(self):
        """Test DLL loading with absolute path that doesn't exist."""
        api = VoicemeeterAPI()

        with patch(
            "voicemeeter_mcp_server.voicemeeter_api.os.path.isabs", return_value=True
        ):
            with patch(
                "voicemeeter_mcp_server.voicemeeter_api.os.path.exists",
                return_value=False,
            ):
                result = api._load_dll()
                assert result is False

    def test_login_exception_in_dll_call(self):
        """Test login with exception in DLL function call."""
        api = VoicemeeterAPI()

        # Mock _load_dll to return True so we get to the exception part
        with patch.object(api, "_load_dll", return_value=True):
            # Mock DLL
            mock_dll = Mock()
            api._dll = mock_dll

            # Mock login function to raise exception
            mock_dll.VBVMR_Login.side_effect = Exception("DLL call failed")

            result = api.login()
            assert result is False
            assert not api._is_connected

    def test_logout_exception_in_dll_call(self):
        """Test logout with exception in DLL function call."""
        api = VoicemeeterAPI()

        # Mock DLL
        mock_dll = Mock()
        api._dll = mock_dll
        api._is_connected = True

        # Mock logout function to raise exception
        mock_dll.VBVMR_Logout.side_effect = Exception("DLL call failed")

        result = api.logout()
        assert result is False
        # In the actual implementation, _is_connected is set to False BEFORE the DLL call
        # So even if the DLL call fails, _is_connected will be False
        assert not api._is_connected

    def test_get_voicemeeter_type_exception(self):
        """Test _get_voicemeeter_type with exception."""
        api = VoicemeeterAPI()

        # Mock DLL
        mock_dll = Mock()
        api._dll = mock_dll

        # Mock function to raise exception
        mock_dll.VBVMR_GetVoicemeeterType.side_effect = Exception("DLL call failed")

        result = api._get_voicemeeter_type()
        assert result is None

    def test_get_parameter_float_exception(self):
        """Test get_parameter_float with exception."""
        api = VoicemeeterAPI()

        # Mock DLL and connection
        mock_dll = Mock()
        api._dll = mock_dll
        api._is_connected = True

        # Mock function to raise exception
        mock_dll.VBVMR_GetParameterFloat.side_effect = Exception("DLL call failed")

        result = api.get_parameter_float("Strip[0].mute")
        assert result is None

    def test_set_parameter_float_exception(self):
        """Test set_parameter_float with exception."""
        api = VoicemeeterAPI()

        # Mock DLL and connection
        mock_dll = Mock()
        api._dll = mock_dll
        api._is_connected = True

        # Mock function to raise exception
        mock_dll.VBVMR_SetParameterFloat.side_effect = Exception("DLL call failed")

        result = api.set_parameter_float("Strip[0].mute", 1.0)
        assert result is False

    def test_get_parameter_string_exception(self):
        """Test get_parameter_string with exception."""
        api = VoicemeeterAPI()

        # Mock DLL and connection
        mock_dll = Mock()
        api._dll = mock_dll
        api._is_connected = True

        # Mock function to raise exception
        mock_dll.VBVMR_GetParameterStringA.side_effect = Exception("DLL call failed")

        result = api.get_parameter_string("Strip[0].label")
        assert result is None

    def test_set_parameter_string_exception(self):
        """Test set_parameter_string with exception."""
        api = VoicemeeterAPI()

        # Mock DLL and connection
        mock_dll = Mock()
        api._dll = mock_dll
        api._is_connected = True

        # Mock function to raise exception
        mock_dll.VBVMR_SetParameterStringA.side_effect = Exception("DLL call failed")

        result = api.set_parameter_string("Strip[0].label", "Test")
        assert result is False

    def test_get_level_exception(self):
        """Test get_level with exception."""
        api = VoicemeeterAPI()

        # Mock DLL and connection
        mock_dll = Mock()
        api._dll = mock_dll
        api._is_connected = True

        # Mock function to raise exception
        mock_dll.VBVMR_GetLevel.side_effect = Exception("DLL call failed")

        result = api.get_level(0, 1)
        assert result is None

    def test_is_parameters_dirty_exception(self):
        """Test is_parameters_dirty with exception."""
        api = VoicemeeterAPI()

        # Mock DLL and connection
        mock_dll = Mock()
        api._dll = mock_dll
        api._is_connected = True

        # Mock function to raise exception
        mock_dll.VBVMR_IsParametersDirty.side_effect = Exception("DLL call failed")

        result = api.is_parameters_dirty()
        assert result is False

    def test_get_version_exception(self):
        """Test get_version with exception."""
        api = VoicemeeterAPI()

        # Mock DLL
        mock_dll = Mock()
        api._dll = mock_dll

        # Mock function to raise exception
        mock_dll.VBVMR_GetVoicemeeterVersion.side_effect = Exception("DLL call failed")

        result = api.get_version()
        assert result is None

    def test_run_voicemeeter_exception(self):
        """Test run_voicemeeter with exception."""
        api = VoicemeeterAPI()

        # Mock DLL
        mock_dll = Mock()
        api._dll = mock_dll

        # Mock function to raise exception
        mock_dll.VBVMR_RunVoicemeeter.side_effect = Exception("DLL call failed")

        result = api.run_voicemeeter(VoicemeeterType.VOICEMEETER)
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__])
