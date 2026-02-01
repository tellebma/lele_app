"""Interface de base pour les importers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from ..models.source import Source, SourceType


@dataclass
class ImportResult:
    """Résultat d'un import."""

    success: bool
    source: Optional[Source] = None
    error: Optional[str] = None
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseImporter(ABC):
    """Classe de base pour tous les importers."""

    source_type: SourceType = SourceType.OTHER

    def __init__(self):
        self.progress_callback = None

    def set_progress_callback(self, callback):
        """Définit un callback pour les mises à jour de progression."""
        self.progress_callback = callback

    def report_progress(self, progress: float, message: str = ""):
        """Rapporte la progression de l'import."""
        if self.progress_callback:
            self.progress_callback(progress, message)

    @abstractmethod
    def import_file(
        self,
        file_path: Path,
        project_files_path: Path,
        **options,
    ) -> ImportResult:
        """
        Importe un fichier et retourne une Source.

        Args:
            file_path: Chemin du fichier à importer
            project_files_path: Dossier où stocker les fichiers du projet
            **options: Options spécifiques à l'importer

        Returns:
            ImportResult avec la source créée ou une erreur
        """
        pass

    def validate_file(self, file_path: Path) -> tuple[bool, str]:
        """
        Valide qu'un fichier peut être importé.

        Returns:
            Tuple (valide, message_erreur)
        """
        if not file_path.exists():
            return False, f"Le fichier n'existe pas: {file_path}"
        if not file_path.is_file():
            return False, f"Ce n'est pas un fichier: {file_path}"
        return True, ""

    def copy_to_project(
        self, source_path: Path, project_files_path: Path
    ) -> Path:
        """Copie un fichier dans le dossier du projet."""
        import shutil

        project_files_path.mkdir(parents=True, exist_ok=True)

        # Gérer les noms de fichiers en double
        dest_path = project_files_path / source_path.name
        counter = 1
        while dest_path.exists():
            stem = source_path.stem
            suffix = source_path.suffix
            dest_path = project_files_path / f"{stem}_{counter}{suffix}"
            counter += 1

        shutil.copy2(source_path, dest_path)
        return dest_path

    def get_file_metadata(self, file_path: Path) -> dict:
        """Extrait les métadonnées de base d'un fichier."""
        import os
        from datetime import datetime

        stat = file_path.stat()
        return {
            "original_path": str(file_path),
            "file_size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "extension": file_path.suffix.lower(),
        }
