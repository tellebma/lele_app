"""Utilitaire de vérification système et détection du matériel.

Ce module détecte les capacités matérielles (GPU, CUDA, etc.)
et configure automatiquement les bibliothèques en conséquence.
"""

import os
import platform
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Optional

from .. import get_logger

logger = get_logger("utils.system")

# Cache global pour les infos système
_system_info: Optional["SystemInfo"] = None


@dataclass
class GPUInfo:
    """Informations sur un GPU."""
    name: str
    memory_total_mb: int = 0
    memory_free_mb: int = 0
    cuda_version: Optional[str] = None
    driver_version: Optional[str] = None


@dataclass
class SystemInfo:
    """Informations système complètes."""
    # OS
    os_name: str = ""
    os_version: str = ""
    python_version: str = ""

    # CPU
    cpu_name: str = ""
    cpu_cores: int = 0

    # RAM
    ram_total_gb: float = 0.0
    ram_available_gb: float = 0.0

    # GPU/CUDA
    has_nvidia_gpu: bool = False
    cuda_available: bool = False
    cuda_version: Optional[str] = None
    cudnn_available: bool = False
    cudnn_version: Optional[str] = None
    gpus: list = field(default_factory=list)

    # PyTorch
    torch_available: bool = False
    torch_version: Optional[str] = None
    torch_cuda_available: bool = False
    torch_cuda_version: Optional[str] = None
    torch_device: str = "cpu"

    # Recommandations
    recommended_device: str = "cpu"
    warnings: list = field(default_factory=list)


def get_system_info(force_refresh: bool = False) -> SystemInfo:
    """
    Récupère les informations système complètes.

    Args:
        force_refresh: Si True, force la mise à jour des infos

    Returns:
        SystemInfo avec toutes les informations détectées
    """
    global _system_info

    if _system_info is not None and not force_refresh:
        return _system_info

    info = SystemInfo()

    # Informations OS
    info.os_name = platform.system()
    info.os_version = platform.version()
    info.python_version = sys.version.split()[0]

    # CPU
    info.cpu_name = platform.processor() or "Unknown"
    info.cpu_cores = os.cpu_count() or 1

    # RAM
    try:
        import psutil
        mem = psutil.virtual_memory()
        info.ram_total_gb = mem.total / (1024 ** 3)
        info.ram_available_gb = mem.available / (1024 ** 3)
    except ImportError:
        logger.debug("psutil non disponible - infos RAM limitées")

    # Détection GPU NVIDIA
    _detect_nvidia_gpu(info)

    # Détection PyTorch et CUDA
    _detect_pytorch(info)

    # Déterminer le device recommandé
    _determine_recommended_device(info)

    _system_info = info
    return info


def _detect_nvidia_gpu(info: SystemInfo) -> None:
    """Détecte les GPU NVIDIA via nvidia-smi."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.free,driver_version",
             "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            info.has_nvidia_gpu = True
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 4:
                        gpu = GPUInfo(
                            name=parts[0],
                            memory_total_mb=int(float(parts[1])),
                            memory_free_mb=int(float(parts[2])),
                            driver_version=parts[3],
                        )
                        info.gpus.append(gpu)

            # Récupérer la version CUDA supportée par le driver
            cuda_result = subprocess.run(
                ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if cuda_result.returncode == 0:
                # nvidia-smi affiche aussi la version CUDA max supportée
                full_output = subprocess.run(
                    ["nvidia-smi"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if "CUDA Version:" in full_output.stdout:
                    for line in full_output.stdout.split("\n"):
                        if "CUDA Version:" in line:
                            parts = line.split("CUDA Version:")
                            if len(parts) > 1:
                                info.cuda_version = parts[1].strip().split()[0]
                                break

            logger.info(f"GPU NVIDIA détecté: {len(info.gpus)} GPU(s)")
            for gpu in info.gpus:
                logger.info(f"  - {gpu.name} ({gpu.memory_total_mb} MB)")

    except FileNotFoundError:
        logger.debug("nvidia-smi non trouvé - pas de GPU NVIDIA")
    except subprocess.TimeoutExpired:
        logger.warning("Timeout lors de la détection GPU")
    except Exception as e:
        logger.debug(f"Erreur détection GPU: {e}")


def _detect_pytorch(info: SystemInfo) -> None:
    """Détecte PyTorch et sa configuration CUDA."""
    try:
        import torch

        info.torch_available = True
        info.torch_version = torch.__version__

        # Vérifier CUDA dans PyTorch
        info.torch_cuda_available = torch.cuda.is_available()

        if info.torch_cuda_available:
            info.torch_cuda_version = torch.version.cuda
            info.torch_device = "cuda"

            # Infos cuDNN
            if torch.backends.cudnn.is_available():
                info.cudnn_available = True
                info.cudnn_version = str(torch.backends.cudnn.version())

            logger.info(f"PyTorch {info.torch_version} avec CUDA {info.torch_cuda_version}")
            logger.info(f"cuDNN disponible: {info.cudnn_available}")
        else:
            info.torch_device = "cpu"
            logger.info(f"PyTorch {info.torch_version} (CPU uniquement)")

            # Avertissement si GPU disponible mais PyTorch CPU
            if info.has_nvidia_gpu:
                warning = (
                    "GPU NVIDIA détecté mais PyTorch est en mode CPU. "
                    "Installez PyTorch avec CUDA pour utiliser le GPU."
                )
                info.warnings.append(warning)
                logger.warning(warning)

    except ImportError:
        logger.debug("PyTorch non installé")


def _determine_recommended_device(info: SystemInfo) -> None:
    """Détermine le device recommandé pour les calculs."""
    if info.torch_cuda_available:
        info.recommended_device = "cuda"

        # Vérifier la mémoire GPU disponible
        if info.gpus:
            max_memory = max(gpu.memory_free_mb for gpu in info.gpus)
            if max_memory < 2000:  # Moins de 2 GB libres
                info.warnings.append(
                    f"Mémoire GPU faible ({max_memory} MB). "
                    "Utilisez un modèle plus petit ou le CPU."
                )
    else:
        info.recommended_device = "cpu"

        # Vérifier la RAM disponible pour le CPU
        if info.ram_available_gb < 4:
            info.warnings.append(
                f"RAM disponible faible ({info.ram_available_gb:.1f} GB). "
                "Utilisez un modèle léger (tiny ou base)."
            )


def get_whisper_device() -> str:
    """
    Retourne le device optimal pour Whisper.

    Returns:
        "cuda" si disponible, sinon "cpu"
    """
    info = get_system_info()
    return info.recommended_device


def check_cuda_compatibility() -> dict:
    """
    Vérifie la compatibilité CUDA complète.

    Returns:
        Dictionnaire avec le statut de compatibilité
    """
    info = get_system_info()

    return {
        "nvidia_gpu": info.has_nvidia_gpu,
        "cuda_driver": info.cuda_version is not None,
        "cuda_driver_version": info.cuda_version,
        "pytorch_cuda": info.torch_cuda_available,
        "pytorch_cuda_version": info.torch_cuda_version,
        "cudnn": info.cudnn_available,
        "ready": info.torch_cuda_available,
        "device": info.recommended_device,
        "warnings": info.warnings,
    }


def get_model_recommendations(model_size: str = "medium") -> dict:
    """
    Retourne des recommandations pour un modèle Whisper donné.

    Args:
        model_size: Taille du modèle (tiny, base, small, medium, large)

    Returns:
        Recommandations et avertissements
    """
    # Mémoire requise approximative (en MB)
    model_memory = {
        "tiny": 500,
        "base": 1000,
        "small": 2000,
        "medium": 5000,
        "large": 10000,
        "large-v2": 10000,
        "large-v3": 10000,
    }

    required_mb = model_memory.get(model_size, 5000)
    info = get_system_info()

    result = {
        "model": model_size,
        "required_memory_mb": required_mb,
        "recommended_device": info.recommended_device,
        "can_use_gpu": False,
        "can_use_cpu": True,
        "warnings": [],
    }

    # Vérifier GPU
    if info.torch_cuda_available and info.gpus:
        max_gpu_memory = max(gpu.memory_free_mb for gpu in info.gpus)
        if max_gpu_memory >= required_mb:
            result["can_use_gpu"] = True
            result["gpu_memory_available_mb"] = max_gpu_memory
        else:
            result["warnings"].append(
                f"Mémoire GPU insuffisante ({max_gpu_memory} MB < {required_mb} MB requis). "
                "Le modèle sera chargé sur CPU."
            )

    # Vérifier CPU/RAM
    ram_mb = info.ram_available_gb * 1024
    if ram_mb < required_mb * 1.5:  # Marge de sécurité
        result["warnings"].append(
            f"RAM disponible faible ({info.ram_available_gb:.1f} GB). "
            "Considérez un modèle plus petit."
        )
        if model_size in ["large", "large-v2", "large-v3"]:
            result["can_use_cpu"] = False

    return result


def get_system_info_message() -> str:
    """
    Retourne un message formaté avec les infos système.

    Returns:
        Message formaté pour affichage
    """
    info = get_system_info()

    lines = [
        "═══ Informations Système ═══",
        f"OS: {info.os_name} {info.os_version}",
        f"Python: {info.python_version}",
        f"CPU: {info.cpu_name} ({info.cpu_cores} cœurs)",
    ]

    if info.ram_total_gb > 0:
        lines.append(f"RAM: {info.ram_available_gb:.1f} / {info.ram_total_gb:.1f} GB disponible")

    lines.append("")
    lines.append("═══ GPU / CUDA ═══")

    if info.has_nvidia_gpu:
        for i, gpu in enumerate(info.gpus):
            lines.append(f"GPU {i}: {gpu.name}")
            lines.append(f"  Mémoire: {gpu.memory_free_mb} / {gpu.memory_total_mb} MB")
            if gpu.driver_version:
                lines.append(f"  Driver: {gpu.driver_version}")
        if info.cuda_version:
            lines.append(f"CUDA (driver): {info.cuda_version}")
    else:
        lines.append("Aucun GPU NVIDIA détecté")

    lines.append("")
    lines.append("═══ PyTorch ═══")

    if info.torch_available:
        lines.append(f"Version: {info.torch_version}")
        if info.torch_cuda_available:
            lines.append(f"✅ CUDA activé: {info.torch_cuda_version}")
            if info.cudnn_available:
                lines.append(f"✅ cuDNN: {info.cudnn_version}")
        else:
            lines.append("❌ CUDA non disponible (mode CPU)")
    else:
        lines.append("PyTorch non installé")

    lines.append("")
    lines.append(f"🎯 Device recommandé: {info.recommended_device.upper()}")

    if info.warnings:
        lines.append("")
        lines.append("⚠️ Avertissements:")
        for warning in info.warnings:
            lines.append(f"  • {warning}")

    return "\n".join(lines)


def log_system_info() -> None:
    """Log les informations système au démarrage."""
    info = get_system_info()

    logger.info("=== Informations Système ===")
    logger.info(f"OS: {info.os_name} {info.os_version}")
    logger.info(f"Python: {info.python_version}")
    logger.info(f"CPU: {info.cpu_name} ({info.cpu_cores} cœurs)")

    if info.ram_total_gb > 0:
        logger.info(f"RAM: {info.ram_available_gb:.1f} / {info.ram_total_gb:.1f} GB")

    if info.has_nvidia_gpu:
        for gpu in info.gpus:
            logger.info(f"GPU: {gpu.name} ({gpu.memory_total_mb} MB)")
        if info.cuda_version:
            logger.info(f"CUDA driver: {info.cuda_version}")

    if info.torch_available:
        logger.info(f"PyTorch: {info.torch_version}")
        if info.torch_cuda_available:
            logger.info(f"PyTorch CUDA: {info.torch_cuda_version}")
        else:
            logger.info("PyTorch: CPU uniquement")

    logger.info(f"Device recommandé: {info.recommended_device}")

    for warning in info.warnings:
        logger.warning(warning)


def get_pytorch_install_command() -> str:
    """
    Retourne la commande d'installation PyTorch avec CUDA.

    Returns:
        Commande pip à exécuter
    """
    info = get_system_info()

    if not info.has_nvidia_gpu:
        return "pip install torch torchvision torchaudio"

    # Déterminer la version CUDA recommandée
    cuda_version = info.cuda_version
    if cuda_version:
        major_minor = ".".join(cuda_version.split(".")[:2])
        major = int(cuda_version.split(".")[0])

        if major >= 12:
            cuda_suffix = "cu121"
        elif major >= 11:
            cuda_suffix = "cu118"
        else:
            cuda_suffix = "cu117"
    else:
        cuda_suffix = "cu121"  # Par défaut

    return (
        f"pip install torch torchvision torchaudio "
        f"--index-url https://download.pytorch.org/whl/{cuda_suffix}"
    )
