"""Modèles pour les mémos et annotations."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Memo:
    """Représente un mémo (note de recherche)."""

    title: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    linked_source_id: Optional[str] = None
    linked_node_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
        if isinstance(self.modified_at, str):
            self.modified_at = datetime.fromisoformat(self.modified_at)

    def to_dict(self) -> dict:
        """Convertit en dictionnaire."""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "linked_source_id": self.linked_source_id,
            "linked_node_id": self.linked_node_id,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
        }

    @classmethod
    def from_row(cls, row: dict) -> "Memo":
        """Crée une instance depuis une ligne de base de données."""
        return cls(
            id=row["id"],
            title=row["title"],
            content=row.get("content", ""),
            linked_source_id=row.get("linked_source_id"),
            linked_node_id=row.get("linked_node_id"),
            created_at=row["created_at"],
            modified_at=row["modified_at"],
        )

    def save(self, db) -> "Memo":
        """Sauvegarde le mémo dans la base de données."""
        self.modified_at = datetime.now()
        data = self.to_dict()
        db.execute(
            """
            INSERT OR REPLACE INTO memos
            (id, title, content, linked_source_id, linked_node_id, created_at, modified_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["id"],
                data["title"],
                data["content"],
                data["linked_source_id"],
                data["linked_node_id"],
                data["created_at"],
                data["modified_at"],
            ),
        )
        # Mettre à jour l'index FTS
        db.execute("DELETE FROM memos_fts WHERE id = ?", (self.id,))
        db.execute(
            "INSERT INTO memos_fts (id, title, content) VALUES (?, ?, ?)",
            (self.id, self.title, self.content),
        )
        db.commit()
        return self

    @classmethod
    def get(cls, db, memo_id: str) -> Optional["Memo"]:
        """Récupère un mémo par ID."""
        cursor = db.execute("SELECT * FROM memos WHERE id = ?", (memo_id,))
        row = cursor.fetchone()
        return cls.from_row(dict(row)) if row else None

    @classmethod
    def get_all(cls, db) -> list["Memo"]:
        """Récupère tous les mémos."""
        cursor = db.execute("SELECT * FROM memos ORDER BY modified_at DESC")
        return [cls.from_row(dict(row)) for row in cursor.fetchall()]

    @classmethod
    def get_by_source(cls, db, source_id: str) -> list["Memo"]:
        """Récupère les mémos liés à une source."""
        cursor = db.execute(
            "SELECT * FROM memos WHERE linked_source_id = ? ORDER BY modified_at DESC",
            (source_id,),
        )
        return [cls.from_row(dict(row)) for row in cursor.fetchall()]

    @classmethod
    def get_by_node(cls, db, node_id: str) -> list["Memo"]:
        """Récupère les mémos liés à un nœud."""
        cursor = db.execute(
            "SELECT * FROM memos WHERE linked_node_id = ? ORDER BY modified_at DESC",
            (node_id,),
        )
        return [cls.from_row(dict(row)) for row in cursor.fetchall()]

    def delete(self, db):
        """Supprime le mémo de la base de données."""
        db.execute("DELETE FROM memos_fts WHERE id = ?", (self.id,))
        db.execute("DELETE FROM memos WHERE id = ?", (self.id,))
        db.commit()


@dataclass
class Annotation:
    """Représente une annotation sur une source."""

    source_id: str
    content: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    start_pos: Optional[int] = None
    end_pos: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)

    def to_dict(self) -> dict:
        """Convertit en dictionnaire."""
        return {
            "id": self.id,
            "source_id": self.source_id,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_row(cls, row: dict) -> "Annotation":
        """Crée une instance depuis une ligne de base de données."""
        return cls(
            id=row["id"],
            source_id=row["source_id"],
            start_pos=row.get("start_pos"),
            end_pos=row.get("end_pos"),
            content=row["content"],
            created_at=row["created_at"],
        )

    def save(self, db) -> "Annotation":
        """Sauvegarde l'annotation dans la base de données."""
        data = self.to_dict()
        db.execute(
            """
            INSERT OR REPLACE INTO annotations
            (id, source_id, start_pos, end_pos, content, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                data["id"],
                data["source_id"],
                data["start_pos"],
                data["end_pos"],
                data["content"],
                data["created_at"],
            ),
        )
        db.commit()
        return self

    @classmethod
    def get_by_source(cls, db, source_id: str) -> list["Annotation"]:
        """Récupère les annotations d'une source."""
        cursor = db.execute(
            "SELECT * FROM annotations WHERE source_id = ? ORDER BY start_pos",
            (source_id,),
        )
        return [cls.from_row(dict(row)) for row in cursor.fetchall()]

    def delete(self, db):
        """Supprime l'annotation de la base de données."""
        db.execute("DELETE FROM annotations WHERE id = ?", (self.id,))
        db.commit()
