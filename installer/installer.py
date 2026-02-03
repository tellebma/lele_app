#!/usr/bin/env python3
"""
Installeur intelligent pour Lele.

Détecte automatiquement le GPU et télécharge/installe la bonne version.
"""

import ctypes
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import zipfile

# Configuration
GITHUB_REPO = "tellebma/lele_app"  # À adapter selon votre repo
APP_NAME = "Lele"
DEFAULT_INSTALL_DIR = Path(os.environ.get("LOCALAPPDATA", "C:\\")) / APP_NAME


def is_admin():
    """Vérifie si le script s'exécute en tant qu'administrateur."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def detect_nvidia_gpu() -> dict:
    """Détecte la présence d'un GPU NVIDIA."""
    result = {
        "found": False,
        "name": None,
        "vram_mb": None,
    }

    # Chercher nvidia-smi
    nvidia_smi_paths = [
        shutil.which("nvidia-smi"),
        r"C:\Windows\System32\nvidia-smi.exe",
        r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe",
    ]

    nvidia_smi = None
    for path in nvidia_smi_paths:
        if path and os.path.exists(path):
            nvidia_smi = path
            break

    if not nvidia_smi:
        return result

    try:
        output = subprocess.run(
            [nvidia_smi, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )

        if output.returncode == 0 and output.stdout.strip():
            parts = output.stdout.strip().split(", ")
            if len(parts) >= 2:
                result["found"] = True
                result["name"] = parts[0].strip()
                result["vram_mb"] = int(float(parts[1].strip()))

    except Exception:
        pass

    return result


def get_latest_release() -> dict | None:
    """Récupère les informations de la dernière release GitHub."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

    try:
        req = Request(url, headers={"User-Agent": "Lele-Installer"})
        with urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Erreur API GitHub: {e}")
        return None


def download_file(url: str, dest: Path, progress_callback=None) -> bool:
    """Télécharge un fichier avec barre de progression."""
    try:
        req = Request(url, headers={"User-Agent": "Lele-Installer"})
        with urlopen(req, timeout=300) as response:
            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0
            block_size = 8192

            with open(dest, "wb") as f:
                while True:
                    chunk = response.read(block_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

                    if progress_callback and total_size > 0:
                        progress_callback(downloaded, total_size)

        return True

    except Exception as e:
        print(f"Erreur téléchargement: {e}")
        return False


def extract_zip(zip_path: Path, dest_dir: Path, progress_callback=None) -> bool:
    """Extrait une archive ZIP."""
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            members = zf.namelist()
            total = len(members)

            for i, member in enumerate(members):
                zf.extract(member, dest_dir)
                if progress_callback:
                    progress_callback(i + 1, total)

        return True

    except Exception as e:
        print(f"Erreur extraction: {e}")
        return False


def get_shell_folder(folder_name: str) -> Path | None:
    """Récupère un dossier spécial Windows (Desktop, StartMenu, etc.)."""
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
        ) as key:
            value, _ = winreg.QueryValueEx(key, folder_name)
            return Path(value)
    except Exception:
        return None


def create_shortcut(target: Path, shortcut_path: Path, description: str = "") -> bool:
    """Crée un raccourci Windows."""
    try:
        # S'assurer que le dossier parent existe
        shortcut_path.parent.mkdir(parents=True, exist_ok=True)

        # Utiliser PowerShell pour créer le raccourci
        # Échapper les guillemets dans les chemins
        target_str = str(target).replace("'", "''")
        shortcut_str = str(shortcut_path).replace("'", "''")
        workdir_str = str(target.parent).replace("'", "''")
        desc_str = description.replace("'", "''")

        ps_script = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{shortcut_str}')
$Shortcut.TargetPath = '{target_str}'
$Shortcut.WorkingDirectory = '{workdir_str}'
$Shortcut.Description = '{desc_str}'
$Shortcut.Save()
'''
        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )

        if result.returncode != 0:
            print(f"PowerShell error: {result.stderr}")
            return False

        return shortcut_path.exists()

    except Exception as e:
        print(f"Erreur création raccourci: {e}")
        return False


class InstallerApp:
    """Application d'installation avec interface graphique."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"Installation de {APP_NAME}")
        self.root.geometry("550x580")
        self.root.minsize(550, 580)
        self.root.resizable(True, True)

        # Centrer la fenêtre
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 550) // 2
        y = (self.root.winfo_screenheight() - 580) // 2
        self.root.geometry(f"+{x}+{y}")

        # Variables
        self.gpu_info = None
        self.release_info = None
        self.selected_variant = tk.StringVar(value="auto")
        self.install_dir = tk.StringVar(value=str(DEFAULT_INSTALL_DIR))
        self.create_desktop_shortcut = tk.BooleanVar(value=True)
        self.create_start_menu = tk.BooleanVar(value=True)

        self.setup_ui()
        self.detect_system()

    def setup_ui(self):
        """Configure l'interface utilisateur."""
        # Style
        style = ttk.Style()
        style.configure("Title.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("Subtitle.TLabel", font=("Segoe UI", 10))
        style.configure("Info.TLabel", font=("Segoe UI", 9), foreground="#666")

        # Frame principal
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Titre
        ttk.Label(
            main_frame,
            text=f"Installation de {APP_NAME}",
            style="Title.TLabel"
        ).pack(anchor=tk.W)

        ttk.Label(
            main_frame,
            text="Analyse Qualitative de Données",
            style="Subtitle.TLabel"
        ).pack(anchor=tk.W, pady=(0, 20))

        # Détection système
        system_frame = ttk.LabelFrame(main_frame, text="Système détecté", padding=10)
        system_frame.pack(fill=tk.X, pady=(0, 15))

        self.system_label = ttk.Label(system_frame, text="Détection en cours...")
        self.system_label.pack(anchor=tk.W)

        self.gpu_label = ttk.Label(system_frame, text="")
        self.gpu_label.pack(anchor=tk.W)

        # Choix de la version
        version_frame = ttk.LabelFrame(main_frame, text="Version à installer", padding=10)
        version_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Radiobutton(
            version_frame,
            text="Automatique (recommandé)",
            variable=self.selected_variant,
            value="auto"
        ).pack(anchor=tk.W)

        ttk.Radiobutton(
            version_frame,
            text="Version GPU (CUDA) - Plus rapide, nécessite GPU NVIDIA",
            variable=self.selected_variant,
            value="cuda"
        ).pack(anchor=tk.W)

        ttk.Radiobutton(
            version_frame,
            text="Version CPU - Compatible avec tous les PC",
            variable=self.selected_variant,
            value="cpu"
        ).pack(anchor=tk.W)

        # Dossier d'installation
        dir_frame = ttk.LabelFrame(main_frame, text="Dossier d'installation", padding=10)
        dir_frame.pack(fill=tk.X, pady=(0, 15))

        dir_row = ttk.Frame(dir_frame)
        dir_row.pack(fill=tk.X)

        ttk.Entry(dir_row, textvariable=self.install_dir, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(dir_row, text="Parcourir...", command=self.browse_dir).pack(side=tk.RIGHT, padx=(10, 0))

        # Options
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding=10)
        options_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Checkbutton(
            options_frame,
            text="Créer un raccourci sur le Bureau",
            variable=self.create_desktop_shortcut
        ).pack(anchor=tk.W)

        ttk.Checkbutton(
            options_frame,
            text="Créer une entrée dans le Menu Démarrer",
            variable=self.create_start_menu
        ).pack(anchor=tk.W)

        # Barre de progression (cachée initialement)
        self.progress_frame = ttk.Frame(main_frame)

        self.progress_label = ttk.Label(self.progress_frame, text="")
        self.progress_label.pack(anchor=tk.W)

        self.progress_bar = ttk.Progressbar(self.progress_frame, length=400, mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=5)

        self.progress_detail = ttk.Label(self.progress_frame, text="", style="Info.TLabel")
        self.progress_detail.pack(anchor=tk.W)

        # Boutons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.cancel_btn = ttk.Button(btn_frame, text="Annuler", command=self.root.quit)
        self.cancel_btn.pack(side=tk.RIGHT)

        self.install_btn = ttk.Button(btn_frame, text="Installer", command=self.start_install, state=tk.DISABLED)
        self.install_btn.pack(side=tk.RIGHT, padx=(0, 10))

    def browse_dir(self):
        """Ouvre le dialogue de sélection de dossier."""
        path = filedialog.askdirectory(initialdir=self.install_dir.get())
        if path:
            self.install_dir.set(path)

    def detect_system(self):
        """Détecte le système en arrière-plan."""
        def detect():
            # Détecter le GPU
            self.gpu_info = detect_nvidia_gpu()

            # Récupérer la release
            self.release_info = get_latest_release()

            # Mettre à jour l'UI
            self.root.after(0, self.update_system_info)

        threading.Thread(target=detect, daemon=True).start()

    def update_system_info(self):
        """Met à jour l'affichage des informations système."""
        # Info système
        import platform
        self.system_label.configure(text=f"Windows {platform.release()} - {platform.machine()}")

        # Info GPU
        if self.gpu_info and self.gpu_info["found"]:
            vram_gb = self.gpu_info["vram_mb"] / 1024
            self.gpu_label.configure(
                text=f"✅ GPU détecté: {self.gpu_info['name']} ({vram_gb:.1f} GB)",
                foreground="#2e7d32"
            )
        else:
            self.gpu_label.configure(
                text="❌ Aucun GPU NVIDIA détecté (version CPU sera installée)",
                foreground="#c62828"
            )

        # Activer le bouton si release trouvée
        if self.release_info:
            self.install_btn.configure(state=tk.NORMAL)
        else:
            messagebox.showerror(
                "Erreur",
                "Impossible de récupérer les informations de la dernière version.\n"
                "Vérifiez votre connexion Internet."
            )

    def get_download_url(self, variant: str) -> str | None:
        """Récupère l'URL de téléchargement pour la variante."""
        if not self.release_info:
            return None

        # Chercher l'asset correspondant
        target_name = f"Lele-{variant}.zip"

        for asset in self.release_info.get("assets", []):
            if asset["name"] == target_name:
                return asset["browser_download_url"]

        return None

    def start_install(self):
        """Démarre l'installation."""
        # Déterminer la variante
        variant = self.selected_variant.get()
        if variant == "auto":
            variant = "cuda" if (self.gpu_info and self.gpu_info["found"]) else "cpu"

        # Vérifier l'URL
        download_url = self.get_download_url(variant)
        if not download_url:
            messagebox.showerror(
                "Erreur",
                f"Version {variant} non trouvée dans la release.\n"
                "Veuillez réessayer plus tard."
            )
            return

        # Désactiver les contrôles
        self.install_btn.configure(state=tk.DISABLED)
        self.cancel_btn.configure(state=tk.DISABLED)

        # Afficher la progression
        self.progress_frame.pack(fill=tk.X, pady=(0, 15), before=self.cancel_btn.master)

        # Lancer l'installation en arrière-plan
        threading.Thread(
            target=self.do_install,
            args=(variant, download_url),
            daemon=True
        ).start()

    def do_install(self, variant: str, download_url: str):
        """Effectue l'installation."""
        try:
            install_dir = Path(self.install_dir.get())

            # Étape 1: Téléchargement
            self.update_progress("Téléchargement en cours...", 0)

            with tempfile.TemporaryDirectory() as tmp_dir:
                zip_path = Path(tmp_dir) / f"Lele-{variant}.zip"

                def on_download_progress(downloaded, total):
                    percent = (downloaded / total) * 50  # 50% pour le téléchargement
                    size_mb = downloaded / (1024 * 1024)
                    total_mb = total / (1024 * 1024)
                    self.root.after(0, lambda: self.update_progress(
                        "Téléchargement en cours...",
                        percent,
                        f"{size_mb:.1f} / {total_mb:.1f} MB"
                    ))

                if not download_file(download_url, zip_path, on_download_progress):
                    raise Exception("Échec du téléchargement")

                # Étape 2: Extraction
                self.root.after(0, lambda: self.update_progress("Extraction...", 50))

                # Créer le dossier d'installation
                install_dir.mkdir(parents=True, exist_ok=True)

                def on_extract_progress(current, total):
                    percent = 50 + (current / total) * 40  # 40% pour l'extraction
                    self.root.after(0, lambda: self.update_progress(
                        "Extraction...",
                        percent,
                        f"{current} / {total} fichiers"
                    ))

                if not extract_zip(zip_path, install_dir, on_extract_progress):
                    raise Exception("Échec de l'extraction")

            # Étape 3: Création des raccourcis
            self.root.after(0, lambda: self.update_progress("Création des raccourcis...", 90))

            exe_path = install_dir / "Lele" / "Lele.exe"

            shortcuts_created = []
            shortcuts_failed = []

            if self.create_desktop_shortcut.get():
                # Utiliser le registre pour obtenir le vrai chemin du Bureau
                desktop = get_shell_folder("Desktop")
                if not desktop:
                    desktop = Path(os.environ.get("USERPROFILE", "")) / "Desktop"

                if create_shortcut(
                    exe_path,
                    desktop / f"{APP_NAME}.lnk",
                    "Lele - Analyse Qualitative de Données"
                ):
                    shortcuts_created.append("Bureau")
                else:
                    shortcuts_failed.append("Bureau")

            if self.create_start_menu.get():
                # Utiliser le registre pour obtenir le vrai chemin du Menu Démarrer
                start_menu = get_shell_folder("Programs")
                if not start_menu:
                    start_menu = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Start Menu" / "Programs"

                if create_shortcut(
                    exe_path,
                    start_menu / f"{APP_NAME}.lnk",
                    "Lele - Analyse Qualitative de Données"
                ):
                    shortcuts_created.append("Menu Démarrer")
                else:
                    shortcuts_failed.append("Menu Démarrer")

            # Stocker les résultats pour l'affichage final
            self.shortcuts_created = shortcuts_created
            self.shortcuts_failed = shortcuts_failed

            # Terminé
            self.root.after(0, lambda: self.installation_complete(install_dir, variant))

        except Exception as e:
            self.root.after(0, lambda: self.installation_error(str(e)))

    def update_progress(self, label: str, percent: float, detail: str = ""):
        """Met à jour la barre de progression."""
        self.progress_label.configure(text=label)
        self.progress_bar["value"] = percent
        self.progress_detail.configure(text=detail)

    def installation_complete(self, install_dir: Path, variant: str):
        """Affichage de fin d'installation."""
        self.update_progress("Installation terminée!", 100)

        variant_text = "GPU (CUDA)" if variant == "cuda" else "CPU"

        # Construire le message avec les infos sur les raccourcis
        message = f"{APP_NAME} (version {variant_text}) a été installé avec succès!\n\n"
        message += f"Dossier: {install_dir}\n\n"

        if hasattr(self, 'shortcuts_created') and self.shortcuts_created:
            message += f"✅ Raccourcis créés: {', '.join(self.shortcuts_created)}\n"
        if hasattr(self, 'shortcuts_failed') and self.shortcuts_failed:
            message += f"⚠️ Raccourcis échoués: {', '.join(self.shortcuts_failed)}\n"

        message += "\nVoulez-vous lancer l'application maintenant?"

        result = messagebox.askyesno("Installation terminée", message)

        if result:
            exe_path = install_dir / "Lele" / "Lele.exe"
            if exe_path.exists():
                os.startfile(str(exe_path))

        self.root.quit()

    def installation_error(self, error: str):
        """Affichage d'erreur."""
        self.cancel_btn.configure(state=tk.NORMAL)

        messagebox.showerror(
            "Erreur d'installation",
            f"Une erreur est survenue:\n\n{error}\n\n"
            "Veuillez réessayer ou télécharger manuellement depuis GitHub."
        )

        self.progress_frame.pack_forget()
        self.install_btn.configure(state=tk.NORMAL)

    def run(self):
        """Lance l'application."""
        self.root.mainloop()


def main():
    """Point d'entrée."""
    app = InstallerApp()
    app.run()


if __name__ == "__main__":
    main()
