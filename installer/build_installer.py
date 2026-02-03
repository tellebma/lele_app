#!/usr/bin/env python3
"""
Script pour construire l'installeur Lele.

Usage:
    python build_installer.py
"""

import subprocess
import sys
import shutil
from pathlib import Path


def main():
    """Construit l'installeur."""
    print("=" * 50)
    print("  Construction de l'installeur Lele")
    print("=" * 50)

    installer_dir = Path(__file__).parent
    dist_dir = installer_dir / "dist"
    build_dir = installer_dir / "build"

    # Nettoyer
    for folder in [dist_dir, build_dir]:
        if folder.exists():
            print(f"Nettoyage de {folder}...")
            shutil.rmtree(folder)

    # Vérifier PyInstaller
    try:
        import PyInstaller
        print(f"PyInstaller: {PyInstaller.__version__}")
    except ImportError:
        print("Installation de PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # Build
    print("\nConstruction de l'installeur...")

    result = subprocess.run([
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "Lele-Installer",
        "--icon", str(installer_dir.parent / "assets" / "icon.ico") if (installer_dir.parent / "assets" / "icon.ico").exists() else "",
        "--add-data", "",  # Pas de données supplémentaires
        "--clean",
        "--noconfirm",
        str(installer_dir / "installer.py"),
    ], cwd=installer_dir)

    if result.returncode != 0:
        print("\n❌ Erreur lors du build")
        return 1

    # Vérifier le résultat
    exe_path = dist_dir / "Lele-Installer.exe"
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"\n✅ Installeur créé: {exe_path}")
        print(f"   Taille: {size_mb:.1f} MB")
    else:
        print("\n❌ Fichier exe non trouvé")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
