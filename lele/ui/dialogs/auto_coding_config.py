"""Dialogue de configuration pour la détection automatique de nœuds."""

import threading
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from ...analysis.auto_coding import (
    AutoCodingConfig,
    LLMProvider,
    SegmentationStrategy,
    check_dependencies,
    check_ollama_available,
    get_ollama_models,
    EmbeddingEngine,
)


class AutoCodingConfigDialog(tk.Toplevel):
    """Dialogue pour configurer l'analyse automatique de nœuds."""

    def __init__(
        self,
        parent,
        sources: list[dict],
        existing_nodes: list[dict] | None = None,
        settings: dict | None = None,
    ):
        """
        Initialise le dialogue.

        Args:
            parent: Fenêtre parente
            sources: Liste des sources disponibles [{'id', 'name', 'type'}]
            existing_nodes: Liste des nœuds existants [{'id', 'name'}]
            settings: Paramètres sauvegardés précédemment
        """
        super().__init__(parent)
        self.title("Détection automatique de nœuds")
        # Taille plus grande par défaut
        self.geometry("650x750")
        self.minsize(600, 700)
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self.sources = sources
        self.existing_nodes = existing_nodes or []
        self.settings = settings or {}

        # Résultat
        self.result_config: Optional[AutoCodingConfig] = None
        self.result_sources: list[dict] = []
        self.cancelled = True

        # Variables
        self._setup_variables()
        self._setup_ui()
        self._check_dependencies()
        self._center_window(parent)

        self.protocol("WM_DELETE_WINDOW", self.cancel)

    def _setup_variables(self):
        """Initialise les variables Tkinter."""
        # Sources sélectionnées
        self.source_vars: dict[str, tk.BooleanVar] = {}
        for source in self.sources:
            var = tk.BooleanVar(value=True)
            self.source_vars[source["id"]] = var

        # Segmentation
        self.segmentation_var = tk.StringVar(
            value=self.settings.get("segmentation", "paragraph")
        )

        # Clustering
        self.max_themes_var = tk.IntVar(
            value=self.settings.get("max_themes", 15)
        )
        self.min_cluster_var = tk.IntVar(
            value=self.settings.get("min_cluster_size", 3)
        )
        self.confidence_var = tk.DoubleVar(
            value=self.settings.get("confidence_threshold", 0.6)
        )

        # LLM
        self.llm_provider_var = tk.StringVar(
            value=self.settings.get("llm_provider", "ollama")
        )
        self.llm_model_var = tk.StringVar(
            value=self.settings.get("llm_model", "mistral")
        )

        # Options
        self.exclude_coded_var = tk.BooleanVar(
            value=self.settings.get("exclude_coded", True)
        )
        self.merge_similar_var = tk.BooleanVar(
            value=self.settings.get("merge_similar", True)
        )

        # État avancé
        self.show_advanced = tk.BooleanVar(value=False)

    def _setup_ui(self):
        """Configure l'interface utilisateur."""
        # Obtenir la couleur de fond du style ttk (coherent avec les autres dialogues)
        style = ttk.Style()
        bg_color = style.lookup("TFrame", "background") or "#f0f0f0"

        # Frame principal avec scrollbar
        self._canvas = tk.Canvas(self, highlightthickness=0, bg=bg_color)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self.main_frame = tk.Frame(self._canvas, bg=bg_color, padx=20, pady=20)

        self.main_frame.bind(
            "<Configure>",
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        )

        self._window_id = self._canvas.create_window((0, 0), window=self.main_frame, anchor="nw")
        self._canvas.configure(yscrollcommand=scrollbar.set)

        # Pack canvas et scrollbar
        self._canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Etendre le main_frame sur toute la largeur du canvas
        def _on_canvas_configure(event):
            self._canvas.itemconfig(self._window_id, width=event.width)
        self._canvas.bind("<Configure>", _on_canvas_configure)

        # Binding molette souris - avec vérification que le widget existe encore
        self._mousewheel_bound = False

        def _on_mousewheel(event):
            # Vérifier que le canvas existe encore avant de scroller
            try:
                if self._canvas.winfo_exists():
                    self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except tk.TclError:
                pass

        def _bind_mousewheel(event):
            if not self._mousewheel_bound:
                self.bind_all("<MouseWheel>", _on_mousewheel)
                self._mousewheel_bound = True

        def _unbind_mousewheel(event):
            if self._mousewheel_bound:
                try:
                    self.unbind_all("<MouseWheel>")
                except tk.TclError:
                    pass
                self._mousewheel_bound = False

        self._unbind_mousewheel_func = _unbind_mousewheel

        self._canvas.bind("<Enter>", _bind_mousewheel)
        self._canvas.bind("<Leave>", _unbind_mousewheel)
        self.main_frame.bind("<Enter>", _bind_mousewheel)
        self.main_frame.bind("<Leave>", _unbind_mousewheel)

        # === Section Sources ===
        self._setup_sources_section()

        # === Section Paramètres de base ===
        self._setup_basic_params_section()

        # === Section LLM ===
        self._setup_llm_section()

        # === Section Avancé (toggle) ===
        self._setup_advanced_section()

        # === État des dépendances ===
        self._setup_dependencies_section()

        # === Boutons ===
        self._setup_buttons()

    def _setup_sources_section(self):
        """Configure la section de sélection des sources."""
        frame = ttk.LabelFrame(
            self.main_frame, text="Sources à analyser", padding="10"
        )
        frame.pack(fill=tk.X, pady=(0, 15))

        # Liste des sources avec checkboxes
        sources_container = ttk.Frame(frame)
        sources_container.pack(fill=tk.X)

        # Limiter la hauteur si beaucoup de sources
        max_visible = 6
        if len(self.sources) > max_visible:
            # Créer un canvas scrollable
            canvas = tk.Canvas(sources_container, height=150, highlightthickness=0)
            scrollbar = ttk.Scrollbar(
                sources_container, orient="vertical", command=canvas.yview
            )
            sources_frame = ttk.Frame(canvas)

            sources_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            canvas.create_window((0, 0), window=sources_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
        else:
            sources_frame = sources_container

        # Ajouter les checkboxes
        for source in self.sources:
            source_frame = ttk.Frame(sources_frame)
            source_frame.pack(fill=tk.X, pady=1)

            cb = ttk.Checkbutton(
                source_frame,
                text=source["name"],
                variable=self.source_vars[source["id"]],
            )
            cb.pack(side=tk.LEFT)

            # Type de source
            ttk.Label(
                source_frame,
                text=source.get("type", ""),
                foreground="#888888",
                font=("", 8),
            ).pack(side=tk.RIGHT)

        # Boutons tout/rien
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(
            btn_frame, text="Tout sélectionner", command=self._select_all_sources
        ).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(
            btn_frame, text="Aucun", command=self._deselect_all_sources
        ).pack(side=tk.LEFT)

        # Compteur
        self.sources_count_label = ttk.Label(
            btn_frame,
            text=f"{len(self.sources)} source(s) sélectionnée(s)",
            foreground="#666666",
        )
        self.sources_count_label.pack(side=tk.RIGHT)

    def _setup_basic_params_section(self):
        """Configure la section des paramètres de base."""
        frame = ttk.LabelFrame(
            self.main_frame, text="Paramètres de découpage", padding="10"
        )
        frame.pack(fill=tk.X, pady=(0, 15))

        # Granularité
        ttk.Label(frame, text="Granularité de découpage:").pack(anchor=tk.W)

        for value, label, desc in [
            ("paragraph", "Paragraphe", "Recommandé pour entretiens"),
            ("sentence", "Phrase", "Pour textes denses"),
            ("window", "Fenêtre glissante (200 mots)", "Pour textes longs"),
        ]:
            rb_frame = ttk.Frame(frame)
            rb_frame.pack(fill=tk.X, padx=(10, 0), pady=1)

            ttk.Radiobutton(
                rb_frame,
                text=label,
                value=value,
                variable=self.segmentation_var,
            ).pack(side=tk.LEFT)

            ttk.Label(
                rb_frame,
                text=f"({desc})",
                foreground="#888888",
                font=("", 8),
            ).pack(side=tk.LEFT, padx=(5, 0))

        # Nombre max de thèmes
        themes_frame = ttk.Frame(frame)
        themes_frame.pack(fill=tk.X, pady=(15, 0))

        ttk.Label(themes_frame, text="Nombre max de thèmes:").pack(side=tk.LEFT)
        themes_spin = ttk.Spinbox(
            themes_frame,
            from_=5,
            to=50,
            textvariable=self.max_themes_var,
            width=5,
        )
        themes_spin.pack(side=tk.LEFT, padx=(10, 0))

    def _setup_llm_section(self):
        """Configure la section LLM pour le nommage."""
        frame = ttk.LabelFrame(
            self.main_frame, text="Nommage des thèmes (LLM)", padding="10"
        )
        frame.pack(fill=tk.X, pady=(0, 15))

        # Provider
        ttk.Label(frame, text="Fournisseur:").pack(anchor=tk.W)

        providers_frame = ttk.Frame(frame)
        providers_frame.pack(fill=tk.X, padx=(10, 0))

        for value, label in [
            ("ollama", "Ollama (local)"),
            ("none", "Mots-clés uniquement (pas de LLM)"),
        ]:
            ttk.Radiobutton(
                providers_frame,
                text=label,
                value=value,
                variable=self.llm_provider_var,
                command=self._on_provider_change,
            ).pack(anchor=tk.W, pady=1)

        # Modèle Ollama
        self.ollama_frame = ttk.Frame(frame)
        self.ollama_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(self.ollama_frame, text="Modèle Ollama:").pack(side=tk.LEFT)

        self.ollama_combo = ttk.Combobox(
            self.ollama_frame,
            textvariable=self.llm_model_var,
            width=20,
        )
        self.ollama_combo.pack(side=tk.LEFT, padx=(10, 0))

        # Bouton rafraîchir
        self.refresh_btn = ttk.Button(
            self.ollama_frame,
            text="🔄",
            width=3,
            command=self._refresh_ollama_models,
        )
        self.refresh_btn.pack(side=tk.LEFT, padx=(5, 0))

        # Status Ollama
        self.ollama_status = ttk.Label(
            frame,
            text="",
            foreground="#666666",
            font=("", 9),
        )
        self.ollama_status.pack(anchor=tk.W, pady=(5, 0))

    def _setup_advanced_section(self):
        """Configure la section des paramètres avancés."""
        # Toggle
        toggle_frame = ttk.Frame(self.main_frame)
        toggle_frame.pack(fill=tk.X, pady=(0, 10))

        self.advanced_toggle = ttk.Checkbutton(
            toggle_frame,
            text="▸ Paramètres avancés",
            variable=self.show_advanced,
            command=self._toggle_advanced,
        )
        self.advanced_toggle.pack(anchor=tk.W)

        # Frame avancé (caché par défaut)
        self.advanced_frame = ttk.LabelFrame(
            self.main_frame, text="Paramètres avancés", padding="10"
        )

        # Taille minimum cluster
        cluster_frame = ttk.Frame(self.advanced_frame)
        cluster_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(cluster_frame, text="Taille min. d'un cluster:").pack(side=tk.LEFT)
        ttk.Spinbox(
            cluster_frame,
            from_=2,
            to=10,
            textvariable=self.min_cluster_var,
            width=5,
        ).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Label(
            cluster_frame,
            text="(segments)",
            foreground="#888888",
        ).pack(side=tk.LEFT, padx=(5, 0))

        # Seuil de confiance
        conf_frame = ttk.Frame(self.advanced_frame)
        conf_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(conf_frame, text="Seuil de confiance min.:").pack(side=tk.LEFT)
        conf_scale = ttk.Scale(
            conf_frame,
            from_=0.3,
            to=0.9,
            variable=self.confidence_var,
            orient=tk.HORIZONTAL,
            length=150,
        )
        conf_scale.pack(side=tk.LEFT, padx=(10, 0))
        self.conf_label = ttk.Label(
            conf_frame,
            text=f"{self.confidence_var.get():.2f}",
            width=5,
        )
        self.conf_label.pack(side=tk.LEFT, padx=(5, 0))

        # Mettre à jour le label quand le slider change
        def update_conf_label(*args):
            self.conf_label.configure(text=f"{self.confidence_var.get():.2f}")
        self.confidence_var.trace_add("write", update_conf_label)

        # Options
        ttk.Checkbutton(
            self.advanced_frame,
            text="Exclure les segments déjà codés",
            variable=self.exclude_coded_var,
        ).pack(anchor=tk.W, pady=2)

        ttk.Checkbutton(
            self.advanced_frame,
            text="Fusionner automatiquement les thèmes similaires",
            variable=self.merge_similar_var,
        ).pack(anchor=tk.W, pady=2)

    def _setup_dependencies_section(self):
        """Configure la section d'état des dépendances."""
        self.deps_frame = ttk.LabelFrame(
            self.main_frame, text="État du système", padding="10"
        )
        self.deps_frame.pack(fill=tk.X, pady=(0, 15))

        self.deps_label = ttk.Label(
            self.deps_frame,
            text="Vérification des dépendances...",
            foreground="#666666",
        )
        self.deps_label.pack(anchor=tk.W)

    def _setup_buttons(self):
        """Configure les boutons d'action."""
        btn_frame = ttk.Frame(self.main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(btn_frame, text="Annuler", command=self.cancel).pack(
            side=tk.RIGHT, padx=(5, 0)
        )

        self.analyze_btn = ttk.Button(
            btn_frame, text="▶ Analyser", command=self.apply
        )
        self.analyze_btn.pack(side=tk.RIGHT)

    def _check_dependencies(self):
        """Vérifie les dépendances de manière asynchrone."""
        # Afficher un message de chargement
        self.deps_label.configure(text="Vérification en cours...")
        self.ollama_status.configure(text="Vérification d'Ollama...", foreground="#666666")

        # Lancer la vérification dans un thread séparé
        thread = threading.Thread(target=self._check_dependencies_async, daemon=True)
        thread.start()

    def _check_dependencies_async(self):
        """Thread de vérification des dépendances."""
        try:
            deps = check_dependencies()
            # Mettre à jour l'UI depuis le thread principal
            self.after(0, lambda: self._update_dependencies_ui(deps))
        except Exception as e:
            self.after(0, lambda: self._show_dependency_error(str(e)))

    def _update_dependencies_ui(self, deps: dict):
        """Met à jour l'UI avec les résultats de vérification."""
        try:
            # Vérifier que le widget existe encore
            if not self.winfo_exists():
                return

            lines = []
            all_ok = True

            # Sentence-transformers
            st = deps["sentence_transformers"]
            if st["available"]:
                lines.append(f"✅ {st['message']}")
            else:
                lines.append(f"❌ {st['message']}")
                all_ok = False

            # Clustering
            cl = deps["clustering"]
            if cl["available"]:
                lines.append(f"✅ {cl['message']}")
            else:
                lines.append(f"❌ {cl['message']}")
                all_ok = False

            # Device
            device = deps["torch_device"]
            if device["cuda"]:
                lines.append(f"✅ GPU: {device['cuda_device_name']}")
            elif device["mps"]:
                lines.append("✅ GPU: Apple Silicon (MPS)")
            else:
                lines.append("⚠️ CPU uniquement (pas de GPU)")

            # Ollama
            ol = deps["ollama"]
            if ol["available"]:
                self.ollama_status.configure(
                    text=f"✅ {ol['message']}", foreground="#228B22"
                )
                # Rafraîchir les modèles Ollama de manière asynchrone
                self._refresh_ollama_models()
            else:
                self.ollama_status.configure(
                    text=f"⚠️ {ol['message']}", foreground="#CC7000"
                )

            self.deps_label.configure(text="\n".join(lines))

            # Désactiver le bouton si dépendances manquantes
            if not all_ok:
                self.analyze_btn.configure(state=tk.DISABLED)

        except tk.TclError:
            # Le widget a été détruit entre-temps
            pass

    def _show_dependency_error(self, error: str):
        """Affiche une erreur de vérification des dépendances."""
        try:
            if not self.winfo_exists():
                return
            self.deps_label.configure(
                text=f"❌ Erreur: {error}",
                foreground="#CC0000",
            )
            self.analyze_btn.configure(state=tk.DISABLED)
        except tk.TclError:
            pass

    def _refresh_ollama_models(self):
        """Rafraîchit la liste des modèles Ollama de manière asynchrone."""
        # Lancer la récupération dans un thread séparé
        thread = threading.Thread(target=self._refresh_ollama_models_async, daemon=True)
        thread.start()

    def _refresh_ollama_models_async(self):
        """Thread de récupération des modèles Ollama."""
        try:
            models = get_ollama_models()
            self.after(0, lambda: self._update_ollama_models_ui(models))
        except Exception:
            self.after(0, lambda: self._update_ollama_models_ui(None))

    def _update_ollama_models_ui(self, models: list | None):
        """Met à jour l'UI avec la liste des modèles Ollama."""
        try:
            if not self.winfo_exists():
                return

            if models:
                self.ollama_combo["values"] = models
                if self.llm_model_var.get() not in models:
                    self.llm_model_var.set(models[0])
            else:
                self.ollama_combo["values"] = ["mistral", "llama2", "phi"]
        except tk.TclError:
            pass

    def _on_provider_change(self):
        """Gère le changement de provider LLM."""
        provider = self.llm_provider_var.get()
        if provider == "ollama":
            for child in self.ollama_frame.winfo_children():
                child.configure(state=tk.NORMAL)
        else:
            for child in self.ollama_frame.winfo_children():
                if isinstance(child, (ttk.Combobox, ttk.Button)):
                    child.configure(state=tk.DISABLED)

    def _toggle_advanced(self):
        """Affiche/masque les paramètres avancés."""
        if self.show_advanced.get():
            self.advanced_toggle.configure(text="▾ Paramètres avancés")
            self.advanced_frame.pack(fill=tk.X, pady=(0, 15), after=self.advanced_toggle.master)
        else:
            self.advanced_toggle.configure(text="▸ Paramètres avancés")
            self.advanced_frame.pack_forget()

    def _select_all_sources(self):
        """Sélectionne toutes les sources."""
        for var in self.source_vars.values():
            var.set(True)
        self._update_sources_count()

    def _deselect_all_sources(self):
        """Désélectionne toutes les sources."""
        for var in self.source_vars.values():
            var.set(False)
        self._update_sources_count()

    def _update_sources_count(self):
        """Met à jour le compteur de sources."""
        count = sum(1 for var in self.source_vars.values() if var.get())
        self.sources_count_label.configure(
            text=f"{count} source(s) sélectionnée(s)"
        )

    def _center_window(self, parent):
        """Centre la fenêtre sur son parent."""
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def apply(self):
        """Applique la configuration et lance l'analyse."""
        # Récupérer les sources sélectionnées
        selected_ids = [
            sid for sid, var in self.source_vars.items() if var.get()
        ]

        if not selected_ids:
            tk.messagebox.showwarning(
                "Aucune source",
                "Veuillez sélectionner au moins une source à analyser.",
                parent=self,
            )
            return

        # Mapper la stratégie
        strategy_map = {
            "paragraph": SegmentationStrategy.PARAGRAPH,
            "sentence": SegmentationStrategy.SENTENCE,
            "window": SegmentationStrategy.FIXED_WINDOW,
        }

        # Mapper le provider
        provider_map = {
            "ollama": LLMProvider.LOCAL_OLLAMA,
            "none": LLMProvider.NONE,
        }

        # Construire la config
        self.result_config = AutoCodingConfig(
            source_ids=selected_ids,
            segmentation_strategy=strategy_map.get(
                self.segmentation_var.get(), SegmentationStrategy.PARAGRAPH
            ),
            max_themes=self.max_themes_var.get(),
            min_cluster_size=self.min_cluster_var.get(),
            confidence_threshold=self.confidence_var.get(),
            llm_provider=provider_map.get(
                self.llm_provider_var.get(), LLMProvider.LOCAL_OLLAMA
            ),
            llm_model=self.llm_model_var.get(),
            exclude_already_coded=self.exclude_coded_var.get(),
            merge_similar_themes=self.merge_similar_var.get(),
        )

        # Récupérer les sources complètes
        self.result_sources = [
            s for s in self.sources if s["id"] in selected_ids
        ]

        self.cancelled = False
        self._cleanup_bindings()
        self.destroy()

    def cancel(self):
        """Annule et ferme le dialogue."""
        self.cancelled = True
        self._cleanup_bindings()
        self.destroy()

    def _cleanup_bindings(self):
        """Nettoie les bindings globaux avant fermeture."""
        try:
            if hasattr(self, "_mousewheel_bound") and self._mousewheel_bound:
                self.unbind_all("<MouseWheel>")
                self._mousewheel_bound = False
        except tk.TclError:
            pass
