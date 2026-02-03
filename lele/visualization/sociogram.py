"""Génération de sociogrammes (graphes de relations)."""

import io
from pathlib import Path
from typing import Optional

from ..models.node import Node
from ..models.source import Source
from ..models.coding import CodeReference


class SociogramGenerator:
    """Génère des sociogrammes (graphes de relations) entre éléments."""

    def __init__(self, db):
        self.db = db

    def generate_node_cooccurrence(
        self,
        node_ids: Optional[list[str]] = None,
        min_cooccurrence: int = 1,
        width: int = 1000,
        height: int = 800,
    ) -> Optional[bytes]:
        """
        Génère un graphe de co-occurrence des nœuds.

        Args:
            node_ids: Nœuds à inclure (None = tous)
            min_cooccurrence: Nombre minimum de co-occurrences pour afficher un lien
            width: Largeur de l'image
            height: Hauteur de l'image

        Returns:
            Image PNG en bytes
        """
        try:
            import matplotlib.pyplot as plt
            import networkx as nx
        except ImportError:
            return None

        # Récupérer les nœuds
        if node_ids:
            nodes = [Node.get(self.db, nid) for nid in node_ids]
            nodes = [n for n in nodes if n]
        else:
            nodes = Node.get_all(self.db)

        if len(nodes) < 2:
            return None

        # Construire le graphe
        G = nx.Graph()

        # Ajouter les nœuds
        for node in nodes:
            G.add_node(
                node.id,
                label=node.name,
                color=node.color,
                size=node.reference_count or 1,
            )

        # Calculer les co-occurrences
        for i, node1 in enumerate(nodes):
            for node2 in nodes[i + 1 :]:
                cooc = self._count_cooccurrences(node1.id, node2.id)
                if cooc >= min_cooccurrence:
                    G.add_edge(node1.id, node2.id, weight=cooc)

        if G.number_of_edges() == 0:
            return None

        # Dessiner le graphe
        fig, ax = plt.subplots(figsize=(width / 100, height / 100))

        # Layout
        pos = nx.spring_layout(G, k=2, iterations=50)

        # Tailles et couleurs des nœuds
        node_sizes = [300 + G.nodes[n].get("size", 1) * 50 for n in G.nodes()]
        node_colors = [G.nodes[n].get("color", "#3498db") for n in G.nodes()]

        # Épaisseurs des arêtes
        edge_weights = [G.edges[e].get("weight", 1) for e in G.edges()]
        max_weight = max(edge_weights) if edge_weights else 1
        edge_widths = [1 + 3 * w / max_weight for w in edge_weights]

        # Dessiner les arêtes
        nx.draw_networkx_edges(G, pos, ax=ax, width=edge_widths, alpha=0.5, edge_color="#cccccc")

        # Dessiner les nœuds
        nx.draw_networkx_nodes(
            G, pos, ax=ax, node_size=node_sizes, node_color=node_colors, alpha=0.9
        )

        # Labels
        labels = {n: G.nodes[n].get("label", n)[:15] for n in G.nodes()}
        nx.draw_networkx_labels(G, pos, ax=ax, labels=labels, font_size=8)

        # Labels des arêtes (poids)
        edge_labels = {e: G.edges[e].get("weight", "") for e in G.edges()}
        nx.draw_networkx_edge_labels(G, pos, ax=ax, edge_labels=edge_labels, font_size=7)

        ax.axis("off")
        ax.set_title("Co-occurrence des codes")

        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        plt.close()
        buf.seek(0)

        return buf.read()

    def _count_cooccurrences(self, node_id_1: str, node_id_2: str) -> int:
        """Compte les co-occurrences de deux nœuds."""
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

    def generate_source_similarity(
        self,
        source_ids: Optional[list[str]] = None,
        min_similarity: float = 0.1,
        width: int = 1000,
        height: int = 800,
    ) -> Optional[bytes]:
        """
        Génère un graphe de similarité entre sources (basé sur les codages communs).

        Args:
            source_ids: Sources à inclure
            min_similarity: Similarité minimum (0-1) pour afficher un lien
            width: Largeur de l'image
            height: Hauteur de l'image

        Returns:
            Image PNG en bytes
        """
        try:
            import matplotlib.pyplot as plt
            import networkx as nx
        except ImportError:
            return None

        # Récupérer les sources
        if source_ids:
            sources = [Source.get(self.db, sid) for sid in source_ids]
            sources = [s for s in sources if s]
        else:
            sources = Source.get_all(self.db)

        if len(sources) < 2:
            return None

        # Construire le graphe
        G = nx.Graph()

        # Ajouter les sources comme nœuds
        for source in sources:
            ref_count = CodeReference.count_by_source(self.db, source.id)
            G.add_node(
                source.id,
                label=source.name,
                type=source.type.value,
                size=ref_count or 1,
            )

        # Calculer les similarités (Jaccard sur les nœuds)
        for i, source1 in enumerate(sources):
            nodes1 = set(r.node_id for r in CodeReference.get_by_source(self.db, source1.id))

            for source2 in sources[i + 1 :]:
                nodes2 = set(r.node_id for r in CodeReference.get_by_source(self.db, source2.id))

                if nodes1 and nodes2:
                    intersection = len(nodes1 & nodes2)
                    union = len(nodes1 | nodes2)
                    similarity = intersection / union if union > 0 else 0

                    if similarity >= min_similarity:
                        G.add_edge(source1.id, source2.id, weight=similarity)

        if G.number_of_edges() == 0:
            return None

        # Dessiner
        fig, ax = plt.subplots(figsize=(width / 100, height / 100))

        pos = nx.spring_layout(G, k=2, iterations=50)

        node_sizes = [200 + G.nodes[n].get("size", 1) * 30 for n in G.nodes()]

        # Couleurs par type
        type_colors = {
            "text": "#3498db",
            "pdf": "#e74c3c",
            "audio": "#2ecc71",
            "video": "#9b59b6",
            "image": "#f39c12",
            "spreadsheet": "#1abc9c",
        }
        node_colors = [type_colors.get(G.nodes[n].get("type", ""), "#95a5a6") for n in G.nodes()]

        edge_weights = [G.edges[e].get("weight", 0) for e in G.edges()]
        edge_widths = [1 + 4 * w for w in edge_weights]

        nx.draw_networkx_edges(G, pos, ax=ax, width=edge_widths, alpha=0.4, edge_color="#cccccc")
        nx.draw_networkx_nodes(
            G, pos, ax=ax, node_size=node_sizes, node_color=node_colors, alpha=0.9
        )

        labels = {n: G.nodes[n].get("label", n)[:12] for n in G.nodes()}
        nx.draw_networkx_labels(G, pos, ax=ax, labels=labels, font_size=7)

        ax.axis("off")
        ax.set_title("Similarité entre sources")

        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        plt.close()
        buf.seek(0)

        return buf.read()

    def export_gexf(
        self,
        output_path: Path,
        graph_type: str = "node_cooccurrence",
        **kwargs,
    ) -> bool:
        """
        Exporte le graphe au format GEXF (pour Gephi).

        Args:
            output_path: Chemin du fichier de sortie
            graph_type: Type de graphe ('node_cooccurrence' ou 'source_similarity')

        Returns:
            True si succès
        """
        try:
            import networkx as nx
        except ImportError:
            return False

        # Construire le graphe
        G = nx.Graph()

        if graph_type == "node_cooccurrence":
            nodes = Node.get_all(self.db)

            for node in nodes:
                G.add_node(
                    node.id,
                    label=node.name,
                    color=node.color,
                    size=node.reference_count or 1,
                )

            for i, node1 in enumerate(nodes):
                for node2 in nodes[i + 1 :]:
                    cooc = self._count_cooccurrences(node1.id, node2.id)
                    if cooc > 0:
                        G.add_edge(node1.id, node2.id, weight=cooc)

        elif graph_type == "source_similarity":
            sources = Source.get_all(self.db)

            for source in sources:
                ref_count = CodeReference.count_by_source(self.db, source.id)
                G.add_node(
                    source.id,
                    label=source.name,
                    type=source.type.value,
                    size=ref_count or 1,
                )

            for i, source1 in enumerate(sources):
                nodes1 = set(r.node_id for r in CodeReference.get_by_source(self.db, source1.id))
                for source2 in sources[i + 1 :]:
                    nodes2 = set(
                        r.node_id for r in CodeReference.get_by_source(self.db, source2.id)
                    )
                    if nodes1 and nodes2:
                        intersection = len(nodes1 & nodes2)
                        union = len(nodes1 | nodes2)
                        similarity = intersection / union if union > 0 else 0
                        if similarity > 0:
                            G.add_edge(source1.id, source2.id, weight=similarity)

        nx.write_gexf(G, str(output_path))
        return True

    def save(self, output_path: Path, graph_type: str = "node_cooccurrence", **kwargs) -> bool:
        """Génère et sauvegarde un sociogramme."""
        if graph_type == "node_cooccurrence":
            image_data = self.generate_node_cooccurrence(**kwargs)
        elif graph_type == "source_similarity":
            image_data = self.generate_source_similarity(**kwargs)
        else:
            return False

        if image_data:
            Path(output_path).write_bytes(image_data)
            return True
        return False
