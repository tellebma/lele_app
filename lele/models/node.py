"""Modèle pour les nœuds (codes) d'analyse."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Node:
    """Représente un nœud (code) pour l'analyse qualitative."""

    name: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    color: str = "#3498db"
    parent_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)

    # Champs calculés (non persistés)
    reference_count: int = field(default=0, repr=False)
    children: list["Node"] = field(default_factory=list, repr=False)

    def __post_init__(self):
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
        if isinstance(self.modified_at, str):
            self.modified_at = datetime.fromisoformat(self.modified_at)

    def to_dict(self) -> dict:
        """Convertit en dictionnaire."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "color": self.color,
            "parent_id": self.parent_id,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
        }

    @classmethod
    def from_row(cls, row: dict) -> "Node":
        """Crée une instance depuis une ligne de base de données."""
        return cls(
            id=row["id"],
            name=row["name"],
            description=row.get("description", ""),
            color=row.get("color", "#3498db"),
            parent_id=row.get("parent_id"),
            created_at=row["created_at"],
            modified_at=row["modified_at"],
        )

    def save(self, db) -> "Node":
        """Sauvegarde le nœud dans la base de données."""
        self.modified_at = datetime.now()
        data = self.to_dict()
        db.execute(
            """
            INSERT OR REPLACE INTO nodes
            (id, name, description, color, parent_id, created_at, modified_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["id"],
                data["name"],
                data["description"],
                data["color"],
                data["parent_id"],
                data["created_at"],
                data["modified_at"],
            ),
        )
        db.commit()
        return self

    @classmethod
    def get(cls, db, node_id: str) -> Optional["Node"]:
        """Récupère un nœud par ID avec son compte de références."""
        cursor = db.execute(
            """
            SELECT n.*, COUNT(cr.id) as ref_count
            FROM nodes n
            LEFT JOIN code_references cr ON n.id = cr.node_id
            WHERE n.id = ?
            GROUP BY n.id
            """,
            (node_id,),
        )
        row = cursor.fetchone()
        if row:
            row_dict = dict(row)
            ref_count = row_dict.pop("ref_count", 0)
            node = cls.from_row(row_dict)
            node.reference_count = ref_count
            return node
        return None

    @classmethod
    def get_all(cls, db, parent_id: Optional[str] = None) -> list["Node"]:
        """Récupère tous les nœuds, optionnellement filtrés par parent.

        Optimisé avec une seule requête JOIN pour éviter le problème N+1.
        """
        if parent_id is None:
            cursor = db.execute("""
                SELECT n.*, COUNT(cr.id) as ref_count
                FROM nodes n
                LEFT JOIN code_references cr ON n.id = cr.node_id
                WHERE n.parent_id IS NULL
                GROUP BY n.id
                ORDER BY n.name
                """)
        else:
            cursor = db.execute(
                """
                SELECT n.*, COUNT(cr.id) as ref_count
                FROM nodes n
                LEFT JOIN code_references cr ON n.id = cr.node_id
                WHERE n.parent_id = ?
                GROUP BY n.id
                ORDER BY n.name
                """,
                (parent_id,),
            )

        nodes = []
        for row in cursor.fetchall():
            row_dict = dict(row)
            ref_count = row_dict.pop("ref_count", 0)
            node = cls.from_row(row_dict)
            node.reference_count = ref_count
            nodes.append(node)
        return nodes

    @classmethod
    def get_tree(cls, db) -> list["Node"]:
        """Récupère l'arbre complet des nœuds."""
        root_nodes = cls.get_all(db, parent_id=None)
        for node in root_nodes:
            node.children = cls._get_children_recursive(db, node.id)
        return root_nodes

    @classmethod
    def _get_children_recursive(cls, db, parent_id: str) -> list["Node"]:
        """Récupère récursivement les enfants d'un nœud."""
        children = cls.get_all(db, parent_id=parent_id)
        for child in children:
            child.children = cls._get_children_recursive(db, child.id)
        return children

    def delete(self, db, recursive: bool = True):
        """Supprime le nœud de la base de données."""
        if recursive:
            # Supprimer les enfants récursivement
            children = Node.get_all(db, parent_id=self.id)
            for child in children:
                child.delete(db, recursive=True)

        # Supprimer les références de codage
        db.execute("DELETE FROM code_references WHERE node_id = ?", (self.id,))
        # Supprimer les mémos liés
        db.execute(
            "UPDATE memos SET linked_node_id = NULL WHERE linked_node_id = ?",
            (self.id,),
        )
        # Supprimer le nœud
        db.execute("DELETE FROM nodes WHERE id = ?", (self.id,))
        db.commit()

    def get_references(self, db) -> list:
        """Récupère toutes les références de codage pour ce nœud."""
        from .coding import CodeReference

        return CodeReference.get_by_node(db, self.id)
