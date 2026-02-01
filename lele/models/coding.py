"""Modèle pour les références de codage."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class CodeReference:
    """Représente une référence de codage (lien entre nœud et source)."""

    node_id: str
    source_id: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    start_pos: Optional[int] = None
    end_pos: Optional[int] = None
    content: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    # Champs joints (non persistés)
    source_name: str = field(default="", repr=False)
    node_name: str = field(default="", repr=False)

    def __post_init__(self):
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)

    def to_dict(self) -> dict:
        """Convertit en dictionnaire."""
        return {
            "id": self.id,
            "node_id": self.node_id,
            "source_id": self.source_id,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_row(cls, row: dict) -> "CodeReference":
        """Crée une instance depuis une ligne de base de données."""
        ref = cls(
            id=row["id"],
            node_id=row["node_id"],
            source_id=row["source_id"],
            start_pos=row.get("start_pos"),
            end_pos=row.get("end_pos"),
            content=row.get("content"),
            created_at=row["created_at"],
        )
        # Champs joints si présents
        if "source_name" in row:
            ref.source_name = row["source_name"]
        if "node_name" in row:
            ref.node_name = row["node_name"]
        return ref

    def save(self, db) -> "CodeReference":
        """Sauvegarde la référence dans la base de données."""
        data = self.to_dict()
        db.execute(
            """
            INSERT OR REPLACE INTO code_references
            (id, node_id, source_id, start_pos, end_pos, content, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["id"],
                data["node_id"],
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
    def get(cls, db, ref_id: str) -> Optional["CodeReference"]:
        """Récupère une référence par ID."""
        cursor = db.execute(
            """
            SELECT cr.*, s.name as source_name, n.name as node_name
            FROM code_references cr
            JOIN sources s ON cr.source_id = s.id
            JOIN nodes n ON cr.node_id = n.id
            WHERE cr.id = ?
            """,
            (ref_id,),
        )
        row = cursor.fetchone()
        return cls.from_row(dict(row)) if row else None

    @classmethod
    def get_by_node(cls, db, node_id: str) -> list["CodeReference"]:
        """Récupère toutes les références pour un nœud."""
        cursor = db.execute(
            """
            SELECT cr.*, s.name as source_name, n.name as node_name
            FROM code_references cr
            JOIN sources s ON cr.source_id = s.id
            JOIN nodes n ON cr.node_id = n.id
            WHERE cr.node_id = ?
            ORDER BY s.name, cr.start_pos
            """,
            (node_id,),
        )
        return [cls.from_row(dict(row)) for row in cursor.fetchall()]

    @classmethod
    def get_by_source(cls, db, source_id: str) -> list["CodeReference"]:
        """Récupère toutes les références pour une source."""
        cursor = db.execute(
            """
            SELECT cr.*, s.name as source_name, n.name as node_name
            FROM code_references cr
            JOIN sources s ON cr.source_id = s.id
            JOIN nodes n ON cr.node_id = n.id
            WHERE cr.source_id = ?
            ORDER BY cr.start_pos
            """,
            (source_id,),
        )
        return [cls.from_row(dict(row)) for row in cursor.fetchall()]

    @classmethod
    def get_by_source_and_node(
        cls, db, source_id: str, node_id: str
    ) -> list["CodeReference"]:
        """Récupère les références pour une source et un nœud spécifiques."""
        cursor = db.execute(
            """
            SELECT cr.*, s.name as source_name, n.name as node_name
            FROM code_references cr
            JOIN sources s ON cr.source_id = s.id
            JOIN nodes n ON cr.node_id = n.id
            WHERE cr.source_id = ? AND cr.node_id = ?
            ORDER BY cr.start_pos
            """,
            (source_id, node_id),
        )
        return [cls.from_row(dict(row)) for row in cursor.fetchall()]

    def delete(self, db):
        """Supprime la référence de la base de données."""
        db.execute("DELETE FROM code_references WHERE id = ?", (self.id,))
        db.commit()

    @classmethod
    def count_by_node(cls, db, node_id: str) -> int:
        """Compte le nombre de références pour un nœud."""
        cursor = db.execute(
            "SELECT COUNT(*) FROM code_references WHERE node_id = ?", (node_id,)
        )
        return cursor.fetchone()[0]

    @classmethod
    def count_by_source(cls, db, source_id: str) -> int:
        """Compte le nombre de références pour une source."""
        cursor = db.execute(
            "SELECT COUNT(*) FROM code_references WHERE source_id = ?", (source_id,)
        )
        return cursor.fetchone()[0]
