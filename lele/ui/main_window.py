"""Fenêtre principale de l'application Lele."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Optional

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

from ..models.project import Project
from ..models.source import Source, SourceType
from ..models.node import Node
from ..models.coding import CodeReference
from ..models.memo import Memo
from ..importers import get_importer


class MainWindow:
    """Fenêtre principale de l'application QDA."""

    def __init__(self):
        # Créer la fenêtre principale
        if DND_AVAILABLE:
            self.root = TkinterDnD.Tk()
        else:
            self.root = tk.Tk()

        self.root.title("Lele - Analyse Qualitative")
        self.root.geometry("1400x900")
        self.root.minsize(1000, 600)

        # État de l'application
        self.project: Optional[Project] = None
        self.current_source: Optional[Source] = None
        self.selected_node: Optional[Node] = None

        # Configuration des styles
        self.setup_styles()

        # Créer l'interface
        self.setup_menu()
        self.setup_toolbar()
        self.setup_main_layout()
        self.setup_status_bar()

        # Bindings
        self.setup_bindings()

    def setup_styles(self):
        """Configure les styles ttk."""
        style = ttk.Style()
        style.theme_use("clam")

        # Styles personnalisés
        style.configure("Sidebar.TFrame", background="#f5f5f5")
        style.configure("Toolbar.TFrame", background="#e0e0e0")
        style.configure("Title.TLabel", font=("", 11, "bold"))
        style.configure("Sidebar.TLabel", background="#f5f5f5")
        style.configure(
            "Treeview",
            rowheight=25,
            font=("", 10),
        )
        style.configure("Treeview.Heading", font=("", 10, "bold"))

    def setup_menu(self):
        """Configure la barre de menu."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # Menu Fichier
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Fichier", menu=file_menu)
        file_menu.add_command(
            label="Nouveau projet...", command=self.new_project, accelerator="Ctrl+N"
        )
        file_menu.add_command(
            label="Ouvrir projet...", command=self.open_project, accelerator="Ctrl+O"
        )
        file_menu.add_command(
            label="Sauvegarder", command=self.save_project, accelerator="Ctrl+S"
        )
        file_menu.add_separator()
        file_menu.add_command(label="Importer...", command=self.import_files)
        file_menu.add_command(label="Exporter...", command=self.export_project)
        file_menu.add_separator()
        file_menu.add_command(label="Quitter", command=self.quit_app, accelerator="Ctrl+Q")

        # Menu Édition
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Édition", menu=edit_menu)
        edit_menu.add_command(label="Annuler", accelerator="Ctrl+Z")
        edit_menu.add_command(label="Rétablir", accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="Rechercher...", command=self.show_search, accelerator="Ctrl+F")

        # Menu Codage
        coding_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Codage", menu=coding_menu)
        coding_menu.add_command(label="Nouveau nœud...", command=self.create_node)
        coding_menu.add_command(label="Coder la sélection", command=self.code_selection, accelerator="Ctrl+K")
        coding_menu.add_separator()
        coding_menu.add_command(label="Gérer les nœuds...", command=self.manage_nodes)

        # Menu Analyse
        analysis_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Analyse", menu=analysis_menu)
        analysis_menu.add_command(label="Requête de codage...", command=self.coding_query)
        analysis_menu.add_command(label="Matrice...", command=self.show_matrix)
        analysis_menu.add_separator()
        analysis_menu.add_command(label="Nuage de mots", command=self.show_wordcloud)
        analysis_menu.add_command(label="Carte mentale", command=self.show_mindmap)
        analysis_menu.add_command(label="Sociogramme", command=self.show_sociogram)

        # Menu Aide
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Aide", menu=help_menu)
        help_menu.add_command(label="Documentation")
        help_menu.add_command(label="À propos", command=self.show_about)

    def setup_toolbar(self):
        """Configure la barre d'outils."""
        toolbar = ttk.Frame(self.root, style="Toolbar.TFrame", padding="5")
        toolbar.pack(fill=tk.X, side=tk.TOP)

        # Boutons de la barre d'outils
        ttk.Button(toolbar, text="📁 Nouveau", command=self.new_project).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="📂 Ouvrir", command=self.open_project).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="💾 Sauver", command=self.save_project).pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        ttk.Button(toolbar, text="📥 Importer", command=self.import_files).pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        ttk.Button(toolbar, text="🏷️ Coder", command=self.code_selection).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="📝 Mémo", command=self.create_memo).pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        ttk.Button(toolbar, text="🔍 Rechercher", command=self.show_search).pack(side=tk.LEFT, padx=2)

        # Recherche rapide
        ttk.Label(toolbar, text="  ").pack(side=tk.LEFT)
        self.quick_search_var = tk.StringVar()
        quick_search = ttk.Entry(toolbar, textvariable=self.quick_search_var, width=30)
        quick_search.pack(side=tk.LEFT, padx=2)
        quick_search.bind("<Return>", lambda e: self.quick_search())

    def setup_main_layout(self):
        """Configure la disposition principale."""
        # PanedWindow principal (horizontal)
        self.main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Panneau gauche (navigation)
        self.left_panel = ttk.Frame(self.main_paned, width=250)
        self.main_paned.add(self.left_panel, weight=0)

        # Notebook pour la navigation
        self.nav_notebook = ttk.Notebook(self.left_panel)
        self.nav_notebook.pack(fill=tk.BOTH, expand=True)

        # Onglet Sources
        self.sources_frame = ttk.Frame(self.nav_notebook)
        self.nav_notebook.add(self.sources_frame, text="Sources")
        self.setup_sources_panel()

        # Onglet Nœuds
        self.nodes_frame = ttk.Frame(self.nav_notebook)
        self.nav_notebook.add(self.nodes_frame, text="Nœuds")
        self.setup_nodes_panel()

        # Onglet Cas
        self.cases_frame = ttk.Frame(self.nav_notebook)
        self.nav_notebook.add(self.cases_frame, text="Cas")

        # Onglet Mémos
        self.memos_frame = ttk.Frame(self.nav_notebook)
        self.nav_notebook.add(self.memos_frame, text="Mémos")

        # Panneau central (contenu)
        self.center_paned = ttk.PanedWindow(self.main_paned, orient=tk.VERTICAL)
        self.main_paned.add(self.center_paned, weight=1)

        # Zone de contenu principale
        self.content_frame = ttk.Frame(self.center_paned)
        self.center_paned.add(self.content_frame, weight=1)
        self.setup_content_area()

        # Zone d'analyse en bas
        self.analysis_frame = ttk.Frame(self.center_paned, height=200)
        self.center_paned.add(self.analysis_frame, weight=0)
        self.setup_analysis_area()

        # Panneau droit (propriétés/codage)
        self.right_panel = ttk.Frame(self.main_paned, width=300)
        self.main_paned.add(self.right_panel, weight=0)
        self.setup_right_panel()

    def setup_sources_panel(self):
        """Configure le panneau des sources."""
        # Boutons
        btn_frame = ttk.Frame(self.sources_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(btn_frame, text="+", width=3, command=self.import_files).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="-", width=3, command=self.delete_source).pack(side=tk.LEFT, padx=2)

        # Filtre par type
        self.source_type_filter = ttk.Combobox(
            btn_frame,
            values=["Tous", "Texte", "Audio", "Vidéo", "Image", "Tableur", "PDF"],
            state="readonly",
            width=10,
        )
        self.source_type_filter.set("Tous")
        self.source_type_filter.pack(side=tk.RIGHT)
        self.source_type_filter.bind("<<ComboboxSelected>>", lambda e: self.refresh_sources())

        # Arbre des sources
        self.sources_tree = ttk.Treeview(
            self.sources_frame,
            columns=("type", "refs"),
            show="tree headings",
            selectmode="browse",
        )
        self.sources_tree.heading("#0", text="Nom")
        self.sources_tree.heading("type", text="Type")
        self.sources_tree.heading("refs", text="Réf.")
        self.sources_tree.column("#0", width=150)
        self.sources_tree.column("type", width=60)
        self.sources_tree.column("refs", width=40)

        sources_scroll = ttk.Scrollbar(self.sources_frame, orient=tk.VERTICAL, command=self.sources_tree.yview)
        self.sources_tree.configure(yscrollcommand=sources_scroll.set)

        self.sources_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        sources_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=5)

        self.sources_tree.bind("<<TreeviewSelect>>", self.on_source_select)
        self.sources_tree.bind("<Double-1>", self.on_source_double_click)

        # Drop zone pour le drag & drop
        if DND_AVAILABLE:
            self.sources_tree.drop_target_register(DND_FILES)
            self.sources_tree.dnd_bind("<<Drop>>", self.on_files_drop)

    def setup_nodes_panel(self):
        """Configure le panneau des nœuds."""
        # Boutons
        btn_frame = ttk.Frame(self.nodes_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(btn_frame, text="+", width=3, command=self.create_node).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="-", width=3, command=self.delete_node).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="📁", width=3, command=self.create_node_folder).pack(side=tk.LEFT, padx=2)

        # Arbre des nœuds
        self.nodes_tree = ttk.Treeview(
            self.nodes_frame,
            columns=("refs",),
            show="tree headings",
            selectmode="browse",
        )
        self.nodes_tree.heading("#0", text="Nœud")
        self.nodes_tree.heading("refs", text="Réf.")
        self.nodes_tree.column("#0", width=180)
        self.nodes_tree.column("refs", width=50)

        nodes_scroll = ttk.Scrollbar(self.nodes_frame, orient=tk.VERTICAL, command=self.nodes_tree.yview)
        self.nodes_tree.configure(yscrollcommand=nodes_scroll.set)

        self.nodes_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        nodes_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=5)

        self.nodes_tree.bind("<<TreeviewSelect>>", self.on_node_select)
        self.nodes_tree.bind("<Double-1>", self.on_node_double_click)

    def setup_content_area(self):
        """Configure la zone de contenu principale."""
        # Notebook pour différentes vues
        self.content_notebook = ttk.Notebook(self.content_frame)
        self.content_notebook.pack(fill=tk.BOTH, expand=True)

        # Vue texte
        self.text_frame = ttk.Frame(self.content_notebook)
        self.content_notebook.add(self.text_frame, text="Document")

        # Zone de texte avec numéros de ligne
        text_container = ttk.Frame(self.text_frame)
        text_container.pack(fill=tk.BOTH, expand=True)

        self.line_numbers = tk.Text(
            text_container,
            width=4,
            padx=4,
            takefocus=0,
            border=0,
            background="#f0f0f0",
            state="disabled",
            font=("Consolas", 11),
        )
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)

        self.content_text = tk.Text(
            text_container,
            wrap=tk.WORD,
            font=("Consolas", 11),
            padx=10,
            pady=10,
        )
        self.content_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        text_scroll = ttk.Scrollbar(text_container, orient=tk.VERTICAL, command=self.content_text.yview)
        self.content_text.configure(yscrollcommand=text_scroll.set)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Tags pour le surlignage des codes
        self.content_text.tag_configure("highlight", background="#fff3cd")
        self.content_text.tag_configure("selection", background="#cce5ff")

        # Vue média (pour audio/vidéo/images)
        self.media_frame = ttk.Frame(self.content_notebook)
        self.content_notebook.add(self.media_frame, text="Média")

        self.media_label = ttk.Label(
            self.media_frame,
            text="Sélectionnez un fichier média",
            anchor=tk.CENTER,
        )
        self.media_label.pack(expand=True)

    def setup_analysis_area(self):
        """Configure la zone d'analyse en bas."""
        # Notebook pour les résultats d'analyse
        self.analysis_notebook = ttk.Notebook(self.analysis_frame)
        self.analysis_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Résultats de recherche
        self.search_frame = ttk.Frame(self.analysis_notebook)
        self.analysis_notebook.add(self.search_frame, text="Recherche")

        self.search_results = ttk.Treeview(
            self.search_frame,
            columns=("type", "snippet"),
            show="headings",
        )
        self.search_results.heading("type", text="Type")
        self.search_results.heading("snippet", text="Extrait")
        self.search_results.column("type", width=80)
        self.search_results.column("snippet", width=500)
        self.search_results.pack(fill=tk.BOTH, expand=True)

        # Références de codage
        self.refs_frame = ttk.Frame(self.analysis_notebook)
        self.analysis_notebook.add(self.refs_frame, text="Références")

        self.refs_tree = ttk.Treeview(
            self.refs_frame,
            columns=("source", "content"),
            show="headings",
        )
        self.refs_tree.heading("source", text="Source")
        self.refs_tree.heading("content", text="Contenu")
        self.refs_tree.column("source", width=150)
        self.refs_tree.column("content", width=400)
        self.refs_tree.pack(fill=tk.BOTH, expand=True)

    def setup_right_panel(self):
        """Configure le panneau droit (propriétés/codage)."""
        # Notebook pour les propriétés
        self.props_notebook = ttk.Notebook(self.right_panel)
        self.props_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Propriétés de l'élément sélectionné
        self.props_frame = ttk.Frame(self.props_notebook)
        self.props_notebook.add(self.props_frame, text="Propriétés")

        ttk.Label(self.props_frame, text="Propriétés", style="Title.TLabel").pack(
            anchor=tk.W, padx=10, pady=(10, 5)
        )

        self.props_content = ttk.Frame(self.props_frame)
        self.props_content.pack(fill=tk.BOTH, expand=True, padx=10)

        # Codages du document actuel
        self.doc_codes_frame = ttk.Frame(self.props_notebook)
        self.props_notebook.add(self.doc_codes_frame, text="Codages")

        ttk.Label(self.doc_codes_frame, text="Codages du document", style="Title.TLabel").pack(
            anchor=tk.W, padx=10, pady=(10, 5)
        )

        self.doc_codes_tree = ttk.Treeview(
            self.doc_codes_frame,
            columns=("pos",),
            show="tree headings",
            height=10,
        )
        self.doc_codes_tree.heading("#0", text="Nœud")
        self.doc_codes_tree.heading("pos", text="Position")
        self.doc_codes_tree.column("#0", width=150)
        self.doc_codes_tree.column("pos", width=80)
        self.doc_codes_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Annotations
        self.annotations_frame = ttk.Frame(self.props_notebook)
        self.props_notebook.add(self.annotations_frame, text="Annotations")

    def setup_status_bar(self):
        """Configure la barre de statut."""
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_label = ttk.Label(self.status_bar, text="Prêt")
        self.status_label.pack(side=tk.LEFT, padx=10, pady=5)

        self.project_label = ttk.Label(self.status_bar, text="Aucun projet")
        self.project_label.pack(side=tk.RIGHT, padx=10, pady=5)

    def setup_bindings(self):
        """Configure les raccourcis clavier."""
        self.root.bind("<Control-n>", lambda e: self.new_project())
        self.root.bind("<Control-o>", lambda e: self.open_project())
        self.root.bind("<Control-s>", lambda e: self.save_project())
        self.root.bind("<Control-f>", lambda e: self.show_search())
        self.root.bind("<Control-k>", lambda e: self.code_selection())
        self.root.bind("<Control-q>", lambda e: self.quit_app())

    # --- Actions du menu ---

    def new_project(self):
        """Crée un nouveau projet."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Nouveau projet")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Nom du projet:").pack(padx=20, pady=(20, 5), anchor=tk.W)
        name_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=name_var, width=40).pack(padx=20, pady=5)

        ttk.Label(dialog, text="Emplacement:").pack(padx=20, pady=(10, 5), anchor=tk.W)
        path_var = tk.StringVar()
        path_frame = ttk.Frame(dialog)
        path_frame.pack(padx=20, pady=5, fill=tk.X)
        ttk.Entry(path_frame, textvariable=path_var, width=30).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(
            path_frame,
            text="...",
            width=3,
            command=lambda: path_var.set(filedialog.askdirectory()),
        ).pack(side=tk.LEFT, padx=(5, 0))

        def create():
            name = name_var.get().strip()
            path = path_var.get().strip()
            if not name or not path:
                messagebox.showerror("Erreur", "Veuillez remplir tous les champs")
                return

            project_path = Path(path) / name
            try:
                self.project = Project(name=name, path=project_path)
                self.project.create()
                self.refresh_all()
                self.update_status(f"Projet créé: {name}")
                self.project_label.configure(text=name)
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de la création: {e}")

        ttk.Button(dialog, text="Créer", command=create).pack(pady=20)

    def open_project(self):
        """Ouvre un projet existant."""
        path = filedialog.askdirectory(title="Sélectionner le dossier du projet")
        if path:
            try:
                self.project = Project.open(Path(path))
                self.refresh_all()
                self.update_status(f"Projet ouvert: {self.project.name}")
                self.project_label.configure(text=self.project.name)
            except Exception as e:
                messagebox.showerror("Erreur", f"Impossible d'ouvrir le projet: {e}")

    def save_project(self):
        """Sauvegarde le projet."""
        if self.project:
            self.project.save()
            self.update_status("Projet sauvegardé")

    def import_files(self):
        """Importe des fichiers."""
        if not self.project:
            messagebox.showwarning("Attention", "Veuillez d'abord créer ou ouvrir un projet")
            return

        filetypes = [
            ("Tous les fichiers supportés", "*.txt *.pdf *.docx *.mp3 *.wav *.mp4 *.jpg *.png *.xlsx *.csv"),
            ("Documents texte", "*.txt *.md *.rtf"),
            ("PDF", "*.pdf"),
            ("Word", "*.doc *.docx"),
            ("Audio", "*.mp3 *.wav *.m4a *.flac *.ogg"),
            ("Vidéo", "*.mp4 *.avi *.mov *.mkv"),
            ("Images", "*.jpg *.jpeg *.png *.gif *.bmp"),
            ("Tableurs", "*.xlsx *.xls *.csv"),
            ("Tous les fichiers", "*.*"),
        ]

        files = filedialog.askopenfilenames(filetypes=filetypes)
        if files:
            self.import_files_list(files)

    def import_files_list(self, files):
        """Importe une liste de fichiers."""
        imported = 0
        errors = []

        for file_path in files:
            try:
                importer = get_importer(file_path)
                importer.set_progress_callback(
                    lambda p, m: self.update_status(f"Import: {m} ({p*100:.0f}%)")
                )

                result = importer.import_file(
                    Path(file_path),
                    self.project.files_path,
                )

                if result.success and result.source:
                    result.source.save(self.project.db)
                    imported += 1
                else:
                    errors.append(f"{Path(file_path).name}: {result.error}")

            except Exception as e:
                errors.append(f"{Path(file_path).name}: {e}")

        self.refresh_sources()
        self.update_status(f"{imported} fichier(s) importé(s)")

        if errors:
            messagebox.showwarning("Erreurs d'import", "\n".join(errors))

    def on_files_drop(self, event):
        """Gère le drop de fichiers."""
        files = self.root.tk.splitlist(event.data)
        if files and self.project:
            self.import_files_list(files)

    def export_project(self):
        """Exporte le projet."""
        if not self.project:
            return
        # TODO: Implémenter l'export REFI-QDA

    def quit_app(self):
        """Quitte l'application."""
        if self.project:
            self.project.close()
        self.root.quit()

    # --- Actions de codage ---

    def create_node(self):
        """Crée un nouveau nœud."""
        if not self.project:
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Nouveau nœud")
        dialog.geometry("350x200")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Nom:").pack(padx=20, pady=(20, 5), anchor=tk.W)
        name_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=name_var, width=35).pack(padx=20, pady=5)

        ttk.Label(dialog, text="Description:").pack(padx=20, pady=(10, 5), anchor=tk.W)
        desc_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=desc_var, width=35).pack(padx=20, pady=5)

        ttk.Label(dialog, text="Couleur:").pack(padx=20, pady=(10, 5), anchor=tk.W)
        color_var = tk.StringVar(value="#3498db")

        color_frame = ttk.Frame(dialog)
        color_frame.pack(padx=20, pady=5, fill=tk.X)

        colors = ["#3498db", "#e74c3c", "#2ecc71", "#f39c12", "#9b59b6", "#1abc9c"]
        for color in colors:
            btn = tk.Button(
                color_frame,
                bg=color,
                width=3,
                command=lambda c=color: color_var.set(c),
            )
            btn.pack(side=tk.LEFT, padx=2)

        def create():
            name = name_var.get().strip()
            if not name:
                return

            node = Node(
                name=name,
                description=desc_var.get().strip(),
                color=color_var.get(),
                parent_id=self.selected_node.id if self.selected_node else None,
            )
            node.save(self.project.db)
            self.refresh_nodes()
            dialog.destroy()

        ttk.Button(dialog, text="Créer", command=create).pack(pady=20)

    def create_node_folder(self):
        """Crée un dossier de nœuds."""
        self.create_node()  # Même logique pour l'instant

    def delete_node(self):
        """Supprime le nœud sélectionné."""
        if not self.project or not self.selected_node:
            return

        if messagebox.askyesno(
            "Confirmer",
            f"Supprimer le nœud '{self.selected_node.name}' et ses références?",
        ):
            self.selected_node.delete(self.project.db)
            self.selected_node = None
            self.refresh_nodes()

    def code_selection(self):
        """Code la sélection avec le nœud sélectionné."""
        if not self.project or not self.current_source or not self.selected_node:
            messagebox.showinfo(
                "Information",
                "Sélectionnez une source et un nœud, puis sélectionnez du texte à coder.",
            )
            return

        try:
            sel_start = self.content_text.index(tk.SEL_FIRST)
            sel_end = self.content_text.index(tk.SEL_LAST)
            selected_text = self.content_text.get(sel_start, sel_end)

            # Convertir les indices tkinter en positions
            start_count = self.content_text.count("1.0", sel_start, "chars")
            end_count = self.content_text.count("1.0", sel_end, "chars")
            start_pos = int(start_count[0]) if start_count else 0
            end_pos = int(end_count[0]) if end_count else 0

            # Créer la référence de codage
            ref = CodeReference(
                node_id=self.selected_node.id,
                source_id=self.current_source.id,
                start_pos=start_pos,
                end_pos=end_pos,
                content=selected_text,
            )
            ref.save(self.project.db)

            # Surligner le texte codé
            self.highlight_coding(sel_start, sel_end, self.selected_node.color)
            self.refresh_document_codes()
            self.update_status(f"Texte codé avec '{self.selected_node.name}'")

        except tk.TclError:
            messagebox.showinfo("Information", "Veuillez sélectionner du texte à coder.")

    def highlight_coding(self, start, end, color):
        """Surligne un passage codé."""
        tag_name = f"code_{color}"
        self.content_text.tag_configure(tag_name, background=color + "40")
        self.content_text.tag_add(tag_name, start, end)

    def manage_nodes(self):
        """Affiche la fenêtre de gestion des nœuds."""
        # TODO: Implémenter une fenêtre de gestion avancée
        pass

    def coding_query(self):
        """Affiche la fenêtre de requête de codage."""
        # TODO: Implémenter l'interface de requête
        pass

    # --- Actions d'analyse ---

    def show_search(self):
        """Affiche la recherche."""
        self.analysis_notebook.select(self.search_frame)

        dialog = tk.Toplevel(self.root)
        dialog.title("Recherche")
        dialog.geometry("400x150")
        dialog.transient(self.root)

        ttk.Label(dialog, text="Rechercher:").pack(padx=20, pady=(20, 5), anchor=tk.W)
        search_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=search_var, width=40).pack(padx=20, pady=5)

        def search():
            query = search_var.get().strip()
            if query and self.project:
                from ..analysis.search import SearchEngine

                engine = SearchEngine(self.project.db)
                results = engine.search(query)

                self.search_results.delete(*self.search_results.get_children())
                for result in results:
                    self.search_results.insert(
                        "",
                        tk.END,
                        values=(result.item_type, result.snippet[:100]),
                    )

                dialog.destroy()
                self.update_status(f"{len(results)} résultat(s) trouvé(s)")

        ttk.Button(dialog, text="Rechercher", command=search).pack(pady=20)

    def quick_search(self):
        """Recherche rapide."""
        query = self.quick_search_var.get().strip()
        if query and self.project:
            from ..analysis.search import SearchEngine

            engine = SearchEngine(self.project.db)
            results = engine.search(query, limit=20)

            self.search_results.delete(*self.search_results.get_children())
            for result in results:
                self.search_results.insert(
                    "",
                    tk.END,
                    values=(result.item_type, result.snippet[:100]),
                )

            self.analysis_notebook.select(self.search_frame)
            self.update_status(f"{len(results)} résultat(s)")

    def show_matrix(self):
        """Affiche une analyse matricielle."""
        if not self.project:
            return
        # TODO: Implémenter l'interface de matrice

    def show_wordcloud(self):
        """Génère et affiche un nuage de mots."""
        if not self.project:
            return

        from ..visualization.wordcloud_viz import WordCloudGenerator

        generator = WordCloudGenerator(self.project.db)
        image_data = generator.generate()

        if image_data:
            # Afficher dans une nouvelle fenêtre
            window = tk.Toplevel(self.root)
            window.title("Nuage de mots")
            window.geometry("850x500")

            from PIL import Image, ImageTk
            import io

            img = Image.open(io.BytesIO(image_data))
            photo = ImageTk.PhotoImage(img)

            label = ttk.Label(window, image=photo)
            label.image = photo
            label.pack(expand=True)

            ttk.Button(
                window,
                text="Sauvegarder",
                command=lambda: self.save_visualization(image_data, "wordcloud.png"),
            ).pack(pady=10)

    def show_mindmap(self):
        """Génère et affiche une carte mentale."""
        if not self.project:
            return

        from ..visualization.mindmap import MindMapGenerator

        generator = MindMapGenerator(self.project.db)
        image_data = generator.generate()

        if image_data:
            window = tk.Toplevel(self.root)
            window.title("Carte mentale")
            window.geometry("1250x850")

            from PIL import Image, ImageTk
            import io

            img = Image.open(io.BytesIO(image_data))
            photo = ImageTk.PhotoImage(img)

            label = ttk.Label(window, image=photo)
            label.image = photo
            label.pack(expand=True)

            ttk.Button(
                window,
                text="Sauvegarder",
                command=lambda: self.save_visualization(image_data, "mindmap.png"),
            ).pack(pady=10)

    def show_sociogram(self):
        """Génère et affiche un sociogramme."""
        if not self.project:
            return

        from ..visualization.sociogram import SociogramGenerator

        generator = SociogramGenerator(self.project.db)
        image_data = generator.generate_node_cooccurrence()

        if image_data:
            window = tk.Toplevel(self.root)
            window.title("Sociogramme")
            window.geometry("1050x850")

            from PIL import Image, ImageTk
            import io

            img = Image.open(io.BytesIO(image_data))
            photo = ImageTk.PhotoImage(img)

            label = ttk.Label(window, image=photo)
            label.image = photo
            label.pack(expand=True)

            ttk.Button(
                window,
                text="Sauvegarder",
                command=lambda: self.save_visualization(image_data, "sociogram.png"),
            ).pack(pady=10)

    def save_visualization(self, image_data: bytes, default_name: str):
        """Sauvegarde une visualisation."""
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            initialfile=default_name,
            filetypes=[("PNG", "*.png"), ("Tous", "*.*")],
        )
        if path:
            Path(path).write_bytes(image_data)
            self.update_status(f"Image sauvegardée: {path}")

    # --- Actions diverses ---

    def create_memo(self):
        """Crée un nouveau mémo."""
        if not self.project:
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Nouveau mémo")
        dialog.geometry("500x400")
        dialog.transient(self.root)

        ttk.Label(dialog, text="Titre:").pack(padx=20, pady=(20, 5), anchor=tk.W)
        title_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=title_var, width=50).pack(padx=20, pady=5)

        ttk.Label(dialog, text="Contenu:").pack(padx=20, pady=(10, 5), anchor=tk.W)
        content_text = tk.Text(dialog, width=50, height=15)
        content_text.pack(padx=20, pady=5)

        def save():
            title = title_var.get().strip()
            content = content_text.get("1.0", tk.END).strip()
            if title:
                memo = Memo(
                    title=title,
                    content=content,
                    linked_source_id=self.current_source.id if self.current_source else None,
                )
                memo.save(self.project.db)
                dialog.destroy()
                self.update_status("Mémo créé")

        ttk.Button(dialog, text="Sauvegarder", command=save).pack(pady=20)

    def delete_source(self):
        """Supprime la source sélectionnée."""
        if not self.project or not self.current_source:
            return

        if messagebox.askyesno(
            "Confirmer",
            f"Supprimer la source '{self.current_source.name}'?",
        ):
            self.current_source.delete(self.project.db)
            self.current_source = None
            self.refresh_sources()
            self.clear_content()

    def show_about(self):
        """Affiche la fenêtre À propos."""
        messagebox.showinfo(
            "À propos",
            "Lele - Analyse Qualitative de Données\n\n"
            "Version 0.1.0\n\n"
            "Application d'analyse qualitative inspirée de NVivo.\n"
            "Supporte l'import de multiples formats, le codage,\n"
            "et diverses visualisations.",
        )

    # --- Rafraîchissement de l'interface ---

    def refresh_all(self):
        """Rafraîchit toute l'interface."""
        self.refresh_sources()
        self.refresh_nodes()

    def refresh_sources(self):
        """Rafraîchit la liste des sources."""
        self.sources_tree.delete(*self.sources_tree.get_children())

        if not self.project:
            return

        filter_type = self.source_type_filter.get()
        type_map = {
            "Texte": SourceType.TEXT,
            "Audio": SourceType.AUDIO,
            "Vidéo": SourceType.VIDEO,
            "Image": SourceType.IMAGE,
            "Tableur": SourceType.SPREADSHEET,
            "PDF": SourceType.PDF,
        }

        source_filter = type_map.get(filter_type)
        sources = Source.get_all(self.project.db, source_type=source_filter)

        for source in sources:
            ref_count = CodeReference.count_by_source(self.project.db, source.id)
            self.sources_tree.insert(
                "",
                tk.END,
                iid=source.id,
                text=source.name,
                values=(source.type.value, ref_count),
            )

    def refresh_nodes(self):
        """Rafraîchit l'arbre des nœuds."""
        self.nodes_tree.delete(*self.nodes_tree.get_children())

        if not self.project:
            return

        def add_nodes(parent_id, tree_parent=""):
            nodes = Node.get_all(self.project.db, parent_id=parent_id)
            for node in nodes:
                self.nodes_tree.insert(
                    tree_parent,
                    tk.END,
                    iid=node.id,
                    text=node.name,
                    values=(node.reference_count,),
                    tags=(node.color,),
                )
                # Ajouter récursivement les enfants
                add_nodes(node.id, node.id)

        add_nodes(None)

    def refresh_document_codes(self):
        """Rafraîchit la liste des codes du document actuel."""
        self.doc_codes_tree.delete(*self.doc_codes_tree.get_children())

        if not self.project or not self.current_source:
            return

        refs = CodeReference.get_by_source(self.project.db, self.current_source.id)
        for ref in refs:
            pos = f"{ref.start_pos}-{ref.end_pos}" if ref.start_pos else ""
            self.doc_codes_tree.insert(
                "",
                tk.END,
                iid=ref.id,
                text=ref.node_name,
                values=(pos,),
            )

    # --- Gestionnaires d'événements ---

    def on_source_select(self, event):
        """Gère la sélection d'une source."""
        selection = self.sources_tree.selection()
        if selection:
            source_id = selection[0]
            self.current_source = Source.get(self.project.db, source_id)
            self.display_source()

    def on_source_double_click(self, event):
        """Gère le double-clic sur une source."""
        self.on_source_select(event)

    def on_node_select(self, event):
        """Gère la sélection d'un nœud."""
        selection = self.nodes_tree.selection()
        if selection:
            node_id = selection[0]
            self.selected_node = Node.get(self.project.db, node_id)
            self.display_node_references()

    def on_node_double_click(self, event):
        """Gère le double-clic sur un nœud."""
        # Ouvrir l'éditeur de nœud
        pass

    def display_source(self):
        """Affiche le contenu d'une source."""
        if not self.current_source:
            return

        self.content_text.configure(state=tk.NORMAL)
        self.content_text.delete("1.0", tk.END)

        if self.current_source.content:
            self.content_text.insert("1.0", self.current_source.content)

            # Surligner les codes existants
            refs = CodeReference.get_by_source(self.project.db, self.current_source.id)
            for ref in refs:
                if ref.start_pos is not None and ref.end_pos is not None:
                    node = Node.get(self.project.db, ref.node_id)
                    if node:
                        start = f"1.0+{ref.start_pos}c"
                        end = f"1.0+{ref.end_pos}c"
                        self.highlight_coding(start, end, node.color)

        self.refresh_document_codes()
        self.update_line_numbers()

    def display_node_references(self):
        """Affiche les références d'un nœud."""
        self.refs_tree.delete(*self.refs_tree.get_children())

        if not self.selected_node or not self.project:
            return

        refs = CodeReference.get_by_node(self.project.db, self.selected_node.id)
        for ref in refs:
            content = (ref.content or "")[:100]
            self.refs_tree.insert(
                "",
                tk.END,
                values=(ref.source_name, content),
            )

        self.analysis_notebook.select(self.refs_frame)

    def clear_content(self):
        """Efface la zone de contenu."""
        self.content_text.configure(state=tk.NORMAL)
        self.content_text.delete("1.0", tk.END)
        self.content_text.configure(state=tk.DISABLED)

    def update_line_numbers(self):
        """Met à jour les numéros de ligne."""
        self.line_numbers.configure(state=tk.NORMAL)
        self.line_numbers.delete("1.0", tk.END)

        line_count = int(self.content_text.index("end-1c").split(".")[0])
        lines = "\n".join(str(i) for i in range(1, line_count + 1))
        self.line_numbers.insert("1.0", lines)

        self.line_numbers.configure(state=tk.DISABLED)

    def update_status(self, message: str):
        """Met à jour la barre de statut."""
        self.status_label.configure(text=message)

    def run(self):
        """Lance l'application."""
        self.root.mainloop()
