#!/usr/bin/env python3
"""
Script de build pour Lele.

Usage:
    python build.py cpu      # Build version CPU (~500 MB)
    python build.py cuda     # Build version CUDA/GPU (~2.5 GB)
    python build.py --check  # Vérifier l'environnement
"""

import argparse
import subprocess
import sys
from pathlib import Path


def check_environment():
    """Vérifie l'environnement de build."""
    print("=== Vérification de l'environnement ===\n")

    # Python
    print(f"Python: {sys.version}")

    # PyInstaller
    try:
        import PyInstaller
        print(f"PyInstaller: {PyInstaller.__version__}")
    except ImportError:
        print("PyInstaller: ❌ Non installé (pip install pyinstaller)")
        return False

    # PyTorch
    try:
        import torch
        cuda_status = "✅ CUDA" if torch.cuda.is_available() else "CPU uniquement"
        print(f"PyTorch: {torch.__version__} ({cuda_status})")

        if torch.cuda.is_available():
            print(f"  CUDA version: {torch.version.cuda}")
            print(f"  GPU: {torch.cuda.get_device_name(0)}")
    except ImportError:
        print("PyTorch: ❌ Non installé")
        return False

    # Whisper
    try:
        import whisper
        print(f"Whisper: ✅ Installé")
    except ImportError:
        print("Whisper: ❌ Non installé (pip install openai-whisper)")
        return False

    # imageio-ffmpeg
    try:
        import imageio_ffmpeg
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        print(f"FFmpeg: ✅ {ffmpeg_path}")
    except ImportError:
        print("FFmpeg: ❌ Non installé (pip install imageio-ffmpeg)")
        return False

    print("\n✅ Environnement prêt pour le build")
    return True


def install_dependencies(variant: str):
    """Installe les dépendances selon la variante."""
    req_file = f"requirements-{variant}.txt"

    if not Path(req_file).exists():
        print(f"❌ Fichier {req_file} non trouvé")
        return False

    print(f"=== Installation des dépendances ({variant}) ===\n")

    # Désinstaller PyTorch existant pour éviter les conflits
    print("Désinstallation de PyTorch existant...")
    subprocess.run(
        [sys.executable, "-m", "pip", "uninstall", "-y", "torch", "torchaudio", "torchvision"],
        capture_output=True,
    )

    # Installer les nouvelles dépendances
    print(f"Installation depuis {req_file}...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", req_file],
        check=False,
    )

    if result.returncode != 0:
        print(f"❌ Erreur lors de l'installation")
        return False

    print("\n✅ Dépendances installées")
    return True


def build_app():
    """Lance le build PyInstaller."""
    print("\n=== Build PyInstaller ===\n")

    # Vérifier que PyInstaller est installé
    try:
        import PyInstaller
    except ImportError:
        print("Installation de PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # Nettoyer les builds précédents
    for folder in ["build", "dist"]:
        path = Path(folder)
        if path.exists():
            print(f"Nettoyage de {folder}/...")
            import shutil
            shutil.rmtree(path)

    # Lancer PyInstaller
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "lele.spec", "--noconfirm"],
        check=False,
    )

    if result.returncode != 0:
        print("❌ Erreur lors du build")
        return False

    print("\n✅ Build terminé!")
    print(f"   L'application se trouve dans: dist/Lele/")
    return True


def main():
    parser = argparse.ArgumentParser(description="Build Lele application")
    parser.add_argument(
        "variant",
        nargs="?",
        choices=["cpu", "cuda"],
        help="Variante à construire (cpu ou cuda)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Vérifier l'environnement sans build",
    )
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="Ne pas réinstaller les dépendances",
    )

    args = parser.parse_args()

    if args.check:
        check_environment()
        return

    if not args.variant:
        parser.print_help()
        print("\n💡 Conseil:")
        print("   - cpu: Version légère (~500 MB), fonctionne partout")
        print("   - cuda: Version GPU (~2.5 GB), nécessite GPU NVIDIA")
        return

    print(f"🚀 Build Lele - Version {args.variant.upper()}\n")

    # Installer les dépendances
    if not args.skip_install:
        if not install_dependencies(args.variant):
            sys.exit(1)

    # Vérifier l'environnement
    if not check_environment():
        sys.exit(1)

    # Build
    if not build_app():
        sys.exit(1)

    # Taille finale
    dist_path = Path("dist/Lele")
    if dist_path.exists():
        total_size = sum(f.stat().st_size for f in dist_path.rglob("*") if f.is_file())
        size_mb = total_size / (1024 * 1024)
        print(f"\n📦 Taille totale: {size_mb:.1f} MB")


if __name__ == "__main__":
    main()
