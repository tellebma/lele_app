"""Modèle pour les sources de données."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class SourceType(Enum):
    """Types de sources supportés."""

    TEXT = "text"
    PDF = "pdf"
    WORD = "word"
    AUDIO = "audio"
    VIDEO = "video"
    IMAGE = "image"
    SPREADSHEET = "spreadsheet"
    SURVEY = "survey"
    BIBLIOGRAPHY = "bibliography"
    SOCIAL_MEDIA = "social_media"
    WEB = "web"
    OTHER = "other"

    @classmethod
    def from_extension(cls, ext: str) -> "SourceType":
        """Détermine le type depuis l'extension."""
        ext = ext.lower().lstrip(".")
        mapping = {
            # Texte
            "txt": cls.TEXT,
            "md": cls.TEXT,
            "rtf": cls.TEXT,
            # PDF
            "pdf": cls.PDF,
            # Word
            "doc": cls.WORD,
            "docx": cls.WORD,
            "odt": cls.WORD,
            # Audio
            "mp3": cls.AUDIO,
            "wav": cls.AUDIO,
            "m4a": cls.AUDIO,
            "flac": cls.AUDIO,
            "ogg": cls.AUDIO,
            "webm": cls.AUDIO,
            # Vidéo
            "mp4": cls.VIDEO,
            "avi": cls.VIDEO,
            "mov": cls.VIDEO,
            "mkv": cls.VIDEO,
            "wmv": cls.VIDEO,
            # Image
            "jpg": cls.IMAGE,
            "jpeg": cls.IMAGE,
            "png": cls.IMAGE,
            "gif": cls.IMAGE,
            "bmp": cls.IMAGE,
            "tiff": cls.IMAGE,
            "webp": cls.IMAGE,
            # Tableur
            "xlsx": cls.SPREADSHEET,
            "xls": cls.SPREADSHEET,
            "csv": cls.SPREADSHEET,
            "ods": cls.SPREADSHEET,
            # Bibliographie
            "ris": cls.BIBLIOGRAPHY,
            "bib": cls.BIBLIOGRAPHY,
            "enw": cls.BIBLIOGRAPHY,
            "xml": cls.BIBLIOGRAPHY,
        }
        return mapping.get(ext, cls.OTHER)


@dataclass
class Source:
    """Représente une source de données importée."""

    name: str
    type: SourceType
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    file_path: Optional[str] = None
    content: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if isinstance(self.type, str):
            self.type = SourceType(self.type)
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
        if isinstance(self.modified_at, str):
            self.modified_at = datetime.fromisoformat(self.modified_at)

    def to_dict(self) -> dict:
        """Convertit en dictionnaire pour la sérialisation."""
        import json
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "file_path": self.file_path,
            "content": self.content,
            "metadata": json.dumps(self.metadata),
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
        }

    @classmethod
    def from_row(cls, row: dict) -> "Source":
        """Crée une instance depuis une ligne de base de données."""
        import json
        metadata = row["metadata"]
        if isinstance(metadata, str):
            metadata = json.loads(metadata) if metadata else {}
        return cls(
            id=row["id"],
            name=row["name"],
            type=SourceType(row["type"]),
            file_path=row["file_path"],
            content=row["content"],
            metadata=metadata,
            created_at=row["created_at"],
            modified_at=row["modified_at"],
        )

    def save(self, db) -> "Source":
        """Sauvegarde la source dans la base de données."""
        import json
        data = self.to_dict()
        db.execute(
            """
            INSERT OR REPLACE INTO sources
            (id, name, type, file_path, content, metadata, created_at, modified_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["id"],
                data["name"],
                data["type"],
                data["file_path"],
                data["content"],
                data["metadata"],
                data["created_at"],
                data["modified_at"],
            ),
        )
        # Mettre à jour l'index FTS
        db.execute("DELETE FROM sources_fts WHERE id = ?", (self.id,))
        db.execute(
            "INSERT INTO sources_fts (id, name, content) VALUES (?, ?, ?)",
            (self.id, self.name, self.content or ""),
        )
        db.commit()
        return self

    @classmethod
    def get(cls, db, source_id: str) -> Optional["Source"]:
        """Récupère une source par ID."""
        cursor = db.execute("SELECT * FROM sources WHERE id = ?", (source_id,))
        row = cursor.fetchone()
        return cls.from_row(dict(row)) if row else None

    @classmethod
    def get_all(cls, db, source_type: Optional[SourceType] = None) -> list["Source"]:
        """Récupère toutes les sources, optionnellement filtrées par type."""
        if source_type:
            cursor = db.execute(
                "SELECT * FROM sources WHERE type = ? ORDER BY name",
                (source_type.value,),
            )
        else:
            cursor = db.execute("SELECT * FROM sources ORDER BY name")
        return [cls.from_row(dict(row)) for row in cursor.fetchall()]

    def delete(self, db):
        """Supprime la source de la base de données."""
        db.execute("DELETE FROM sources_fts WHERE id = ?", (self.id,))
        db.execute("DELETE FROM code_references WHERE source_id = ?", (self.id,))
        db.execute("DELETE FROM annotations WHERE source_id = ?", (self.id,))
        db.execute("DELETE FROM sources WHERE id = ?", (self.id,))
        db.commit()
