"""Utilitaire pour la configuration de FFmpeg.

Ce module gère l'installation et la configuration de FFmpeg pour Whisper.
Il utilise imageio-ffmpeg pour fournir des binaires FFmpeg intégrés,
évitant ainsi aux utilisateurs d'installer FFmpeg manuellement.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

from .. import get_logger

logger = get_logger("utils.ffmpeg")

# Variable globale pour stocker le chemin FFmpeg configuré
_ffmpeg_path: Optional[str] = None
_ffmpeg_configured: bool = False
_ffmpeg_wrapper_dir: Optional[str] = None


def get_ffmpeg_path() -> Optional[str]:
    """
    Retourne le chemin vers l'exécutable FFmpeg.

    Cherche dans l'ordre:
    1. FFmpeg du système (dans le PATH)
    2. FFmpeg fourni par imageio-ffmpeg

    Returns:
        Chemin vers ffmpeg ou None si non trouvé
    """
    global _ffmpeg_path

    if _ffmpeg_path is not None:
        return _ffmpeg_path

    # 1. Vérifier si FFmpeg est dans le PATH système
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        logger.info(f"FFmpeg système trouvé: {system_ffmpeg}")
        _ffmpeg_path = system_ffmpeg
        return _ffmpeg_path

    # 2. Utiliser imageio-ffmpeg
    try:
        import imageio_ffmpeg

        bundled_ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        if bundled_ffmpeg and Path(bundled_ffmpeg).exists():
            logger.info(f"FFmpeg intégré trouvé: {bundled_ffmpeg}")
            _ffmpeg_path = bundled_ffmpeg
            return _ffmpeg_path
    except ImportError:
        logger.warning("imageio-ffmpeg non installé")
    except Exception as e:
        logger.warning(f"Erreur lors de la récupération de FFmpeg intégré: {e}")

    logger.error("FFmpeg non trouvé")
    return None


def _create_ffmpeg_wrapper() -> Optional[str]:
    """
    Crée un lien/copie de FFmpeg avec le nom standard.

    imageio-ffmpeg utilise un nom versionné (ex: ffmpeg-win-x86_64-v7.1.exe)
    mais Whisper cherche 'ffmpeg' ou 'ffmpeg.exe'.

    Returns:
        Chemin vers le répertoire contenant le wrapper, ou None si échec
    """
    global _ffmpeg_wrapper_dir

    if _ffmpeg_wrapper_dir and Path(_ffmpeg_wrapper_dir).exists():
        return _ffmpeg_wrapper_dir

    ffmpeg_path = get_ffmpeg_path()
    if not ffmpeg_path:
        return None

    ffmpeg_path = Path(ffmpeg_path)

    # Si l'exécutable s'appelle déjà ffmpeg(.exe), pas besoin de wrapper
    expected_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    if ffmpeg_path.name == expected_name:
        logger.info(f"FFmpeg a déjà le nom standard: {ffmpeg_path}")
        return str(ffmpeg_path.parent)

    # Créer un répertoire temporaire persistant pour le wrapper
    wrapper_dir = Path(tempfile.gettempdir()) / "lele_ffmpeg"
    wrapper_dir.mkdir(exist_ok=True)

    wrapper_path = wrapper_dir / expected_name

    # Créer le lien/copie si nécessaire
    if not wrapper_path.exists():
        try:
            # Essayer de créer un lien symbolique (nécessite droits admin sur Windows)
            wrapper_path.symlink_to(ffmpeg_path)
            logger.info(f"Lien symbolique FFmpeg créé: {wrapper_path}")
        except (OSError, NotImplementedError):
            # Fallback: copier l'exécutable
            try:
                shutil.copy2(ffmpeg_path, wrapper_path)
                logger.info(f"Copie FFmpeg créée: {wrapper_path}")
            except Exception as e:
                logger.error(f"Impossible de créer le wrapper FFmpeg: {e}")
                return None
    else:
        logger.info(f"Wrapper FFmpeg existant: {wrapper_path}")

    _ffmpeg_wrapper_dir = str(wrapper_dir)
    return _ffmpeg_wrapper_dir


def setup_ffmpeg() -> bool:
    """
    Configure FFmpeg pour être utilisable par Whisper.

    Whisper utilise FFmpeg via subprocess en cherchant 'ffmpeg' dans le PATH.
    Cette fonction crée un wrapper avec le nom standard et l'ajoute au PATH.

    Returns:
        True si FFmpeg est configuré avec succès, False sinon
    """
    global _ffmpeg_configured

    if _ffmpeg_configured:
        return True

    ffmpeg_path = get_ffmpeg_path()
    if not ffmpeg_path:
        logger.error(
            "FFmpeg n'est pas disponible. " "Installez-le avec: pip install imageio-ffmpeg"
        )
        return False

    # Créer un wrapper avec le nom standard (ffmpeg.exe)
    wrapper_dir = _create_ffmpeg_wrapper()
    if wrapper_dir:
        current_path = os.environ.get("PATH", "")
        if wrapper_dir not in current_path:
            # Ajouter au début du PATH pour priorité
            os.environ["PATH"] = wrapper_dir + os.pathsep + current_path
            logger.info(f"Répertoire wrapper FFmpeg ajouté au PATH: {wrapper_dir}")
    else:
        # Fallback: ajouter le répertoire original
        ffmpeg_dir = str(Path(ffmpeg_path).parent)
        current_path = os.environ.get("PATH", "")
        if ffmpeg_dir not in current_path:
            os.environ["PATH"] = ffmpeg_dir + os.pathsep + current_path
            logger.info(f"FFmpeg ajouté au PATH (fallback): {ffmpeg_dir}")

    _ffmpeg_configured = True
    logger.info("FFmpeg configuré avec succès")
    return True


def check_ffmpeg() -> dict:
    """
    Vérifie l'installation de FFmpeg et retourne des informations.

    Returns:
        Dictionnaire avec:
        - available: bool - FFmpeg est disponible
        - path: str|None - Chemin vers l'exécutable
        - version: str|None - Version de FFmpeg
        - source: str - 'system', 'bundled', ou 'not_found'
    """
    result = {
        "available": False,
        "path": None,
        "version": None,
        "source": "not_found",
    }

    # Vérifier le système d'abord
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        result["path"] = system_ffmpeg
        result["source"] = "system"
    else:
        # Essayer imageio-ffmpeg
        try:
            import imageio_ffmpeg

            bundled = imageio_ffmpeg.get_ffmpeg_exe()
            if bundled and Path(bundled).exists():
                result["path"] = bundled
                result["source"] = "bundled"
        except Exception:
            pass

    if result["path"]:
        result["available"] = True
        # Récupérer la version
        try:
            proc = subprocess.run(
                [result["path"], "-version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if proc.returncode == 0:
                # Première ligne contient la version
                first_line = proc.stdout.split("\n")[0]
                result["version"] = first_line
        except Exception as e:
            logger.debug(f"Impossible de récupérer la version FFmpeg: {e}")

    return result


def get_ffmpeg_info_message() -> str:
    """
    Retourne un message d'information sur l'état de FFmpeg.

    Returns:
        Message formaté pour affichage à l'utilisateur
    """
    info = check_ffmpeg()

    if not info["available"]:
        return (
            "⚠️ FFmpeg n'est pas installé.\n\n"
            "FFmpeg est requis pour la transcription audio/vidéo.\n\n"
            "Solution: Exécutez la commande suivante:\n"
            "  pip install imageio-ffmpeg\n\n"
            "Puis redémarrez l'application."
        )

    source_text = {
        "system": "installation système",
        "bundled": "intégré (imageio-ffmpeg)",
    }.get(info["source"], "inconnu")

    version = info["version"] or "inconnue"

    return f"✅ FFmpeg disponible\nSource: {source_text}\nVersion: {version}"
