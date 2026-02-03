"""Dialogue de prévisualisation des résultats d'auto-codage."""

import tkinter as tk
from tkinter import ttk, simpledialog
from typing import Optional

from ...analysis.auto_coding import AutoCodingResult, NodeProposal, get_theme_color


class AutoCodingPreviewDialog(tk.Toplevel):
    """Dialogue pour prévisualiser et valider les thèmes détectés."""

    def __init__(self, parent, result: AutoCodingResult):
        """
        Initialise le dialogue.

        Args:
            parent: Fenêtre parente
            result: Résultat de l'analyse d'auto-codage
        """
        super().__init__(parent)
        self.title("Résultats de détection automatique")
        self.geometry("900x700")
        self.minsize(800, 600)
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self.result = result
        self.selected_proposal: Optional[NodeProposal] = None

        # Résultat
        self.approved = False

        self._setup_ui()
        self._populate_proposals()
        self._center_window(parent)

        self.protocol("WM_DELETE_WINDOW", self.cancel)

    def _setup_ui(self):
        """Configure l'interface utilisateur."""
        # Header avec statistiques
        self._setup_header()

        # Panneau principal divisé
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Panel gauche: liste des thèmes
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        self._setup_proposals_list(left_frame)

        # Panel droit: détails du thème
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)
        self._setup_details_panel(right_frame)

        # Footer avec boutons
        self._setup_footer()

    def _setup_header(self):
        """Configure l'en-tête avec les statistiques."""
        header = ttk.Frame(self, padding="15")
        header.pack(fill=tk.X)

        # Titre
        ttk.Label(
            header,
            text="🔮 Thèmes détectés",
            font=("", 14, "bold"),
        ).pack(side=tk.LEFT)

        # Stats
        stats_frame = ttk.Frame(header)
        stats_frame.pack(side=tk.RIGHT)

        n_proposals = len(self.result.proposals)
        n_segments = self.result.clustered_segments
        n_noise = self.result.noise_segments
        coverage = self.result.coverage_percentage

        stats_text = (
            f"{n_proposals} thèmes · "
            f"{n_segments} segments classés · "
            f"{n_noise} non classés · "
            f"Couverture: {coverage:.0f}%"
        )

        ttk.Label(
            stats_frame,
            text=stats_text,
            foreground="#666666",
        ).pack(side=tk.LEFT)

    def _setup_proposals_list(self, parent):
        """Configure la liste des propositions de thèmes."""
        # Label
        ttk.Label(
            parent,
            text="THÈMES PROPOSÉS",
            font=("", 9, "bold"),
        ).pack(anchor=tk.W, pady=(0, 5))

        # Frame pour la liste
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True)

        # Treeview
        columns = ("name", "segments", "confidence", "status")
        self.proposals_tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="tree headings",
            selectmode="browse",
        )

        # Colonnes
        self.proposals_tree.heading("#0", text="")
        self.proposals_tree.heading("name", text="Thème")
        self.proposals_tree.heading("segments", text="Segments")
        self.proposals_tree.heading("confidence", text="Confiance")
        self.proposals_tree.heading("status", text="État")

        self.proposals_tree.column("#0", width=30, stretch=False)
        self.proposals_tree.column("name", width=180, minwidth=100)
        self.proposals_tree.column("segments", width=70, anchor=tk.CENTER)
        self.proposals_tree.column("confidence", width=80, anchor=tk.CENTER)
        self.proposals_tree.column("status", width=100, anchor=tk.CENTER)

        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.proposals_tree.yview)
        self.proposals_tree.configure(yscrollcommand=scrollbar.set)

        self.proposals_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind sélection
        self.proposals_tree.bind("<<TreeviewSelect>>", self._on_proposal_select)
        self.proposals_tree.bind("<Double-1>", self._on_double_click)

        # Boutons d'action
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(btn_frame, text="✓ Tout", width=8, command=self._select_all).pack(
            side=tk.LEFT, padx=(0, 5)
        )

        ttk.Button(btn_frame, text="✗ Aucun", width=8, command=self._deselect_all).pack(
            side=tk.LEFT, padx=(0, 5)
        )

        ttk.Button(btn_frame, text="✏ Renommer", width=10, command=self._rename_selected).pack(
            side=tk.LEFT
        )

    def _setup_details_panel(self, parent):
        """Configure le panneau de détails."""
        # Nom du thème
        self.detail_name = ttk.Label(
            parent,
            text="Sélectionnez un thème",
            font=("", 12, "bold"),
        )
        self.detail_name.pack(anchor=tk.W, pady=(0, 5))

        # Description
        self.detail_desc = ttk.Label(
            parent,
            text="",
            foreground="#666666",
            wraplength=350,
        )
        self.detail_desc.pack(anchor=tk.W, pady=(0, 10))

        # Mots-clés
        keywords_frame = ttk.Frame(parent)
        keywords_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            keywords_frame,
            text="Mots-clés:",
            font=("", 9, "bold"),
        ).pack(side=tk.LEFT)

        self.detail_keywords = ttk.Label(
            keywords_frame,
            text="",
            foreground="#3498db",
        )
        self.detail_keywords.pack(side=tk.LEFT, padx=(5, 0))

        # Info nœud existant
        self.existing_frame = ttk.Frame(parent)
        self.existing_frame.pack(fill=tk.X, pady=(0, 10))

        self.existing_label = ttk.Label(
            self.existing_frame,
            text="",
            foreground="#CC7000",
        )
        self.existing_label.pack(anchor=tk.W)

        # Liste des segments
        ttk.Label(
            parent,
            text="SEGMENTS:",
            font=("", 9, "bold"),
        ).pack(anchor=tk.W, pady=(10, 5))

        # Frame pour la liste des segments
        segments_frame = ttk.Frame(parent)
        segments_frame.pack(fill=tk.BOTH, expand=True)

        # Text widget pour les segments
        self.segments_text = tk.Text(
            segments_frame,
            wrap=tk.WORD,
            font=("", 9),
            bg="#f8f8f8",
            state=tk.DISABLED,
            height=15,
        )

        seg_scrollbar = ttk.Scrollbar(
            segments_frame, orient=tk.VERTICAL, command=self.segments_text.yview
        )
        self.segments_text.configure(yscrollcommand=seg_scrollbar.set)

        self.segments_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        seg_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Tags pour le formatage
        self.segments_text.tag_configure("source", foreground="#888888", font=("", 8))
        self.segments_text.tag_configure("text", font=("", 9))
        self.segments_text.tag_configure("separator", foreground="#cccccc")

    def _setup_footer(self):
        """Configure le footer avec les boutons."""
        footer = ttk.Frame(self, padding="15")
        footer.pack(fill=tk.X, side=tk.BOTTOM)

        # Résumé
        self.summary_label = ttk.Label(
            footer,
            text="",
            foreground="#666666",
        )
        self.summary_label.pack(side=tk.LEFT)

        # Boutons
        ttk.Button(footer, text="Annuler", command=self.cancel).pack(side=tk.RIGHT, padx=(5, 0))

        self.apply_btn = ttk.Button(footer, text="✓ Appliquer", command=self.apply)
        self.apply_btn.pack(side=tk.RIGHT)

        self._update_summary()

    def _populate_proposals(self):
        """Remplit la liste des propositions."""
        for proposal in self.result.proposals:
            # Couleur d'indicateur de confiance
            if proposal.confidence >= 0.9:
                conf_icon = "🟢"
            elif proposal.confidence >= 0.7:
                conf_icon = "🟡"
            elif proposal.confidence >= 0.5:
                conf_icon = "🟠"
            else:
                conf_icon = "🔴"

            # État
            if proposal.has_existing_match:
                status = f"≈ {proposal.existing_node_name[:15]}..."
            else:
                status = "Nouveau"

            # Checkbox implicite via tags
            check = "☑" if proposal.is_selected else "☐"

            self.proposals_tree.insert(
                "",
                tk.END,
                iid=proposal.id,
                text=check,
                values=(
                    proposal.display_name,
                    proposal.segment_count,
                    f"{conf_icon} {proposal.confidence:.0%}",
                    status,
                ),
                tags=("selected" if proposal.is_selected else "unselected",),
            )

        # Tags de style
        self.proposals_tree.tag_configure("selected", foreground="black")
        self.proposals_tree.tag_configure("unselected", foreground="#888888")

    def _on_proposal_select(self, event):
        """Gère la sélection d'une proposition."""
        selection = self.proposals_tree.selection()
        if not selection:
            return

        proposal_id = selection[0]
        self.selected_proposal = next(
            (p for p in self.result.proposals if p.id == proposal_id), None
        )

        if self.selected_proposal:
            self._show_proposal_details(self.selected_proposal)

    def _on_double_click(self, event):
        """Toggle la sélection sur double-clic."""
        item = self.proposals_tree.identify_row(event.y)
        if not item:
            return

        proposal = next((p for p in self.result.proposals if p.id == item), None)
        if proposal:
            proposal.is_selected = not proposal.is_selected
            self._update_proposal_display(proposal)
            self._update_summary()

    def _show_proposal_details(self, proposal: NodeProposal):
        """Affiche les détails d'une proposition."""
        self.detail_name.configure(text=proposal.display_name)
        self.detail_desc.configure(text=proposal.description or "(Pas de description)")

        # Mots-clés
        if proposal.keywords:
            keywords = ", ".join(proposal.keywords)
        else:
            keywords = "(aucun)"
        self.detail_keywords.configure(text=keywords)

        # Nœud existant
        if proposal.has_existing_match:
            self.existing_label.configure(
                text=f'⚠️ Similaire au nœud existant "{proposal.existing_node_name}" '
                f"({proposal.similarity_to_existing:.0%})"
            )
            self.existing_frame.pack(fill=tk.X, pady=(0, 10))
        else:
            self.existing_frame.pack_forget()

        # Segments
        self.segments_text.configure(state=tk.NORMAL)
        self.segments_text.delete("1.0", tk.END)

        for i, segment in enumerate(proposal.segments):
            if i > 0:
                self.segments_text.insert(tk.END, "\n" + "─" * 40 + "\n", "separator")

            # Source
            self.segments_text.insert(tk.END, f"📄 {segment.source_name}\n", "source")

            # Texte
            self.segments_text.insert(tk.END, segment.text + "\n", "text")

        self.segments_text.configure(state=tk.DISABLED)

    def _update_proposal_display(self, proposal: NodeProposal):
        """Met à jour l'affichage d'une proposition."""
        check = "☑" if proposal.is_selected else "☐"
        self.proposals_tree.item(
            proposal.id,
            text=check,
            tags=("selected" if proposal.is_selected else "unselected",),
        )

    def _select_all(self):
        """Sélectionne toutes les propositions."""
        for proposal in self.result.proposals:
            proposal.is_selected = True
            self._update_proposal_display(proposal)
        self._update_summary()

    def _deselect_all(self):
        """Désélectionne toutes les propositions."""
        for proposal in self.result.proposals:
            proposal.is_selected = False
            self._update_proposal_display(proposal)
        self._update_summary()

    def _rename_selected(self):
        """Renomme la proposition sélectionnée."""
        if not self.selected_proposal:
            return

        new_name = simpledialog.askstring(
            "Renommer le thème",
            "Nouveau nom:",
            initialvalue=self.selected_proposal.display_name,
            parent=self,
        )

        if new_name:
            self.selected_proposal.user_edited_name = new_name
            self.proposals_tree.item(
                self.selected_proposal.id,
                values=(
                    new_name,
                    self.selected_proposal.segment_count,
                    self.proposals_tree.item(self.selected_proposal.id)["values"][2],
                    self.proposals_tree.item(self.selected_proposal.id)["values"][3],
                ),
            )
            self._show_proposal_details(self.selected_proposal)

    def _update_summary(self):
        """Met à jour le résumé."""
        selected = self.result.selected_proposals
        n_nodes = len(selected)
        n_segments = sum(p.segment_count for p in selected)

        self.summary_label.configure(
            text=f"{n_nodes} nœud(s) à créer · {n_segments} segment(s) à coder"
        )

    def _center_window(self, parent):
        """Centre la fenêtre sur son parent."""
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def apply(self):
        """Applique les sélections et ferme."""
        if not self.result.selected_proposals:
            tk.messagebox.showwarning(
                "Aucun thème sélectionné",
                "Veuillez sélectionner au moins un thème à créer.",
                parent=self,
            )
            return

        self.approved = True
        self.destroy()

    def cancel(self):
        """Annule et ferme."""
        self.approved = False
        self.destroy()


class AutoCodingProgressDialog(tk.Toplevel):
    """Dialogue de progression pour l'analyse d'auto-codage."""

    def __init__(self, parent, n_sources: int):
        """
        Initialise le dialogue.

        Args:
            parent: Fenêtre parente
            n_sources: Nombre de sources à analyser
        """
        super().__init__(parent)
        self.title("Analyse en cours")
        self.geometry("500x200")
        self.resizable(False, False)
        self.transient(parent)

        self.n_sources = n_sources
        self._cancelled = False

        self._setup_ui()
        self._center_window(parent)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_ui(self):
        """Configure l'interface."""
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Titre
        ttk.Label(
            main_frame,
            text="🔮 Détection automatique de nœuds",
            font=("", 11, "bold"),
        ).pack(anchor=tk.W)

        # Status
        self.status_label = ttk.Label(
            main_frame,
            text="Initialisation...",
            foreground="#666666",
        )
        self.status_label.pack(anchor=tk.W, pady=(10, 5))

        # Barre de progression
        self.progress = ttk.Progressbar(main_frame, mode="determinate", maximum=100)
        self.progress.pack(fill=tk.X, pady=(5, 10))

        # Détails
        self.details_label = ttk.Label(
            main_frame,
            text="",
            foreground="#888888",
            font=("", 9),
        )
        self.details_label.pack(anchor=tk.W)

        # Bouton Annuler
        self.cancel_btn = ttk.Button(main_frame, text="Annuler", command=self._on_cancel)
        self.cancel_btn.pack(side=tk.BOTTOM, anchor=tk.E)

    def update_progress(self, progress: float, message: str):
        """Met à jour la progression.

        Args:
            progress: Progression de 0 à 1
            message: Message de statut
        """
        self.progress["value"] = int(progress * 100)
        self.status_label.configure(text=message)
        self.update_idletasks()

    def set_details(self, details: str):
        """Met à jour les détails."""
        self.details_label.configure(text=details)
        self.update_idletasks()

    @property
    def cancelled(self) -> bool:
        """Retourne True si l'utilisateur a annulé."""
        return self._cancelled

    def _on_cancel(self):
        """Gère le clic sur Annuler."""
        self._cancelled = True
        self.cancel_btn.configure(state=tk.DISABLED, text="Annulation...")

    def _on_close(self):
        """Gère la tentative de fermeture."""
        self._on_cancel()

    def complete(self):
        """Termine le dialogue."""
        self.destroy()

    def _center_window(self, parent):
        """Centre la fenêtre sur son parent."""
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
