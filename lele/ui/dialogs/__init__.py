"""Dialogues de l'interface utilisateur."""

from .transcription_settings import (
    TranscriptionSettingsDialog,
    ModelDownloadDialog,
    ImportProgressDialog,
    download_whisper_model_async,
    WHISPER_MODELS,
    LANGUAGES,
)

from .auto_coding_config import AutoCodingConfigDialog
from .auto_coding_preview import AutoCodingPreviewDialog, AutoCodingProgressDialog
from .llm_settings import LLMSettingsDialog

__all__ = [
    # Transcription
    "TranscriptionSettingsDialog",
    "ModelDownloadDialog",
    "ImportProgressDialog",
    "download_whisper_model_async",
    "WHISPER_MODELS",
    "LANGUAGES",
    # Auto-coding
    "AutoCodingConfigDialog",
    "AutoCodingPreviewDialog",
    "AutoCodingProgressDialog",
    # LLM Settings
    "LLMSettingsDialog",
]
