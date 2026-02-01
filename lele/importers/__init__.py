"""Importers pour différents formats de données."""

from .base import BaseImporter, ImportResult
from .text import TextImporter
from .audio import AudioImporter
from .video import VideoImporter
from .image import ImageImporter
from .spreadsheet import SpreadsheetImporter
from .bibliography import BibliographyImporter
from .refi_qda import RefiQdaImporter

__all__ = [
    "BaseImporter",
    "ImportResult",
    "TextImporter",
    "AudioImporter",
    "VideoImporter",
    "ImageImporter",
    "SpreadsheetImporter",
    "BibliographyImporter",
    "RefiQdaImporter",
]


def get_importer(file_path: str) -> BaseImporter:
    """Retourne l'importer approprié pour un fichier."""
    from pathlib import Path

    ext = Path(file_path).suffix.lower()

    importers = {
        # Texte
        ".txt": TextImporter,
        ".md": TextImporter,
        ".rtf": TextImporter,
        ".pdf": TextImporter,
        ".doc": TextImporter,
        ".docx": TextImporter,
        ".odt": TextImporter,
        # Audio
        ".mp3": AudioImporter,
        ".wav": AudioImporter,
        ".m4a": AudioImporter,
        ".flac": AudioImporter,
        ".ogg": AudioImporter,
        ".webm": AudioImporter,
        # Vidéo
        ".mp4": VideoImporter,
        ".avi": VideoImporter,
        ".mov": VideoImporter,
        ".mkv": VideoImporter,
        ".wmv": VideoImporter,
        # Image
        ".jpg": ImageImporter,
        ".jpeg": ImageImporter,
        ".png": ImageImporter,
        ".gif": ImageImporter,
        ".bmp": ImageImporter,
        ".tiff": ImageImporter,
        ".webp": ImageImporter,
        # Tableur
        ".xlsx": SpreadsheetImporter,
        ".xls": SpreadsheetImporter,
        ".csv": SpreadsheetImporter,
        ".ods": SpreadsheetImporter,
        # Bibliographie
        ".ris": BibliographyImporter,
        ".bib": BibliographyImporter,
        ".enw": BibliographyImporter,
        # REFI-QDA
        ".qdpx": RefiQdaImporter,
    }

    importer_class = importers.get(ext, TextImporter)
    return importer_class()
