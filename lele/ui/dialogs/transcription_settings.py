"""Dialogue de paramètres de transcription audio/vidéo."""

import threading
import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable

from ...utils.system import (
    get_system_info,
    check_cuda_compatibility,
    get_pytorch_install_command,
)

# Informations sur les modèles Whisper
WHISPER_MODELS = [
    ("tiny", "Tiny - Très rapide (~1GB VRAM)", "~39 MB"),
    ("base", "Base - Équilibré (~1GB VRAM)", "~74 MB"),
    ("small", "Small - Bon (~2GB VRAM)", "~244 MB"),
    ("medium", "Medium - Haute qualité (~5GB VRAM)", "~769 MB"),
    ("large", "Large - Meilleure qualité (~10GB VRAM)", "~1550 MB"),
]

LANGUAGES = [
    ("auto", "Détection automatique"),
    ("fr", "Français"),
    ("en", "Anglais"),
    ("es", "Espagnol"),
    ("de", "Allemand"),
    ("it", "Italien"),
    ("pt", "Portugais"),
    ("nl", "Néerlandais"),
    ("pl", "Polonais"),
    ("ru", "Russe"),
    ("zh", "Chinois"),
    ("ja", "Japonais"),
    ("ko", "Coréen"),
    ("ar", "Arabe"),
]


class TranscriptionSettingsDialog(tk.Toplevel):
    """Dialogue pour configurer les paramètres de transcription."""

    def __init__(
        self,
        parent,
        current_model: str = "medium",
        current_language: Optional[str] = None,
        show_transcribe_option: bool = False,
        current_show_timestamps: bool = False,
    ):
        """
        Initialise le dialogue.

        Args:
            parent: Fenêtre parente
            current_model: Modèle Whisper actuel
            current_language: Code de langue actuel (None = auto)
            show_transcribe_option: Si True, affiche l'option pour activer/désactiver la transcription
            current_show_timestamps: Si True, affiche les timestamps dans la transcription
        """
        super().__init__(parent)
        self.title("Paramètres de transcription")
        # Ajuster la hauteur pour les nouvelles options
        self.geometry("520x650" if show_transcribe_option else "520x600")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Résultats
        self.result_model = current_model
        self.result_language = current_language
        self.result_transcribe = True
        self.result_show_timestamps = current_show_timestamps
        self.cancelled = True

        # Variables
        self.model_var = tk.StringVar(value=current_model)
        self.language_var = tk.StringVar()
        self.transcribe_var = tk.BooleanVar(value=True)
        self.timestamps_var = tk.BooleanVar(value=current_show_timestamps)
        self.show_transcribe_option = show_transcribe_option

        self._setup_ui()
        self._center_window(parent)

        # Attendre la fermeture
        self.protocol("WM_DELETE_WINDOW", self.cancel)

    def _setup_ui(self):
        """Configure l'interface utilisateur."""
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Option transcription (si demandée)
        if self.show_transcribe_option:
            transcribe_frame = ttk.Frame(main_frame)
            transcribe_frame.pack(fill=tk.X, pady=(0, 15))

            self.transcribe_check = ttk.Checkbutton(
                transcribe_frame,
                text="Transcrire les fichiers audio/vidéo",
                variable=self.transcribe_var,
                command=self._on_transcribe_toggle,
            )
            self.transcribe_check.pack(anchor=tk.W)

            ttk.Label(
                transcribe_frame,
                text="La transcription convertit l'audio en texte consultable",
                foreground="#666666",
                font=("", 9),
            ).pack(anchor=tk.W, padx=(20, 0))

        # Sélection du modèle
        model_label_frame = ttk.Frame(main_frame)
        model_label_frame.pack(fill=tk.X)

        ttk.Label(
            model_label_frame,
            text="Modèle Whisper:",
            font=("", 10, "bold"),
        ).pack(side=tk.LEFT)

        self.download_status = ttk.Label(
            model_label_frame,
            text="",
            foreground="#666666",
            font=("", 9),
        )
        self.download_status.pack(side=tk.RIGHT)

        self.model_frame = ttk.Frame(main_frame)
        self.model_frame.pack(fill=tk.X, pady=(5, 15))

        for model_id, model_label, size in WHISPER_MODELS:
            frame = ttk.Frame(self.model_frame)
            frame.pack(fill=tk.X, pady=1)

            rb = ttk.Radiobutton(
                frame,
                text=model_label,
                value=model_id,
                variable=self.model_var,
            )
            rb.pack(side=tk.LEFT)

            ttk.Label(
                frame,
                text=size,
                foreground="#888888",
                font=("", 9),
            ).pack(side=tk.RIGHT)

        # Sélection de la langue
        ttk.Label(
            main_frame,
            text="Langue:",
            font=("", 10, "bold"),
        ).pack(anchor=tk.W, pady=(10, 0))

        lang_frame = ttk.Frame(main_frame)
        lang_frame.pack(fill=tk.X, pady=5)

        self.lang_combo = ttk.Combobox(
            lang_frame,
            textvariable=self.language_var,
            values=[f"{code} - {name}" for code, name in LANGUAGES],
            state="readonly",
            width=35,
        )
        self.lang_combo.pack(fill=tk.X)

        # Sélectionner la langue actuelle
        current_lang = self.result_language or "auto"
        for i, (code, _) in enumerate(LANGUAGES):
            if code == current_lang:
                self.lang_combo.current(i)
                break
        else:
            self.lang_combo.current(0)

        # Options de formatage
        format_frame = ttk.LabelFrame(main_frame, text="Formatage du texte", padding="10")
        format_frame.pack(fill=tk.X, pady=(15, 0))

        self.timestamps_check = ttk.Checkbutton(
            format_frame,
            text="Afficher les horodatages [00:00 -> 00:05]",
            variable=self.timestamps_var,
        )
        self.timestamps_check.pack(anchor=tk.W)

        ttk.Label(
            format_frame,
            text="Le texte sera automatiquement découpé en paragraphes (un par segment)",
            foreground="#666666",
            font=("", 9),
        ).pack(anchor=tk.W, pady=(5, 0))

        # Informations matérielles
        hw_frame = ttk.LabelFrame(main_frame, text="Matériel détecté", padding="10")
        hw_frame.pack(fill=tk.X, pady=(15, 0))

        self._setup_hardware_info(hw_frame)

        # Note sur le téléchargement
        note_frame = ttk.Frame(main_frame)
        note_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(
            note_frame,
            text="ℹ️ Le modèle sera téléchargé automatiquement si nécessaire.",
            foreground="#666666",
            font=("", 9),
            justify=tk.LEFT,
        ).pack(anchor=tk.W)

        # Barre de progression (cachée par défaut)
        self.progress_frame = ttk.Frame(main_frame)
        self.progress_frame.pack(fill=tk.X, pady=(10, 0))

        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            mode="indeterminate",
        )
        self.progress_label = ttk.Label(
            self.progress_frame,
            text="",
            foreground="#666666",
            font=("", 9),
        )

        # Boutons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(20, 0))

        ttk.Button(btn_frame, text="Annuler", command=self.cancel).pack(side=tk.RIGHT, padx=(5, 0))
        self.ok_btn = ttk.Button(btn_frame, text="OK", command=self.apply)
        self.ok_btn.pack(side=tk.RIGHT)

    def _setup_hardware_info(self, parent_frame):
        """Configure l'affichage des informations matérielles."""
        cuda_info = check_cuda_compatibility()
        system_info = get_system_info()

        # Device utilisé
        device = cuda_info["device"].upper()
        if cuda_info["ready"]:
            device_text = f"✅ {device} - Accélération GPU activée"
            device_color = "#228B22"  # Vert
        else:
            device_text = f"⚠️ {device} - Pas d'accélération GPU"
            device_color = "#CC7000"  # Orange

        device_label = ttk.Label(
            parent_frame,
            text=device_text,
            font=("", 10, "bold"),
        )
        device_label.pack(anchor=tk.W)

        # Détails GPU
        if system_info.has_nvidia_gpu and system_info.gpus:
            gpu = system_info.gpus[0]
            gpu_text = f"GPU: {gpu.name}"
            if gpu.memory_total_mb:
                gpu_text += f" ({gpu.memory_total_mb} MB)"
            ttk.Label(
                parent_frame,
                text=gpu_text,
                foreground="#444444",
                font=("", 9),
            ).pack(anchor=tk.W, padx=(15, 0))

        # PyTorch status
        if system_info.torch_available:
            if system_info.torch_cuda_available:
                torch_text = (
                    f"PyTorch: {system_info.torch_version} (CUDA {system_info.torch_cuda_version})"
                )
                torch_color = "#228B22"
            else:
                torch_text = f"PyTorch: {system_info.torch_version} (CPU uniquement)"
                torch_color = "#CC7000"
        else:
            torch_text = "PyTorch: Non installé"
            torch_color = "#CC0000"

        ttk.Label(
            parent_frame,
            text=torch_text,
            foreground=torch_color,
            font=("", 9),
        ).pack(anchor=tk.W, padx=(15, 0))

        # Avertissement et aide pour installer CUDA
        if system_info.has_nvidia_gpu and not system_info.torch_cuda_available:
            warning_frame = ttk.Frame(parent_frame)
            warning_frame.pack(fill=tk.X, pady=(5, 0))

            ttk.Label(
                warning_frame,
                text="💡 Pour activer le GPU, installez PyTorch avec CUDA:",
                foreground="#666666",
                font=("", 8),
            ).pack(anchor=tk.W)

            # Commande à copier
            cmd = get_pytorch_install_command()
            cmd_text = tk.Text(
                warning_frame,
                height=1,
                font=("Consolas", 8),
                bg="#f0f0f0",
                relief=tk.FLAT,
                wrap=tk.NONE,
            )
            cmd_text.insert("1.0", cmd)
            cmd_text.configure(state=tk.DISABLED)
            cmd_text.pack(fill=tk.X, pady=(2, 0))

    def _on_transcribe_toggle(self):
        """Gère le changement d'état de la case transcription."""
        enabled = self.transcribe_var.get()
        state = tk.NORMAL if enabled else tk.DISABLED

        for child in self.model_frame.winfo_children():
            for widget in child.winfo_children():
                if isinstance(widget, ttk.Radiobutton):
                    widget.configure(state=state)

        self.lang_combo.configure(state="readonly" if enabled else tk.DISABLED)
        self.timestamps_check.configure(state=state)

    def _center_window(self, parent):
        """Centre la fenêtre sur son parent."""
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def apply(self):
        """Applique les paramètres et ferme le dialogue."""
        self.result_model = self.model_var.get()

        # Extraire le code de langue
        lang_selection = self.language_var.get()
        if " - " in lang_selection:
            lang_code = lang_selection.split(" - ")[0]
        else:
            lang_code = lang_selection

        self.result_language = None if lang_code == "auto" else lang_code
        self.result_transcribe = self.transcribe_var.get()
        self.result_show_timestamps = self.timestamps_var.get()
        self.cancelled = False
        self.destroy()

    def cancel(self):
        """Annule et ferme le dialogue."""
        self.cancelled = True
        self.destroy()


class ModelDownloadDialog(tk.Toplevel):
    """Dialogue affichant la progression du téléchargement d'un modèle."""

    def __init__(self, parent, model_name: str):
        super().__init__(parent)
        self.title("Téléchargement du modèle")
        self.geometry("400x150")
        self.resizable(False, False)
        self.transient(parent)

        self.model_name = model_name
        self.download_complete = False
        self.download_error: Optional[str] = None

        self._setup_ui()
        self._center_window(parent)

        # Empêcher la fermeture pendant le téléchargement
        self.protocol("WM_DELETE_WINDOW", lambda: None)

    def _setup_ui(self):
        """Configure l'interface."""
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            main_frame,
            text=f"Téléchargement du modèle '{self.model_name}'...",
            font=("", 10, "bold"),
        ).pack(anchor=tk.W)

        ttk.Label(
            main_frame,
            text="Cette opération peut prendre quelques minutes.\n"
            "L'application reste utilisable pendant le téléchargement.",
            foreground="#666666",
            font=("", 9),
        ).pack(anchor=tk.W, pady=(5, 15))

        self.progress = ttk.Progressbar(main_frame, mode="indeterminate")
        self.progress.pack(fill=tk.X)
        self.progress.start(10)

        self.status_label = ttk.Label(
            main_frame,
            text="Connexion au serveur...",
            foreground="#666666",
        )
        self.status_label.pack(anchor=tk.W, pady=(10, 0))

    def _center_window(self, parent):
        """Centre la fenêtre sur son parent."""
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def update_status(self, message: str):
        """Met à jour le message de statut."""
        self.status_label.configure(text=message)

    def complete(self, success: bool, error: Optional[str] = None):
        """Termine le dialogue."""
        self.download_complete = success
        self.download_error = error
        self.progress.stop()
        self.destroy()


class ImportProgressDialog(tk.Toplevel):
    """Dialogue affichant la progression de l'import de fichiers."""

    def __init__(self, parent, total_files: int = 1):
        super().__init__(parent)
        self.title("Import en cours")
        self.geometry("600x400")
        self.minsize(500, 300)
        self.resizable(True, True)
        self.transient(parent)

        self.total_files = total_files
        self.current_file = 0
        self._cancelled = False

        self._setup_ui()
        self._center_window(parent)

        # Empêcher la fermeture pendant l'import (sauf via Annuler)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_ui(self):
        """Configure l'interface."""
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Titre
        self.title_label = ttk.Label(
            main_frame,
            text="Import des fichiers...",
            font=("", 11, "bold"),
        )
        self.title_label.pack(anchor=tk.W)

        # Fichier en cours
        self.file_label = ttk.Label(
            main_frame,
            text="Préparation...",
            foreground="#333333",
            font=("", 9),
        )
        self.file_label.pack(anchor=tk.W, pady=(10, 5))

        # Progression globale (fichiers)
        files_frame = ttk.Frame(main_frame)
        files_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Label(files_frame, text="Fichiers:", width=12).pack(side=tk.LEFT)
        self.files_progress = ttk.Progressbar(
            files_frame, mode="determinate", maximum=self.total_files
        )
        self.files_progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        self.files_label = ttk.Label(
            main_frame,
            text=f"0 / {self.total_files}",
            foreground="#666666",
            font=("", 9),
        )
        self.files_label.pack(anchor=tk.E)

        # Progression de l'étape actuelle
        step_frame = ttk.Frame(main_frame)
        step_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(step_frame, text="Étape:", width=12).pack(side=tk.LEFT)
        self.step_progress = ttk.Progressbar(step_frame, mode="determinate", maximum=100)
        self.step_progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        # Message d'étape
        self.step_label = ttk.Label(
            main_frame,
            text="En attente...",
            foreground="#666666",
            font=("", 9),
        )
        self.step_label.pack(anchor=tk.W, pady=(5, 0))

        # Zone de log (scrollable)
        log_frame = ttk.LabelFrame(main_frame, text="Détails", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(15, 0))

        # Conteneur pour le texte et la scrollbar
        log_container = ttk.Frame(log_frame)
        log_container.pack(fill=tk.BOTH, expand=True)

        # Scrollbar verticale
        log_scrollbar = ttk.Scrollbar(log_container, orient=tk.VERTICAL)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_text = tk.Text(
            log_container,
            height=8,
            font=("Consolas", 9),
            state=tk.DISABLED,
            wrap=tk.WORD,
            bg="#f8f8f8",
            yscrollcommand=log_scrollbar.set,
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        log_scrollbar.config(command=self.log_text.yview)

        # Bouton Annuler
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(15, 0))

        self.cancel_btn = ttk.Button(btn_frame, text="Annuler", command=self._on_cancel)
        self.cancel_btn.pack(side=tk.RIGHT)

    def _center_window(self, parent):
        """Centre la fenêtre sur son parent."""
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _on_cancel(self):
        """Gère le clic sur Annuler."""
        self._cancelled = True
        self.cancel_btn.configure(state=tk.DISABLED, text="Annulation...")

    def _on_close(self):
        """Gère la tentative de fermeture."""
        self._on_cancel()

    @property
    def cancelled(self) -> bool:
        """Retourne True si l'utilisateur a annulé."""
        return self._cancelled

    def set_file(self, filename: str, file_num: int):
        """Définit le fichier en cours de traitement."""
        self.current_file = file_num
        self.file_label.configure(text=f"📄 {filename}")
        self.files_progress["value"] = file_num - 1
        self.files_label.configure(text=f"{file_num} / {self.total_files}")
        self.step_progress["value"] = 0
        self.update_idletasks()

    def set_step(self, progress: float, message: str):
        """Met à jour la progression de l'étape (0.0 à 1.0)."""
        self.step_progress["value"] = int(progress * 100)
        self.step_label.configure(text=message)
        self.update_idletasks()

    def log(self, message: str):
        """Ajoute un message au log."""
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)
        self.update_idletasks()

    def complete(self, success_count: int, error_count: int):
        """Termine le dialogue avec un résumé."""
        self.title_label.configure(text="Import terminé")
        self.file_label.configure(text="")
        self.files_progress["value"] = self.total_files

        if error_count == 0:
            self.step_label.configure(text=f"✅ {success_count} fichier(s) importé(s) avec succès")
        else:
            self.step_label.configure(text=f"⚠️ {success_count} réussi(s), {error_count} erreur(s)")

        self.step_progress["value"] = 100
        self.cancel_btn.configure(text="Fermer", state=tk.NORMAL, command=self.destroy)


def download_whisper_model_async(
    parent: tk.Tk,
    model_name: str,
    on_complete: Optional[Callable[[bool, Optional[str]], None]] = None,
) -> None:
    """
    Télécharge un modèle Whisper de manière asynchrone.

    Args:
        parent: Fenêtre parente
        model_name: Nom du modèle à télécharger
        on_complete: Callback appelé à la fin (success, error_message)
    """
    dialog = ModelDownloadDialog(parent, model_name)

    def do_download():
        try:
            import whisper

            dialog.after(0, lambda: dialog.update_status("Chargement du modèle..."))

            # Ceci télécharge le modèle s'il n'existe pas
            whisper.load_model(model_name)

            dialog.after(0, lambda: dialog.complete(True))

            if on_complete:
                parent.after(0, lambda: on_complete(True, None))

        except Exception as e:
            error_msg = str(e)
            dialog.after(0, lambda: dialog.complete(False, error_msg))

            if on_complete:
                parent.after(0, lambda: on_complete(False, error_msg))

    thread = threading.Thread(target=do_download, daemon=True)
    thread.start()
