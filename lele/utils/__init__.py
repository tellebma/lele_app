"""Modules utilitaires pour Lele."""

from .ffmpeg import setup_ffmpeg, check_ffmpeg, get_ffmpeg_path
from .system import (
    get_system_info,
    get_whisper_device,
    check_cuda_compatibility,
    get_model_recommendations,
    get_system_info_message,
    log_system_info,
    get_pytorch_install_command,
    SystemInfo,
    GPUInfo,
)
from .settings import (
    get_settings_manager,
    get_settings,
    SettingsManager,
    AppSettings,
)

__all__ = [
    # FFmpeg
    "setup_ffmpeg",
    "check_ffmpeg",
    "get_ffmpeg_path",
    # System
    "get_system_info",
    "get_whisper_device",
    "check_cuda_compatibility",
    "get_model_recommendations",
    "get_system_info_message",
    "log_system_info",
    "get_pytorch_install_command",
    "SystemInfo",
    "GPUInfo",
    # Settings
    "get_settings_manager",
    "get_settings",
    "SettingsManager",
    "AppSettings",
]
