"""Tests for Voicemeeter API wrapper."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import ctypes

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
    
    @patch('ctypes.CDLL')
    def test_load_dll_success(self, mock_cdll):
        """Test successful DLL loading."""
        mock_dll = Mock()
        mock_cdll.return_value = mock_dll
        
        result = self.api._load_dll()
        
        assert result is True
        assert self.api._dll == mock_dll
    
    @patch('ctypes.CDLL')
    def test_load_dll_failure(self, mock_cdll):
        """Test DLL loading failure."""
        mock_cdll.side_effect = OSError("DLL not found")
        
        result = self.api._load_dll()
        
        assert result is False
        assert self.api._dll is None
    
    @patch.object(VoicemeeterAPI, '_load_dll')
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
        with patch.object(self.api, '_get_voicemeeter_type', return_value=VoicemeeterType.VOICEMEETER):
            result = self.api.login()
        
        assert result is True
        assert self.api._is_connected is True
        assert self.api._vm_type == VoicemeeterType.VOICEMEETER
        mock_login_func.assert_called_once()
    
    @patch.object(VoicemeeterAPI, '_load_dll')
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
        # Setup mock DLL
        mock_dll = Mock()
        mock_get_param_func = Mock()
        mock_get_param_func.return_value = 0  # Success
        mock_dll.VBVMR_GetParameterFloat = mock_get_param_func
        
        self.api._dll = mock_dll
        self.api._is_connected = True
        
        # Mock ctypes behavior
        with patch('ctypes.c_float') as mock_c_float, \
             patch('ctypes.byref') as mock_byref:
            
            mock_value = Mock()
            mock_value.value = 0.5
            mock_c_float.return_value = mock_value
            
            result = self.api.get_parameter_float("Strip[0].mute")
            
            assert result == 0.5
            mock_get_param_func.assert_called_once()
    
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
        
        with patch('ctypes.c_float') as mock_c_float:
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
        with patch.object(self.api, 'login', return_value=True) as mock_login, \
             patch.object(self.api, 'logout', return_value=True) as mock_logout:
            
            with self.api as api:
                assert api == self.api
                mock_login.assert_called_once()
            
            mock_logout.assert_called_once()


class TestVoicemeeterType:
    """Test cases for VoicemeeterType enum."""
    
    def test_enum_values(self):
        """Test enum values."""
        assert VoicemeeterType.VOICEMEETER.value == 1
        assert VoicemeeterType.VOICEMEETER_BANANA.value == 2
        assert VoicemeeterType.VOICEMEETER_POTATO.value == 3
    
    def test_enum_names(self):
        """Test enum names."""
        assert VoicemeeterType.VOICEMEETER.name == "VOICEMEETER"
        assert VoicemeeterType.VOICEMEETER_BANANA.name == "VOICEMEETER_BANANA"
        assert VoicemeeterType.VOICEMEETER_POTATO.name == "VOICEMEETER_POTATO"


if __name__ == "__main__":
    pytest.main([__file__])
