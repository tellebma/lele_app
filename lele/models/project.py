"""Modèle de projet QDA."""

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class Project:
    """Représente un projet d'analyse qualitative."""

    name: str
    path: Path
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    settings: dict = field(default_factory=dict)

    _db_connection: Optional[sqlite3.Connection] = field(default=None, repr=False)

    def __post_init__(self):
        if isinstance(self.path, str):
            self.path = Path(self.path)
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
        if isinstance(self.modified_at, str):
            self.modified_at = datetime.fromisoformat(self.modified_at)

    @property
    def db_path(self) -> Path:
        """Chemin vers la base de données du projet."""
        return self.path / "project.db"

    @property
    def files_path(self) -> Path:
        """Chemin vers le dossier des fichiers sources."""
        return self.path / "files"

    @property
    def db(self) -> sqlite3.Connection:
        """Connexion à la base de données."""
        if self._db_connection is None:
            self._db_connection = sqlite3.connect(str(self.db_path))
            self._db_connection.row_factory = sqlite3.Row
        return self._db_connection

    def create(self) -> "Project":
        """Crée un nouveau projet sur le disque."""
        self.path.mkdir(parents=True, exist_ok=True)
        self.files_path.mkdir(exist_ok=True)

        self._init_database()
        self._save_metadata()
        return self

    def _init_database(self):
        """Initialise le schéma de la base de données."""
        schema = """
        -- Sources de données
        CREATE TABLE IF NOT EXISTS sources (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            file_path TEXT,
            content TEXT,
            metadata TEXT,
            created_at TEXT NOT NULL,
            modified_at TEXT NOT NULL
        );

        -- Nœuds (codes)
        CREATE TABLE IF NOT EXISTS nodes (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            color TEXT DEFAULT '#3498db',
            parent_id TEXT,
            created_at TEXT NOT NULL,
            modified_at TEXT NOT NULL,
            FOREIGN KEY (parent_id) REFERENCES nodes(id)
        );

        -- Références de codage
        CREATE TABLE IF NOT EXISTS code_references (
            id TEXT PRIMARY KEY,
            node_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            start_pos INTEGER,
            end_pos INTEGER,
            content TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (node_id) REFERENCES nodes(id),
            FOREIGN KEY (source_id) REFERENCES sources(id)
        );

        -- Mémos
        CREATE TABLE IF NOT EXISTS memos (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT,
            linked_source_id TEXT,
            linked_node_id TEXT,
            created_at TEXT NOT NULL,
            modified_at TEXT NOT NULL,
            FOREIGN KEY (linked_source_id) REFERENCES sources(id),
            FOREIGN KEY (linked_node_id) REFERENCES nodes(id)
        );

        -- Annotations
        CREATE TABLE IF NOT EXISTS annotations (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            start_pos INTEGER,
            end_pos INTEGER,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (source_id) REFERENCES sources(id)
        );

        -- Classifications
        CREATE TABLE IF NOT EXISTS classifications (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            type TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        -- Attributs de classification
        CREATE TABLE IF NOT EXISTS attributes (
            id TEXT PRIMARY KEY,
            classification_id TEXT NOT NULL,
            name TEXT NOT NULL,
            data_type TEXT NOT NULL,
            options TEXT,
            FOREIGN KEY (classification_id) REFERENCES classifications(id)
        );

        -- Cas
        CREATE TABLE IF NOT EXISTS cases (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            classification_id TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (classification_id) REFERENCES classifications(id)
        );

        -- Valeurs d'attributs pour les cas
        CREATE TABLE IF NOT EXISTS case_attributes (
            case_id TEXT NOT NULL,
            attribute_id TEXT NOT NULL,
            value TEXT,
            PRIMARY KEY (case_id, attribute_id),
            FOREIGN KEY (case_id) REFERENCES cases(id),
            FOREIGN KEY (attribute_id) REFERENCES attributes(id)
        );

        -- Liens entre éléments
        CREATE TABLE IF NOT EXISTS links (
            id TEXT PRIMARY KEY,
            source_type TEXT NOT NULL,
            source_id TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            link_type TEXT,
            description TEXT,
            created_at TEXT NOT NULL
        );

        -- Index pour les recherches
        CREATE INDEX IF NOT EXISTS idx_sources_type ON sources(type);
        CREATE INDEX IF NOT EXISTS idx_nodes_parent ON nodes(parent_id);
        CREATE INDEX IF NOT EXISTS idx_code_refs_node ON code_references(node_id);
        CREATE INDEX IF NOT EXISTS idx_code_refs_source ON code_references(source_id);
        CREATE INDEX IF NOT EXISTS idx_memos_source ON memos(linked_source_id);
        CREATE INDEX IF NOT EXISTS idx_memos_node ON memos(linked_node_id);

        -- Table FTS pour la recherche full-text
        CREATE VIRTUAL TABLE IF NOT EXISTS sources_fts USING fts5(
            id, name, content, tokenize='unicode61'
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS memos_fts USING fts5(
            id, title, content, tokenize='unicode61'
        );
        """
        self.db.executescript(schema)
        self.db.commit()

    def _save_metadata(self):
        """Sauvegarde les métadonnées du projet."""
        metadata = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
            "settings": self.settings,
            "version": "1.0",
        }
        meta_path = self.path / "project.json"
        meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False))

    def save(self):
        """Sauvegarde le projet."""
        self.modified_at = datetime.now()
        self._save_metadata()
        self.db.commit()

    @classmethod
    def open(cls, path: Path) -> "Project":
        """Ouvre un projet existant."""
        if isinstance(path, str):
            path = Path(path)

        meta_path = path / "project.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"Projet non trouvé: {path}")

        metadata = json.loads(meta_path.read_text())
        return cls(
            id=metadata["id"],
            name=metadata["name"],
            path=path,
            description=metadata.get("description", ""),
            created_at=metadata["created_at"],
            modified_at=metadata["modified_at"],
            settings=metadata.get("settings", {}),
        )

    def close(self):
        """Ferme le projet et libère les ressources."""
        if self._db_connection:
            self._db_connection.close()
            self._db_connection = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
