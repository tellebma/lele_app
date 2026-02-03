"""Gestion des paramètres de l'application.

Ce module gère les préférences utilisateur et les projets récents.
Les paramètres sont stockés dans un fichier JSON dans le dossier utilisateur.
"""

import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field, asdict

from .. import get_logger

logger = get_logger("utils.settings")

# Chemin du fichier de configuration
SETTINGS_DIR = Path.home() / ".lele"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"
MAX_RECENT_PROJECTS = 10


@dataclass
class AppSettings:
    """Paramètres de l'application."""

    # Projets récents (liste de chemins)
    recent_projects: list = field(default_factory=list)

    # Paramètres de transcription
    whisper_model: str = "medium"
    whisper_language: Optional[str] = None
    transcription_show_timestamps: bool = False

    # Paramètres LLM local (pour auto-codage)
    llm_provider: str = "ollama"  # "ollama", "none"
    llm_model: str = "mistral"
    ollama_url: str = "http://localhost:11434"

    # Paramètres d'auto-codage
    autocoding_embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    autocoding_max_themes: int = 15
    autocoding_min_cluster_size: int = 3
    autocoding_confidence_threshold: float = 0.6

    # Interface
    window_width: int = 1400
    window_height: int = 900
    window_x: Optional[int] = None
    window_y: Optional[int] = None

    # Thème
    theme: str = "clam"

    def to_dict(self) -> dict:
        """Convertit en dictionnaire."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AppSettings":
        """Crée depuis un dictionnaire."""
        # Filtrer les clés inconnues
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


class SettingsManager:
    """Gestionnaire des paramètres de l'application."""

    _instance: Optional["SettingsManager"] = None
    _settings: Optional[AppSettings] = None

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._settings is None:
            self._settings = self._load()

    def _load(self) -> AppSettings:
        """Charge les paramètres depuis le fichier."""
        if SETTINGS_FILE.exists():
            try:
                data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
                logger.info(f"Paramètres chargés: {SETTINGS_FILE}")
                return AppSettings.from_dict(data)
            except Exception as e:
                logger.warning(f"Erreur lors du chargement des paramètres: {e}")

        return AppSettings()

    def save(self):
        """Sauvegarde les paramètres dans le fichier."""
        try:
            SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
            SETTINGS_FILE.write_text(
                json.dumps(self._settings.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.debug(f"Paramètres sauvegardés: {SETTINGS_FILE}")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des paramètres: {e}")

    @property
    def settings(self) -> AppSettings:
        """Retourne les paramètres."""
        return self._settings

    def add_recent_project(self, path: Path | str):
        """Ajoute un projet aux projets récents."""
        path_str = str(Path(path).resolve())

        # Retirer si déjà présent (pour le remettre en tête)
        if path_str in self._settings.recent_projects:
            self._settings.recent_projects.remove(path_str)

        # Ajouter en tête de liste
        self._settings.recent_projects.insert(0, path_str)

        # Limiter le nombre de projets récents
        self._settings.recent_projects = self._settings.recent_projects[:MAX_RECENT_PROJECTS]

        logger.info(f"Projet ajouté aux récents: {path_str}")
        self.save()

    def remove_recent_project(self, path: Path | str):
        """Retire un projet des projets récents."""
        path_str = str(Path(path).resolve())

        if path_str in self._settings.recent_projects:
            self._settings.recent_projects.remove(path_str)
            logger.info(f"Projet retiré des récents: {path_str}")
            self.save()

    def get_recent_projects(self) -> list[dict]:
        """
        Retourne les projets récents avec leurs informations.

        Returns:
            Liste de dictionnaires avec 'path', 'name', 'exists'
        """
        projects = []
        for path_str in self._settings.recent_projects:
            path = Path(path_str)
            projects.append(
                {
                    "path": path_str,
                    "name": path.name,
                    "exists": path.exists(),
                }
            )
        return projects

    def clear_recent_projects(self):
        """Efface tous les projets récents."""
        self._settings.recent_projects = []
        self.save()
        logger.info("Projets récents effacés")

    def clean_nonexistent_projects(self):
        """Retire les projets qui n'existent plus."""
        original_count = len(self._settings.recent_projects)
        self._settings.recent_projects = [
            p for p in self._settings.recent_projects if Path(p).exists()
        ]

        removed = original_count - len(self._settings.recent_projects)
        if removed > 0:
            logger.info(f"{removed} projet(s) inexistant(s) retiré(s)")
            self.save()


# Instance globale
_settings_manager: Optional[SettingsManager] = None


def get_settings_manager() -> SettingsManager:
    """Retourne le gestionnaire de paramètres (singleton)."""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager


def get_settings() -> AppSettings:
    """Raccourci pour obtenir les paramètres."""
    return get_settings_manager().settings
