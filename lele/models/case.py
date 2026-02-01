"""Modèles pour les cas et classifications."""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class AttributeType(Enum):
    """Types d'attributs pour les classifications."""

    TEXT = "text"
    INTEGER = "integer"
    DECIMAL = "decimal"
    DATE = "date"
    BOOLEAN = "boolean"
    LIST = "list"


@dataclass
class Attribute:
    """Représente un attribut de classification."""

    name: str
    classification_id: str
    data_type: AttributeType
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    options: list = field(default_factory=list)  # Pour les listes

    def __post_init__(self):
        if isinstance(self.data_type, str):
            self.data_type = AttributeType(self.data_type)

    def to_dict(self) -> dict:
        """Convertit en dictionnaire."""
        return {
            "id": self.id,
            "classification_id": self.classification_id,
            "name": self.name,
            "data_type": self.data_type.value,
            "options": json.dumps(self.options),
        }

    @classmethod
    def from_row(cls, row: dict) -> "Attribute":
        """Crée une instance depuis une ligne de base de données."""
        options = row.get("options", "[]")
        if isinstance(options, str):
            options = json.loads(options) if options else []
        return cls(
            id=row["id"],
            classification_id=row["classification_id"],
            name=row["name"],
            data_type=AttributeType(row["data_type"]),
            options=options,
        )

    def save(self, db) -> "Attribute":
        """Sauvegarde l'attribut dans la base de données."""
        data = self.to_dict()
        db.execute(
            """
            INSERT OR REPLACE INTO attributes
            (id, classification_id, name, data_type, options)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                data["id"],
                data["classification_id"],
                data["name"],
                data["data_type"],
                data["options"],
            ),
        )
        db.commit()
        return self

    @classmethod
    def get_by_classification(cls, db, classification_id: str) -> list["Attribute"]:
        """Récupère les attributs d'une classification."""
        cursor = db.execute(
            "SELECT * FROM attributes WHERE classification_id = ? ORDER BY name",
            (classification_id,),
        )
        return [cls.from_row(dict(row)) for row in cursor.fetchall()]

    def delete(self, db):
        """Supprime l'attribut de la base de données."""
        db.execute("DELETE FROM case_attributes WHERE attribute_id = ?", (self.id,))
        db.execute("DELETE FROM attributes WHERE id = ?", (self.id,))
        db.commit()


@dataclass
class Classification:
    """Représente une classification (schéma de cas)."""

    name: str
    type: str  # 'source' ou 'case'
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    # Champs non persistés
    attributes: list[Attribute] = field(default_factory=list, repr=False)

    def __post_init__(self):
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)

    def to_dict(self) -> dict:
        """Convertit en dictionnaire."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_row(cls, row: dict) -> "Classification":
        """Crée une instance depuis une ligne de base de données."""
        return cls(
            id=row["id"],
            name=row["name"],
            description=row.get("description", ""),
            type=row["type"],
            created_at=row["created_at"],
        )

    def save(self, db) -> "Classification":
        """Sauvegarde la classification dans la base de données."""
        data = self.to_dict()
        db.execute(
            """
            INSERT OR REPLACE INTO classifications
            (id, name, description, type, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                data["id"],
                data["name"],
                data["description"],
                data["type"],
                data["created_at"],
            ),
        )
        db.commit()
        return self

    @classmethod
    def get(cls, db, classification_id: str) -> Optional["Classification"]:
        """Récupère une classification par ID."""
        cursor = db.execute(
            "SELECT * FROM classifications WHERE id = ?", (classification_id,)
        )
        row = cursor.fetchone()
        if row:
            classification = cls.from_row(dict(row))
            classification.attributes = Attribute.get_by_classification(
                db, classification_id
            )
            return classification
        return None

    @classmethod
    def get_all(cls, db, type_filter: Optional[str] = None) -> list["Classification"]:
        """Récupère toutes les classifications."""
        if type_filter:
            cursor = db.execute(
                "SELECT * FROM classifications WHERE type = ? ORDER BY name",
                (type_filter,),
            )
        else:
            cursor = db.execute("SELECT * FROM classifications ORDER BY name")
        return [cls.from_row(dict(row)) for row in cursor.fetchall()]

    def add_attribute(
        self,
        db,
        name: str,
        data_type: AttributeType,
        options: list = None,
    ) -> Attribute:
        """Ajoute un attribut à la classification."""
        attr = Attribute(
            name=name,
            classification_id=self.id,
            data_type=data_type,
            options=options or [],
        )
        attr.save(db)
        self.attributes.append(attr)
        return attr

    def delete(self, db):
        """Supprime la classification de la base de données."""
        # Supprimer les attributs
        for attr in Attribute.get_by_classification(db, self.id):
            attr.delete(db)
        # Mettre à jour les cas
        db.execute(
            "UPDATE cases SET classification_id = NULL WHERE classification_id = ?",
            (self.id,),
        )
        db.execute("DELETE FROM classifications WHERE id = ?", (self.id,))
        db.commit()


@dataclass
class Case:
    """Représente un cas (unité d'analyse)."""

    name: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    classification_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    # Champs non persistés
    attribute_values: dict[str, Any] = field(default_factory=dict, repr=False)

    def __post_init__(self):
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)

    def to_dict(self) -> dict:
        """Convertit en dictionnaire."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "classification_id": self.classification_id,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_row(cls, row: dict) -> "Case":
        """Crée une instance depuis une ligne de base de données."""
        return cls(
            id=row["id"],
            name=row["name"],
            description=row.get("description", ""),
            classification_id=row.get("classification_id"),
            created_at=row["created_at"],
        )

    def save(self, db) -> "Case":
        """Sauvegarde le cas dans la base de données."""
        data = self.to_dict()
        db.execute(
            """
            INSERT OR REPLACE INTO cases
            (id, name, description, classification_id, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                data["id"],
                data["name"],
                data["description"],
                data["classification_id"],
                data["created_at"],
            ),
        )
        db.commit()
        return self

    def set_attribute(self, db, attribute_id: str, value: Any):
        """Définit la valeur d'un attribut pour ce cas."""
        str_value = json.dumps(value) if not isinstance(value, str) else value
        db.execute(
            """
            INSERT OR REPLACE INTO case_attributes (case_id, attribute_id, value)
            VALUES (?, ?, ?)
            """,
            (self.id, attribute_id, str_value),
        )
        db.commit()
        self.attribute_values[attribute_id] = value

    def get_attribute(self, db, attribute_id: str) -> Any:
        """Récupère la valeur d'un attribut."""
        cursor = db.execute(
            "SELECT value FROM case_attributes WHERE case_id = ? AND attribute_id = ?",
            (self.id, attribute_id),
        )
        row = cursor.fetchone()
        if row:
            try:
                return json.loads(row["value"])
            except (json.JSONDecodeError, TypeError):
                return row["value"]
        return None

    def load_attributes(self, db):
        """Charge toutes les valeurs d'attributs."""
        cursor = db.execute(
            "SELECT attribute_id, value FROM case_attributes WHERE case_id = ?",
            (self.id,),
        )
        for row in cursor.fetchall():
            try:
                self.attribute_values[row["attribute_id"]] = json.loads(row["value"])
            except (json.JSONDecodeError, TypeError):
                self.attribute_values[row["attribute_id"]] = row["value"]

    @classmethod
    def get(cls, db, case_id: str) -> Optional["Case"]:
        """Récupère un cas par ID."""
        cursor = db.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
        row = cursor.fetchone()
        if row:
            case = cls.from_row(dict(row))
            case.load_attributes(db)
            return case
        return None

    @classmethod
    def get_all(
        cls, db, classification_id: Optional[str] = None
    ) -> list["Case"]:
        """Récupère tous les cas."""
        if classification_id:
            cursor = db.execute(
                "SELECT * FROM cases WHERE classification_id = ? ORDER BY name",
                (classification_id,),
            )
        else:
            cursor = db.execute("SELECT * FROM cases ORDER BY name")
        return [cls.from_row(dict(row)) for row in cursor.fetchall()]

    def delete(self, db):
        """Supprime le cas de la base de données."""
        db.execute("DELETE FROM case_attributes WHERE case_id = ?", (self.id,))
        db.execute("DELETE FROM cases WHERE id = ?", (self.id,))
        db.commit()

    def get_linked_source_ids(self, db) -> list[str]:
        """Récupère les IDs des sources liées à ce cas via la table links."""
        cursor = db.execute(
            """
            SELECT target_id FROM links
            WHERE source_type = 'case' AND source_id = ? AND target_type = 'source'
            UNION
            SELECT source_id FROM links
            WHERE target_type = 'case' AND target_id = ? AND source_type = 'source'
            """,
            (self.id, self.id),
        )
        return [row[0] for row in cursor.fetchall()]

    def link_source(self, db, source_id: str, link_type: str = "contains"):
        """Lie une source à ce cas."""
        from datetime import datetime
        link_id = str(uuid.uuid4())
        db.execute(
            """
            INSERT INTO links (id, source_type, source_id, target_type, target_id, link_type, created_at)
            VALUES (?, 'case', ?, 'source', ?, ?, ?)
            """,
            (link_id, self.id, source_id, link_type, datetime.now().isoformat()),
        )
        db.commit()
