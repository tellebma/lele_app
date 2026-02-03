"""Dialogue de paramètres pour le LLM local (Ollama)."""

import tkinter as tk
from tkinter import ttk
from typing import Optional

from ...analysis.auto_coding import (
    check_ollama_available,
    get_ollama_models,
    download_ollama_model,
    RECOMMENDED_OLLAMA_MODELS,
    EmbeddingEngine,
)


class LLMSettingsDialog(tk.Toplevel):
    """Dialogue pour configurer les paramètres du LLM local."""

    def __init__(
        self,
        parent,
        llm_provider: str = "ollama",
        llm_model: str = "mistral",
        ollama_url: str = "http://localhost:11434",
        embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2",
    ):
        """
        Initialise le dialogue.

        Args:
            parent: Fenêtre parente
            llm_provider: Fournisseur LLM actuel
            llm_model: Modèle LLM actuel
            ollama_url: URL du serveur Ollama
            embedding_model: Modèle d'embeddings actuel
        """
        super().__init__(parent)
        self.title("Paramètres IA / LLM")
        self.geometry("550x600")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Résultats
        self.result_provider = llm_provider
        self.result_model = llm_model
        self.result_ollama_url = ollama_url
        self.result_embedding_model = embedding_model
        self.cancelled = True

        # Variables
        self.provider_var = tk.StringVar(value=llm_provider)
        self.model_var = tk.StringVar(value=llm_model)
        self.url_var = tk.StringVar(value=ollama_url)
        self.embedding_var = tk.StringVar(value=embedding_model)

        self._setup_ui()
        self._check_ollama_status()
        self._center_window(parent)

        self.protocol("WM_DELETE_WINDOW", self.cancel)

    def _setup_ui(self):
        """Configure l'interface utilisateur."""
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # === Section LLM ===
        llm_frame = ttk.LabelFrame(main_frame, text="LLM pour le nommage des thèmes", padding="10")
        llm_frame.pack(fill=tk.X, pady=(0, 15))

        # Provider
        ttk.Label(llm_frame, text="Fournisseur:").pack(anchor=tk.W)

        for value, label, desc in [
            ("ollama", "Ollama (local)", "LLM gratuit, fonctionne hors ligne"),
            ("none", "Mots-clés uniquement", "Pas de LLM, extraction par fréquence"),
        ]:
            frame = ttk.Frame(llm_frame)
            frame.pack(fill=tk.X, padx=(10, 0), pady=1)

            ttk.Radiobutton(
                frame,
                text=label,
                value=value,
                variable=self.provider_var,
                command=self._on_provider_change,
            ).pack(side=tk.LEFT)

            ttk.Label(
                frame,
                text=f"— {desc}",
                foreground="#888888",
                font=("", 8),
            ).pack(side=tk.LEFT, padx=(5, 0))

        # URL Ollama
        self.ollama_config_frame = ttk.Frame(llm_frame)
        self.ollama_config_frame.pack(fill=tk.X, pady=(10, 0))

        url_frame = ttk.Frame(self.ollama_config_frame)
        url_frame.pack(fill=tk.X)

        ttk.Label(url_frame, text="URL Ollama:").pack(side=tk.LEFT)
        ttk.Entry(
            url_frame,
            textvariable=self.url_var,
            width=30,
        ).pack(side=tk.LEFT, padx=(10, 0))

        ttk.Button(
            url_frame,
            text="Tester",
            command=self._test_ollama_connection,
            width=8,
        ).pack(side=tk.LEFT, padx=(5, 0))

        # Status Ollama
        self.ollama_status = ttk.Label(
            self.ollama_config_frame,
            text="",
            font=("", 9),
        )
        self.ollama_status.pack(anchor=tk.W, pady=(5, 0))

        # Modèle Ollama
        model_frame = ttk.Frame(self.ollama_config_frame)
        model_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(model_frame, text="Modèle:").pack(side=tk.LEFT)
        self.model_combo = ttk.Combobox(
            model_frame,
            textvariable=self.model_var,
            width=20,
        )
        self.model_combo.pack(side=tk.LEFT, padx=(10, 0))

        ttk.Button(
            model_frame,
            text="🔄",
            width=3,
            command=self._refresh_models,
        ).pack(side=tk.LEFT, padx=(5, 0))

        # Liste des modèles recommandés
        ttk.Label(
            self.ollama_config_frame,
            text="Modèles recommandés:",
            font=("", 9, "bold"),
        ).pack(anchor=tk.W, pady=(15, 5))

        for model_info in RECOMMENDED_OLLAMA_MODELS[:4]:
            model_item = ttk.Frame(self.ollama_config_frame)
            model_item.pack(fill=tk.X, padx=(10, 0), pady=1)

            ttk.Label(
                model_item,
                text=f"• {model_info['display_name']}",
                font=("", 9),
            ).pack(side=tk.LEFT)

            ttk.Label(
                model_item,
                text=f"({model_info['size_gb']} GB) — {model_info['description']}",
                foreground="#888888",
                font=("", 8),
            ).pack(side=tk.LEFT, padx=(5, 0))

        # Note d'installation
        install_note = ttk.Label(
            self.ollama_config_frame,
            text="💡 Installez Ollama depuis ollama.ai puis lancez: ollama pull mistral",
            foreground="#666666",
            font=("", 8),
        )
        install_note.pack(anchor=tk.W, pady=(10, 0))

        # === Section Embeddings ===
        embed_frame = ttk.LabelFrame(
            main_frame, text="Modèle d'embeddings (vectorisation)", padding="10"
        )
        embed_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(embed_frame, text="Modèle sentence-transformers:").pack(anchor=tk.W)

        embed_combo_frame = ttk.Frame(embed_frame)
        embed_combo_frame.pack(fill=tk.X, pady=(5, 0))

        available_models = EmbeddingEngine.get_available_models()
        model_choices = [m["id"] for m in available_models]

        self.embed_combo = ttk.Combobox(
            embed_combo_frame,
            textvariable=self.embedding_var,
            values=model_choices,
            state="readonly",
            width=45,
        )
        self.embed_combo.pack(side=tk.LEFT)

        # Info sur le modèle sélectionné
        self.embed_info = ttk.Label(
            embed_frame,
            text="",
            foreground="#666666",
            font=("", 9),
        )
        self.embed_info.pack(anchor=tk.W, pady=(5, 0))

        self.embed_combo.bind("<<ComboboxSelected>>", self._on_embed_model_change)
        self._on_embed_model_change(None)

        # === Info matériel ===
        hw_frame = ttk.LabelFrame(main_frame, text="Matériel détecté", padding="10")
        hw_frame.pack(fill=tk.X, pady=(0, 15))

        self._setup_hardware_info(hw_frame)

        # === Boutons ===
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(btn_frame, text="Annuler", command=self.cancel).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(btn_frame, text="OK", command=self.apply).pack(side=tk.RIGHT)

    def _setup_hardware_info(self, parent):
        """Configure l'affichage des informations matérielles."""
        from ...analysis.auto_coding import check_torch_device

        device_info = check_torch_device()

        if device_info["cuda"]:
            device_text = f"✅ GPU NVIDIA: {device_info['cuda_device_name']}"
            device_color = "#228B22"
        elif device_info["mps"]:
            device_text = "✅ GPU Apple Silicon (MPS)"
            device_color = "#228B22"
        else:
            device_text = "⚠️ CPU uniquement (embeddings plus lents)"
            device_color = "#CC7000"

        ttk.Label(
            parent,
            text=device_text,
            foreground=device_color,
            font=("", 9),
        ).pack(anchor=tk.W)

        ttk.Label(
            parent,
            text=f"Device recommandé: {device_info['recommended'].upper()}",
            foreground="#666666",
            font=("", 8),
        ).pack(anchor=tk.W, padx=(10, 0))

    def _check_ollama_status(self):
        """Vérifie le statut d'Ollama."""
        available, message = check_ollama_available(self.url_var.get())

        if available:
            self.ollama_status.configure(
                text=f"✅ {message}",
                foreground="#228B22",
            )
            self._refresh_models()
        else:
            self.ollama_status.configure(
                text=f"❌ {message}",
                foreground="#CC0000",
            )
            self.model_combo["values"] = ["mistral", "llama2", "phi"]

        self._on_provider_change()

    def _test_ollama_connection(self):
        """Teste la connexion à Ollama."""
        self.ollama_status.configure(text="⏳ Test en cours...", foreground="#666666")
        self.update_idletasks()

        available, message = check_ollama_available(self.url_var.get())

        if available:
            self.ollama_status.configure(
                text=f"✅ {message}",
                foreground="#228B22",
            )
            self._refresh_models()
        else:
            self.ollama_status.configure(
                text=f"❌ {message}",
                foreground="#CC0000",
            )

    def _refresh_models(self):
        """Rafraîchit la liste des modèles Ollama."""
        models = get_ollama_models(self.url_var.get())
        if models:
            self.model_combo["values"] = models
            if self.model_var.get() not in models and models:
                self.model_var.set(models[0])
        else:
            self.model_combo["values"] = ["mistral", "llama2", "phi", "gemma:2b"]

    def _on_provider_change(self):
        """Gère le changement de provider."""
        if self.provider_var.get() == "ollama":
            for child in self.ollama_config_frame.winfo_children():
                self._enable_widget(child)
        else:
            for child in self.ollama_config_frame.winfo_children():
                self._disable_widget(child)

    def _enable_widget(self, widget):
        """Active un widget et ses enfants."""
        try:
            widget.configure(state=tk.NORMAL)
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            self._enable_widget(child)

    def _disable_widget(self, widget):
        """Désactive un widget et ses enfants."""
        try:
            widget.configure(state=tk.DISABLED)
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            self._disable_widget(child)

    def _on_embed_model_change(self, event):
        """Met à jour l'info du modèle d'embeddings."""
        model_id = self.embedding_var.get()
        available_models = EmbeddingEngine.get_available_models()

        for model in available_models:
            if model["id"] == model_id:
                self.embed_info.configure(
                    text=f"{model['name']} — {model['size_mb']} MB — {model['description']}"
                )
                break

    def _center_window(self, parent):
        """Centre la fenêtre sur son parent."""
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def apply(self):
        """Applique les paramètres."""
        self.result_provider = self.provider_var.get()
        self.result_model = self.model_var.get()
        self.result_ollama_url = self.url_var.get()
        self.result_embedding_model = self.embedding_var.get()
        self.cancelled = False
        self.destroy()

    def cancel(self):
        """Annule et ferme."""
        self.cancelled = True
        self.destroy()
