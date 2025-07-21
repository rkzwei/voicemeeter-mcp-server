"""Voicemeeter Remote API wrapper using ctypes."""

import ctypes
import ctypes.wintypes
import os
import platform
import time
from typing import Optional, Dict, Any, List
from enum import Enum


class VoicemeeterType(Enum):
    """Voicemeeter application types."""

    VOICEMEETER = 1
    VOICEMEETER_BANANA = 2
    VOICEMEETER_POTATO = 3


class VoicemeeterAPI:
    """Wrapper for Voicemeeter Remote API."""

    def __init__(self):
        self._dll: Optional[ctypes.CDLL] = None
        self._is_connected = False
        self._vm_type: Optional[VoicemeeterType] = None

    def _load_dll(self) -> bool:
        """Load the VoicemeeterRemote DLL."""
        try:
            # Detect system architecture
            is_64bit = (
                platform.machine().endswith("64")
                or platform.architecture()[0] == "64bit"
            )

            # Build DLL search paths based on architecture
            dll_paths = []

            if is_64bit:
                # 64-bit system - prefer 64-bit DLL
                dll_paths.extend(
                    [
                        "VoicemeeterRemote64.dll",  # Try from PATH first
                        os.path.join(
                            os.environ.get("PROGRAMFILES", ""),
                            "VB",
                            "Voicemeeter",
                            "VoicemeeterRemote64.dll",
                        ),
                        os.path.join(
                            os.environ.get("PROGRAMFILES(X86)", ""),
                            "VB",
                            "Voicemeeter",
                            "VoicemeeterRemote64.dll",
                        ),
                        os.path.join(
                            os.environ.get("WINDIR", ""),
                            "System32",
                            "VoicemeeterRemote64.dll",
                        ),
                        # Fallback to 32-bit if 64-bit not available
                        "VoicemeeterRemote.dll",
                        os.path.join(
                            os.environ.get("PROGRAMFILES(X86)", ""),
                            "VB",
                            "Voicemeeter",
                            "VoicemeeterRemote.dll",
                        ),
                        os.path.join(
                            os.environ.get("WINDIR", ""),
                            "SysWOW64",
                            "VoicemeeterRemote.dll",
                        ),
                    ]
                )
            else:
                # 32-bit system - use 32-bit DLL only
                dll_paths.extend(
                    [
                        "VoicemeeterRemote.dll",  # Try from PATH first
                        os.path.join(
                            os.environ.get("PROGRAMFILES", ""),
                            "VB",
                            "Voicemeeter",
                            "VoicemeeterRemote.dll",
                        ),
                        os.path.join(
                            os.environ.get("WINDIR", ""),
                            "System32",
                            "VoicemeeterRemote.dll",
                        ),
                    ]
                )

            # Try each DLL path
            for dll_path in dll_paths:
                try:
                    # Skip if path doesn't exist (for absolute paths)
                    if os.path.isabs(dll_path) and not os.path.exists(dll_path):
                        continue

                    self._dll = ctypes.CDLL(dll_path)
                    return True
                except OSError as e:
                    continue

            return False
        except Exception as e:
            return False

    def login(self) -> bool:
        """Login to Voicemeeter Remote API."""
        if not self._load_dll():
            return False

        try:
            # VBVMR_Login function
            login_func = self._dll.VBVMR_Login
            login_func.restype = ctypes.c_long

            result = login_func()
            if result == 0:
                self._is_connected = True
                # Get Voicemeeter type
                self._vm_type = self._get_voicemeeter_type()
                return True
            return False
        except Exception:
            return False

    def logout(self) -> bool:
        """Logout from Voicemeeter Remote API."""
        if not self._dll:
            return False

        try:
            logout_func = self._dll.VBVMR_Logout
            logout_func.restype = ctypes.c_long

            result = logout_func()
            self._is_connected = False
            return result == 0
        except Exception:
            return False

    def _get_voicemeeter_type(self) -> Optional[VoicemeeterType]:
        """Get the type of Voicemeeter running."""
        if not self._dll:
            return None

        try:
            get_type_func = self._dll.VBVMR_GetVoicemeeterType
            get_type_func.restype = ctypes.c_long
            get_type_func.argtypes = [ctypes.POINTER(ctypes.c_long)]

            vm_type = ctypes.c_long()
            result = get_type_func(ctypes.byref(vm_type))

            if result == 0:
                type_value = vm_type.value
                if type_value == 1:
                    return VoicemeeterType.VOICEMEETER
                elif type_value == 2:
                    return VoicemeeterType.VOICEMEETER_BANANA
                elif type_value == 3:
                    return VoicemeeterType.VOICEMEETER_POTATO
            return None
        except Exception:
            return None

    def get_parameter_float(self, param_name: str) -> Optional[float]:
        """Get a float parameter value."""
        if not self._dll or not self._is_connected:
            return None

        try:
            get_param_func = self._dll.VBVMR_GetParameterFloat
            get_param_func.restype = ctypes.c_long
            get_param_func.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_float)]

            value = ctypes.c_float()
            result = get_param_func(param_name.encode("ascii"), ctypes.byref(value))

            if result == 0:
                return value.value
            return None
        except Exception:
            return None

    def set_parameter_float(self, param_name: str, value: float) -> bool:
        """Set a float parameter value."""
        if not self._dll or not self._is_connected:
            return False

        try:
            set_param_func = self._dll.VBVMR_SetParameterFloat
            set_param_func.restype = ctypes.c_long
            set_param_func.argtypes = [ctypes.c_char_p, ctypes.c_float]

            result = set_param_func(param_name.encode("ascii"), ctypes.c_float(value))
            return result == 0
        except Exception:
            return False

    def get_parameter_string(self, param_name: str) -> Optional[str]:
        """Get a string parameter value."""
        if not self._dll or not self._is_connected:
            return None

        try:
            get_param_func = self._dll.VBVMR_GetParameterStringA
            get_param_func.restype = ctypes.c_long
            get_param_func.argtypes = [ctypes.c_char_p, ctypes.c_char_p]

            buffer = ctypes.create_string_buffer(512)
            result = get_param_func(param_name.encode("ascii"), buffer)

            if result == 0:
                return buffer.value.decode("ascii")
            return None
        except Exception:
            return None

    def set_parameter_string(self, param_name: str, value: str) -> bool:
        """Set a string parameter value."""
        if not self._dll or not self._is_connected:
            return False

        try:
            set_param_func = self._dll.VBVMR_SetParameterStringA
            set_param_func.restype = ctypes.c_long
            set_param_func.argtypes = [ctypes.c_char_p, ctypes.c_char_p]

            result = set_param_func(param_name.encode("ascii"), value.encode("ascii"))
            return result == 0
        except Exception:
            return False

    def run_voicemeeter(self, vm_type: VoicemeeterType) -> bool:
        """Run Voicemeeter application."""
        if not self._dll:
            return False

        try:
            run_func = self._dll.VBVMR_RunVoicemeeter
            run_func.restype = ctypes.c_long
            run_func.argtypes = [ctypes.c_long]

            result = run_func(vm_type.value)
            return result == 0
        except Exception:
            return False

    def is_parameters_dirty(self) -> bool:
        """Check if parameters have been updated."""
        if not self._dll or not self._is_connected:
            return False

        try:
            dirty_func = self._dll.VBVMR_IsParametersDirty
            dirty_func.restype = ctypes.c_long

            result = dirty_func()
            return result > 0
        except Exception:
            return False

    def get_level(self, level_type: int, channel: int) -> Optional[float]:
        """Get audio level for specified type and channel."""
        if not self._dll or not self._is_connected:
            return None

        try:
            get_level_func = self._dll.VBVMR_GetLevel
            get_level_func.restype = ctypes.c_long
            get_level_func.argtypes = [
                ctypes.c_long,
                ctypes.c_long,
                ctypes.POINTER(ctypes.c_float),
            ]

            value = ctypes.c_float()
            result = get_level_func(level_type, channel, ctypes.byref(value))

            if result == 0:
                return value.value
            return None
        except Exception:
            return None

    def get_version(self) -> Optional[str]:
        """Get Voicemeeter version."""
        if not self._dll:
            return None

        try:
            get_version_func = self._dll.VBVMR_GetVoicemeeterVersion
            get_version_func.restype = ctypes.c_long
            get_version_func.argtypes = [ctypes.POINTER(ctypes.c_long)]

            version = ctypes.c_long()
            result = get_version_func(ctypes.byref(version))

            if result == 0:
                v = version.value
                return f"{(v & 0xFF000000) >> 24}.{(v & 0x00FF0000) >> 16}.{(v & 0x0000FF00) >> 8}.{v & 0x000000FF}"
            return None
        except Exception:
            return None

    @property
    def is_connected(self) -> bool:
        """Check if connected to Voicemeeter."""
        return self._is_connected

    @property
    def voicemeeter_type(self) -> Optional[VoicemeeterType]:
        """Get the type of Voicemeeter running."""
        return self._vm_type

    def __enter__(self):
        """Context manager entry."""
        self.login()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.logout()
