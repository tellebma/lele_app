"""Système de requêtes avancées pour l'analyse qualitative."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from ..models.source import Source
from ..models.node import Node
from ..models.coding import CodeReference


class QueryOperator(Enum):
    """Opérateurs pour les requêtes."""

    AND = "and"
    OR = "or"
    NOT = "not"
    NEAR = "near"  # Proximité
    PRECEDED_BY = "preceded_by"
    FOLLOWED_BY = "followed_by"


@dataclass
class QueryCondition:
    """Condition de requête."""

    field: str  # 'node', 'source', 'text', 'attribute'
    value: Any
    operator: str = "equals"  # equals, contains, starts_with, etc.


@dataclass
class QueryResult:
    """Résultat d'une requête."""

    source: Source
    references: list[CodeReference]
    context: str
    score: float = 0.0


class QueryBuilder:
    """Constructeur de requêtes pour l'analyse qualitative."""

    def __init__(self, db):
        self.db = db

    def coding_query(
        self,
        node_ids: list[str],
        operator: QueryOperator = QueryOperator.AND,
        scope: str = "source",  # 'source', 'paragraph', 'sentence'
    ) -> list[QueryResult]:
        """
        Requête sur les codages.

        Args:
            node_ids: IDs des nœuds à chercher
            operator: Opérateur logique
            scope: Portée de la recherche

        Returns:
            Liste de QueryResult
        """
        if operator == QueryOperator.AND:
            return self._coding_and_query(node_ids, scope)
        elif operator == QueryOperator.OR:
            return self._coding_or_query(node_ids, scope)
        elif operator == QueryOperator.NOT:
            return self._coding_not_query(node_ids, scope)
        else:
            return []

    def _coding_and_query(self, node_ids: list[str], scope: str) -> list[QueryResult]:
        """Trouve les sources/passages codés avec TOUS les nœuds."""
        results = []

        # Trouver les sources qui ont des codages pour tous les nœuds
        if scope == "source":
            # Pour chaque source, vérifier qu'elle a tous les nœuds
            cursor = self.db.execute("SELECT DISTINCT source_id FROM code_references")
            source_ids = [row["source_id"] for row in cursor.fetchall()]

            for source_id in source_ids:
                refs_by_node = {}
                all_nodes_present = True

                for node_id in node_ids:
                    refs = CodeReference.get_by_source_and_node(self.db, source_id, node_id)
                    if refs:
                        refs_by_node[node_id] = refs
                    else:
                        all_nodes_present = False
                        break

                if all_nodes_present:
                    source = Source.get(self.db, source_id)
                    if source:
                        all_refs = []
                        for refs in refs_by_node.values():
                            all_refs.extend(refs)

                        results.append(
                            QueryResult(
                                source=source,
                                references=all_refs,
                                context=source.content[:500] if source.content else "",
                                score=len(all_refs),
                            )
                        )

        return results

    def _coding_or_query(self, node_ids: list[str], scope: str) -> list[QueryResult]:
        """Trouve les sources/passages codés avec AU MOINS UN nœud."""
        results = []
        seen_sources = set()

        for node_id in node_ids:
            refs = CodeReference.get_by_node(self.db, node_id)
            for ref in refs:
                if ref.source_id not in seen_sources:
                    source = Source.get(self.db, ref.source_id)
                    if source:
                        all_refs = CodeReference.get_by_source(self.db, source.id)
                        # Filtrer pour ne garder que les nœuds demandés
                        filtered_refs = [r for r in all_refs if r.node_id in node_ids]

                        results.append(
                            QueryResult(
                                source=source,
                                references=filtered_refs,
                                context=source.content[:500] if source.content else "",
                                score=len(filtered_refs),
                            )
                        )
                        seen_sources.add(ref.source_id)

        return results

    def _coding_not_query(self, node_ids: list[str], scope: str) -> list[QueryResult]:
        """Trouve les sources qui N'ONT PAS les nœuds spécifiés."""
        results = []

        # Toutes les sources
        all_sources = Source.get_all(self.db)

        for source in all_sources:
            has_excluded_node = False
            for node_id in node_ids:
                refs = CodeReference.get_by_source_and_node(self.db, source.id, node_id)
                if refs:
                    has_excluded_node = True
                    break

            if not has_excluded_node:
                results.append(
                    QueryResult(
                        source=source,
                        references=[],
                        context=source.content[:500] if source.content else "",
                        score=1,
                    )
                )

        return results

    def proximity_query(
        self,
        node_id_1: str,
        node_id_2: str,
        max_distance: int = 100,  # En caractères
    ) -> list[QueryResult]:
        """
        Trouve les passages où deux nœuds sont proches.

        Args:
            node_id_1: Premier nœud
            node_id_2: Deuxième nœud
            max_distance: Distance maximale en caractères

        Returns:
            Liste de QueryResult
        """
        results = []

        # Trouver les sources avec les deux nœuds
        cursor = self.db.execute(
            """
            SELECT DISTINCT cr1.source_id
            FROM code_references cr1
            JOIN code_references cr2 ON cr1.source_id = cr2.source_id
            WHERE cr1.node_id = ? AND cr2.node_id = ?
            """,
            (node_id_1, node_id_2),
        )

        for row in cursor.fetchall():
            source_id = row["source_id"]
            source = Source.get(self.db, source_id)
            if not source:
                continue

            refs1 = CodeReference.get_by_source_and_node(self.db, source_id, node_id_1)
            refs2 = CodeReference.get_by_source_and_node(self.db, source_id, node_id_2)

            close_refs = []
            for r1 in refs1:
                for r2 in refs2:
                    if r1.end_pos and r2.start_pos:
                        distance = abs(r2.start_pos - r1.end_pos)
                        if distance <= max_distance:
                            close_refs.extend([r1, r2])

            if close_refs:
                results.append(
                    QueryResult(
                        source=source,
                        references=list(set(close_refs)),
                        context=source.content[:500] if source.content else "",
                        score=len(close_refs) / 2,
                    )
                )

        return results

    def text_query(
        self,
        text_pattern: str,
        node_ids: Optional[list[str]] = None,
        regex: bool = False,
    ) -> list[QueryResult]:
        """
        Recherche textuelle dans les passages codés.

        Args:
            text_pattern: Texte ou regex à chercher
            node_ids: Limiter aux passages codés avec ces nœuds
            regex: Traiter comme expression régulière

        Returns:
            Liste de QueryResult
        """
        import re

        results = []

        if regex:
            try:
                pattern = re.compile(text_pattern, re.IGNORECASE)
            except re.error:
                return []
        else:
            pattern = re.compile(re.escape(text_pattern), re.IGNORECASE)

        if node_ids:
            # Chercher dans les passages codés
            for node_id in node_ids:
                refs = CodeReference.get_by_node(self.db, node_id)
                for ref in refs:
                    if ref.content and pattern.search(ref.content):
                        source = Source.get(self.db, ref.source_id)
                        if source:
                            results.append(
                                QueryResult(
                                    source=source,
                                    references=[ref],
                                    context=ref.content,
                                    score=len(pattern.findall(ref.content)),
                                )
                            )
        else:
            # Chercher dans toutes les sources
            for source in Source.get_all(self.db):
                if source.content and pattern.search(source.content):
                    refs = CodeReference.get_by_source(self.db, source.id)
                    matches = pattern.findall(source.content)
                    results.append(
                        QueryResult(
                            source=source,
                            references=refs,
                            context=source.content[:500],
                            score=len(matches),
                        )
                    )

        return sorted(results, key=lambda r: r.score, reverse=True)

    def comparison_query(
        self,
        group1_sources: list[str],
        group2_sources: list[str],
        node_ids: Optional[list[str]] = None,
    ) -> dict:
        """
        Compare les codages entre deux groupes de sources.

        Args:
            group1_sources: IDs des sources du groupe 1
            group2_sources: IDs des sources du groupe 2
            node_ids: Nœuds à comparer (None = tous)

        Returns:
            Dictionnaire avec les statistiques comparatives
        """
        if node_ids is None:
            nodes = Node.get_all(self.db)
            node_ids = [n.id for n in nodes]

        comparison = {
            "group1": {},
            "group2": {},
            "differences": {},
        }

        for node_id in node_ids:
            node = Node.get(self.db, node_id)
            if not node:
                continue

            # Compter pour le groupe 1
            count1 = 0
            for source_id in group1_sources:
                refs = CodeReference.get_by_source_and_node(self.db, source_id, node_id)
                count1 += len(refs)

            # Compter pour le groupe 2
            count2 = 0
            for source_id in group2_sources:
                refs = CodeReference.get_by_source_and_node(self.db, source_id, node_id)
                count2 += len(refs)

            comparison["group1"][node.name] = count1
            comparison["group2"][node.name] = count2
            comparison["differences"][node.name] = count1 - count2

        return comparison
