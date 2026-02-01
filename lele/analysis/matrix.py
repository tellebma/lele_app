"""Analyse matricielle pour l'application QDA."""

from dataclasses import dataclass
from typing import Optional

from ..models.source import Source
from ..models.node import Node
from ..models.coding import CodeReference
from ..models.case import Case


@dataclass
class MatrixCell:
    """Cellule d'une matrice d'analyse."""

    row_id: str
    col_id: str
    value: float
    references: list[CodeReference]


class MatrixAnalysis:
    """Analyse matricielle (crosstab) des codages."""

    def __init__(self, db):
        self.db = db

    def node_source_matrix(
        self,
        node_ids: Optional[list[str]] = None,
        source_ids: Optional[list[str]] = None,
        measure: str = "count",  # 'count', 'presence', 'percentage'
    ) -> dict:
        """
        Crée une matrice nœuds × sources.

        Args:
            node_ids: Nœuds à inclure (None = tous)
            source_ids: Sources à inclure (None = toutes)
            measure: Type de mesure

        Returns:
            Dictionnaire avec la matrice et les métadonnées
        """
        # Récupérer les nœuds et sources
        if node_ids:
            nodes = [Node.get(self.db, nid) for nid in node_ids]
            nodes = [n for n in nodes if n]
        else:
            nodes = Node.get_all(self.db)

        if source_ids:
            sources = [Source.get(self.db, sid) for sid in source_ids]
            sources = [s for s in sources if s]
        else:
            sources = Source.get_all(self.db)

        # Construire la matrice
        matrix = []
        row_labels = []
        col_labels = [s.name for s in sources]

        for node in nodes:
            row_labels.append(node.name)
            row = []

            for source in sources:
                refs = CodeReference.get_by_source_and_node(
                    self.db, source.id, node.id
                )

                if measure == "count":
                    value = len(refs)
                elif measure == "presence":
                    value = 1 if refs else 0
                elif measure == "percentage":
                    # Pourcentage du contenu codé
                    if source.content and refs:
                        total_coded = sum(
                            (r.end_pos or 0) - (r.start_pos or 0)
                            for r in refs
                        )
                        value = (total_coded / len(source.content)) * 100
                    else:
                        value = 0
                else:
                    value = len(refs)

                row.append(value)

            matrix.append(row)

        return {
            "matrix": matrix,
            "row_labels": row_labels,
            "col_labels": col_labels,
            "row_ids": [n.id for n in nodes],
            "col_ids": [s.id for s in sources],
            "measure": measure,
        }

    def node_node_matrix(
        self,
        node_ids: Optional[list[str]] = None,
        measure: str = "cooccurrence",  # 'cooccurrence', 'correlation'
    ) -> dict:
        """
        Crée une matrice de co-occurrence nœuds × nœuds.

        Args:
            node_ids: Nœuds à inclure
            measure: Type de mesure

        Returns:
            Matrice de co-occurrence
        """
        if node_ids:
            nodes = [Node.get(self.db, nid) for nid in node_ids]
            nodes = [n for n in nodes if n]
        else:
            nodes = Node.get_all(self.db)

        n = len(nodes)
        matrix = [[0] * n for _ in range(n)]
        labels = [node.name for node in nodes]

        # Calculer les co-occurrences
        for i, node1 in enumerate(nodes):
            for j, node2 in enumerate(nodes):
                if i <= j:  # Matrice symétrique
                    cooc = self._count_cooccurrences(node1.id, node2.id)
                    matrix[i][j] = cooc
                    matrix[j][i] = cooc

        return {
            "matrix": matrix,
            "labels": labels,
            "node_ids": [n.id for n in nodes],
            "measure": measure,
        }

    def _count_cooccurrences(self, node_id_1: str, node_id_2: str) -> int:
        """Compte les co-occurrences de deux nœuds dans les mêmes sources."""
        cursor = self.db.execute(
            """
            SELECT COUNT(DISTINCT cr1.source_id)
            FROM code_references cr1
            JOIN code_references cr2 ON cr1.source_id = cr2.source_id
            WHERE cr1.node_id = ? AND cr2.node_id = ?
            """,
            (node_id_1, node_id_2),
        )
        return cursor.fetchone()[0]

    def case_node_matrix(
        self,
        classification_id: str,
        node_ids: Optional[list[str]] = None,
    ) -> dict:
        """
        Crée une matrice cas × nœuds.

        Compte les références de codage pour chaque combinaison cas/nœud
        en utilisant les sources liées aux cas via la table links.

        Args:
            classification_id: ID de la classification des cas
            node_ids: Nœuds à inclure

        Returns:
            Matrice cas × nœuds
        """
        cases = Case.get_all(self.db, classification_id=classification_id)

        if node_ids:
            nodes = [Node.get(self.db, nid) for nid in node_ids]
            nodes = [n for n in nodes if n]
        else:
            nodes = Node.get_all(self.db)

        matrix = []
        row_labels = [c.name for c in cases]
        col_labels = [n.name for n in nodes]

        for case in cases:
            row = []
            # Récupérer les sources liées à ce cas
            source_ids = case.get_linked_source_ids(self.db)

            for node in nodes:
                # Compter les codages pour ce nœud dans les sources liées
                count = 0
                for source_id in source_ids:
                    refs = CodeReference.get_by_source_and_node(
                        self.db, source_id, node.id
                    )
                    count += len(refs)
                row.append(count)
            matrix.append(row)

        return {
            "matrix": matrix,
            "row_labels": row_labels,
            "col_labels": col_labels,
            "case_ids": [c.id for c in cases],
            "node_ids": [n.id for n in nodes],
        }

    def attribute_node_matrix(
        self,
        classification_id: str,
        attribute_id: str,
        node_ids: Optional[list[str]] = None,
    ) -> dict:
        """
        Crée une matrice valeurs d'attribut × nœuds.

        Utile pour voir comment les codages varient selon
        les caractéristiques des cas. Agrège les codages de tous
        les cas ayant une même valeur d'attribut.
        """
        from ..models.case import Classification

        classification = Classification.get(self.db, classification_id)
        if not classification:
            return {"error": "Classification non trouvée"}

        # Récupérer les valeurs uniques de l'attribut
        cursor = self.db.execute(
            "SELECT DISTINCT value FROM case_attributes WHERE attribute_id = ?",
            (attribute_id,),
        )
        attribute_values = [row["value"] for row in cursor.fetchall()]

        if node_ids:
            nodes = [Node.get(self.db, nid) for nid in node_ids]
            nodes = [n for n in nodes if n]
        else:
            nodes = Node.get_all(self.db)

        matrix = []
        row_labels = attribute_values
        col_labels = [n.name for n in nodes]

        for attr_value in attribute_values:
            row = []
            # Trouver les cas avec cette valeur d'attribut
            cursor = self.db.execute(
                "SELECT case_id FROM case_attributes WHERE attribute_id = ? AND value = ?",
                (attribute_id, attr_value),
            )
            case_ids = [r["case_id"] for r in cursor.fetchall()]

            # Récupérer toutes les sources liées à ces cas
            all_source_ids = set()
            for case_id in case_ids:
                case = Case.get(self.db, case_id)
                if case:
                    all_source_ids.update(case.get_linked_source_ids(self.db))

            for node in nodes:
                # Compter les codages pour ce nœud dans les sources des cas
                count = 0
                for source_id in all_source_ids:
                    refs = CodeReference.get_by_source_and_node(
                        self.db, source_id, node.id
                    )
                    count += len(refs)
                row.append(count)
            matrix.append(row)

        return {
            "matrix": matrix,
            "row_labels": row_labels,
            "col_labels": col_labels,
            "attribute_id": attribute_id,
            "node_ids": [n.id for n in nodes],
        }

    def get_statistics(self, matrix_data: dict) -> dict:
        """
        Calcule des statistiques sur une matrice.

        Args:
            matrix_data: Données de matrice retournées par les autres méthodes

        Returns:
            Statistiques (sommes, moyennes, etc.)
        """
        matrix = matrix_data.get("matrix", [])
        if not matrix:
            return {}

        import statistics

        # Statistiques par ligne
        row_stats = []
        for row in matrix:
            row_stats.append({
                "sum": sum(row),
                "mean": statistics.mean(row) if row else 0,
                "max": max(row) if row else 0,
                "min": min(row) if row else 0,
            })

        # Statistiques par colonne
        n_cols = len(matrix[0]) if matrix else 0
        col_stats = []
        for j in range(n_cols):
            col = [matrix[i][j] for i in range(len(matrix))]
            col_stats.append({
                "sum": sum(col),
                "mean": statistics.mean(col) if col else 0,
                "max": max(col) if col else 0,
                "min": min(col) if col else 0,
            })

        # Statistiques globales
        all_values = [v for row in matrix for v in row]
        global_stats = {
            "total": sum(all_values),
            "mean": statistics.mean(all_values) if all_values else 0,
            "stdev": statistics.stdev(all_values) if len(all_values) > 1 else 0,
            "max": max(all_values) if all_values else 0,
            "min": min(all_values) if all_values else 0,
        }

        return {
            "row_stats": row_stats,
            "col_stats": col_stats,
            "global": global_stats,
        }
