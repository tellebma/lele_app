"""
Lele - Application d'analyse qualitative de données (QDA)
Inspirée de NVivo
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

__version__ = "0.1.0"
__author__ = "Lele Team"


def setup_logging(log_dir: Path | None = None, level: int = logging.INFO) -> logging.Logger:
    """
    Configure le système de logging pour l'application.

    Args:
        log_dir: Répertoire pour les fichiers de log (défaut: ~/.lele/logs)
        level: Niveau de log (défaut: INFO)

    Returns:
        Logger principal de l'application
    """
    # Créer le répertoire de logs
    if log_dir is None:
        log_dir = Path.home() / ".lele" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Nom du fichier de log avec date
    log_file = log_dir / f"lele_{datetime.now().strftime('%Y%m%d')}.log"

    # Créer le logger principal
    logger = logging.getLogger("lele")
    logger.setLevel(level)

    # Éviter les handlers dupliqués
    if logger.handlers:
        return logger

    # Format des messages
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler console (stderr)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler fichier
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.info(f"Logging initialisé - fichier: {log_file}")

    return logger


# Initialiser le logging au démarrage du module
logger = setup_logging()


def get_logger(name: str) -> logging.Logger:
    """
    Obtient un logger enfant pour un module spécifique.

    Args:
        name: Nom du module (ex: "ui.main_window")

    Returns:
        Logger pour le module
    """
    return logging.getLogger(f"lele.{name}")
