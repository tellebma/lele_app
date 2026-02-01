"""Génération de graphiques (histogrammes, camemberts, etc.)."""

import io
from pathlib import Path
from typing import Optional

from ..models.node import Node
from ..models.source import Source
from ..models.coding import CodeReference


class ChartGenerator:
    """Génère des graphiques pour l'analyse QDA."""

    def __init__(self, db):
        self.db = db

    def coding_frequency_bar(
        self,
        node_ids: Optional[list[str]] = None,
        width: int = 800,
        height: int = 400,
        color: str = "#3498db",
        title: str = "Fréquence des codages par nœud",
    ) -> Optional[bytes]:
        """
        Génère un histogramme des fréquences de codage.

        Args:
            node_ids: Nœuds à inclure (None = tous)
            width: Largeur de l'image
            height: Hauteur de l'image
            color: Couleur des barres
            title: Titre du graphique

        Returns:
            Image PNG en bytes
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            return None

        # Récupérer les données
        if node_ids:
            nodes = [Node.get(self.db, nid) for nid in node_ids]
            nodes = [n for n in nodes if n]
        else:
            nodes = Node.get_all(self.db)

        names = []
        counts = []

        for node in nodes:
            ref_count = CodeReference.count_by_node(self.db, node.id)
            names.append(node.name)
            counts.append(ref_count)

        if not names:
            return None

        # Trier par fréquence décroissante
        sorted_data = sorted(zip(counts, names), reverse=True)
        counts, names = zip(*sorted_data) if sorted_data else ([], [])

        # Créer le graphique
        fig, ax = plt.subplots(figsize=(width / 100, height / 100))

        bars = ax.barh(range(len(names)), counts, color=color)
        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(names)
        ax.invert_yaxis()
        ax.set_xlabel("Nombre de références")
        ax.set_title(title)

        # Ajouter les valeurs sur les barres
        for bar, count in zip(bars, counts):
            ax.text(
                bar.get_width() + 0.5,
                bar.get_y() + bar.get_height() / 2,
                str(count),
                va="center",
            )

        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        plt.close()
        buf.seek(0)

        return buf.read()

    def source_type_pie(
        self,
        width: int = 600,
        height: int = 600,
        title: str = "Répartition des types de sources",
    ) -> Optional[bytes]:
        """
        Génère un camembert des types de sources.

        Returns:
            Image PNG en bytes
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            return None

        # Compter par type
        sources = Source.get_all(self.db)
        type_counts = {}

        for source in sources:
            type_name = source.type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        if not type_counts:
            return None

        labels = list(type_counts.keys())
        sizes = list(type_counts.values())

        fig, ax = plt.subplots(figsize=(width / 100, height / 100))

        ax.pie(
            sizes,
            labels=labels,
            autopct="%1.1f%%",
            startangle=90,
            colors=plt.cm.Set3.colors,
        )
        ax.set_title(title)

        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        plt.close()
        buf.seek(0)

        return buf.read()

    def coding_timeline(
        self,
        node_ids: Optional[list[str]] = None,
        width: int = 1000,
        height: int = 400,
    ) -> Optional[bytes]:
        """
        Génère une timeline des codages (si timestamps disponibles).

        Returns:
            Image PNG en bytes
        """
        try:
            import matplotlib.pyplot as plt
            from datetime import datetime
        except ImportError:
            return None

        # Récupérer les codages avec dates
        cursor = self.db.execute(
            "SELECT created_at FROM code_references ORDER BY created_at"
        )
        dates = []
        for row in cursor.fetchall():
            try:
                dt = datetime.fromisoformat(row["created_at"])
                dates.append(dt)
            except (ValueError, TypeError):
                continue

        if not dates:
            return None

        # Grouper par jour
        from collections import Counter

        date_counts = Counter(d.date() for d in dates)
        sorted_dates = sorted(date_counts.keys())
        counts = [date_counts[d] for d in sorted_dates]

        fig, ax = plt.subplots(figsize=(width / 100, height / 100))

        ax.plot(sorted_dates, counts, marker="o", color="#3498db")
        ax.fill_between(sorted_dates, counts, alpha=0.3)
        ax.set_xlabel("Date")
        ax.set_ylabel("Nombre de codages")
        ax.set_title("Évolution des codages dans le temps")

        plt.xticks(rotation=45)
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        plt.close()
        buf.seek(0)

        return buf.read()

    def matrix_heatmap(
        self,
        matrix_data: dict,
        width: int = 800,
        height: int = 600,
        colormap: str = "Blues",
        title: str = "Matrice de codage",
    ) -> Optional[bytes]:
        """
        Génère une heatmap à partir d'une matrice.

        Args:
            matrix_data: Données de matrice (de MatrixAnalysis)

        Returns:
            Image PNG en bytes
        """
        try:
            import matplotlib.pyplot as plt
            import numpy as np
        except ImportError:
            return None

        matrix = matrix_data.get("matrix", [])
        row_labels = matrix_data.get("row_labels", [])
        col_labels = matrix_data.get("col_labels", [])

        if not matrix:
            return None

        fig, ax = plt.subplots(figsize=(width / 100, height / 100))

        im = ax.imshow(matrix, cmap=colormap, aspect="auto")

        # Axes
        ax.set_xticks(range(len(col_labels)))
        ax.set_xticklabels(col_labels, rotation=45, ha="right")
        ax.set_yticks(range(len(row_labels)))
        ax.set_yticklabels(row_labels)

        # Colorbar
        plt.colorbar(im)

        # Valeurs dans les cellules
        for i in range(len(row_labels)):
            for j in range(len(col_labels)):
                value = matrix[i][j]
                if value > 0:
                    text_color = "white" if value > np.max(matrix) / 2 else "black"
                    ax.text(j, i, f"{value:.0f}", ha="center", va="center", color=text_color)

        ax.set_title(title)
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        plt.close()
        buf.seek(0)

        return buf.read()

    def node_hierarchy(
        self,
        width: int = 800,
        height: int = 600,
    ) -> Optional[bytes]:
        """
        Génère un diagramme de la hiérarchie des nœuds.

        Returns:
            Image PNG en bytes
        """
        try:
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches
        except ImportError:
            return None

        nodes = Node.get_tree(self.db)
        if not nodes:
            return None

        fig, ax = plt.subplots(figsize=(width / 100, height / 100))

        def draw_node(node, x, y, level, max_width):
            # Dessiner le nœud
            box = mpatches.FancyBboxPatch(
                (x - 0.1, y - 0.05),
                0.2,
                0.1,
                boxstyle="round,pad=0.01",
                facecolor=node.color,
                edgecolor="black",
            )
            ax.add_patch(box)
            ax.text(x, y, node.name, ha="center", va="center", fontsize=8)

            # Dessiner les enfants
            if node.children:
                child_width = max_width / len(node.children)
                start_x = x - max_width / 2 + child_width / 2

                for i, child in enumerate(node.children):
                    child_x = start_x + i * child_width
                    child_y = y - 0.2

                    # Ligne de connexion
                    ax.plot([x, child_x], [y - 0.05, child_y + 0.05], "k-", lw=0.5)

                    draw_node(child, child_x, child_y, level + 1, child_width)

        # Dessiner à partir des nœuds racines
        if nodes:
            root_width = 1.0 / len(nodes)
            for i, node in enumerate(nodes):
                x = (i + 0.5) * root_width
                draw_node(node, x, 0.9, 0, root_width)

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        ax.set_title("Hiérarchie des nœuds")

        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        plt.close()
        buf.seek(0)

        return buf.read()

    def save(self, output_path: Path, chart_type: str, **kwargs) -> bool:
        """Génère et sauvegarde un graphique."""
        generators = {
            "coding_frequency": self.coding_frequency_bar,
            "source_types": self.source_type_pie,
            "timeline": self.coding_timeline,
            "heatmap": self.matrix_heatmap,
            "hierarchy": self.node_hierarchy,
        }

        generator = generators.get(chart_type)
        if generator:
            image_data = generator(**kwargs)
            if image_data:
                Path(output_path).write_bytes(image_data)
                return True
        return False
