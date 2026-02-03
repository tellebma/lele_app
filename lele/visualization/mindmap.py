"""Génération de cartes mentales (mindmaps)."""

import io
import json
import math
from pathlib import Path
from typing import Optional

# Imports matplotlib (optionnels)
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from ..models.node import Node
from ..models.coding import CodeReference


class MindMapGenerator:
    """Génère des cartes mentales à partir des nœuds."""

    def __init__(self, db):
        self.db = db

    def generate(
        self,
        root_node_id: Optional[str] = None,
        width: int = 1200,
        height: int = 800,
        show_references: bool = True,
    ) -> Optional[bytes]:
        """
        Génère une carte mentale des nœuds.

        Args:
            root_node_id: ID du nœud racine (None = tous les nœuds racines)
            width: Largeur de l'image
            height: Hauteur de l'image
            show_references: Afficher le nombre de références

        Returns:
            Image PNG en bytes
        """
        if not MATPLOTLIB_AVAILABLE:
            return None

        if root_node_id:
            root = Node.get(self.db, root_node_id)
            if root:
                root.children = Node._get_children_recursive(self.db, root.id)
                nodes = [root]
            else:
                return None
        else:
            nodes = Node.get_tree(self.db)

        if not nodes:
            return None

        fig, ax = plt.subplots(figsize=(width / 100, height / 100))

        # Calculer les positions
        positions = self._calculate_positions(nodes, width, height)

        # Dessiner les connexions d'abord (arrière-plan)
        self._draw_connections(ax, nodes, positions)

        # Dessiner les nœuds
        self._draw_nodes(ax, nodes, positions, show_references)

        ax.set_xlim(0, width)
        ax.set_ylim(0, height)
        ax.axis("off")
        ax.set_aspect("equal")

        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        plt.close()
        buf.seek(0)

        return buf.read()

    def _calculate_positions(
        self, nodes: list[Node], width: int, height: int
    ) -> dict[str, tuple[float, float]]:
        """Calcule les positions des nœuds."""
        positions = {}

        def place_node(node, center_x, center_y, angle_start, angle_range, radius, level):
            positions[node.id] = (center_x, center_y)

            if node.children:
                n_children = len(node.children)
                angle_step = angle_range / max(n_children, 1)
                child_radius = radius * 0.7

                for i, child in enumerate(node.children):
                    angle = angle_start + (i + 0.5) * angle_step
                    child_x = center_x + child_radius * math.cos(math.radians(angle))
                    child_y = center_y + child_radius * math.sin(math.radians(angle))

                    place_node(
                        child,
                        child_x,
                        child_y,
                        angle - angle_step / 2,
                        angle_step,
                        child_radius,
                        level + 1,
                    )

        # Placer les nœuds racines
        center_x = width / 2
        center_y = height / 2
        n_roots = len(nodes)
        angle_per_root = 360 / max(n_roots, 1)
        radius = min(width, height) * 0.35

        for i, node in enumerate(nodes):
            if n_roots == 1:
                # Un seul nœud racine au centre
                place_node(node, center_x, center_y, 0, 360, radius, 0)
            else:
                angle = i * angle_per_root
                node_x = center_x + radius * 0.3 * math.cos(math.radians(angle))
                node_y = center_y + radius * 0.3 * math.sin(math.radians(angle))
                place_node(
                    node,
                    node_x,
                    node_y,
                    angle - angle_per_root / 2,
                    angle_per_root,
                    radius,
                    0,
                )

        return positions

    def _draw_connections(self, ax, nodes: list[Node], positions: dict):
        """Dessine les lignes de connexion."""

        def draw_recursive(node):
            if node.id not in positions:
                return

            parent_pos = positions[node.id]

            for child in node.children:
                if child.id in positions:
                    child_pos = positions[child.id]
                    ax.plot(
                        [parent_pos[0], child_pos[0]],
                        [parent_pos[1], child_pos[1]],
                        color="#cccccc",
                        linewidth=1.5,
                        zorder=1,
                    )
                    draw_recursive(child)

        for node in nodes:
            draw_recursive(node)

    def _draw_nodes(self, ax, nodes: list[Node], positions: dict, show_references: bool):
        """Dessine les nœuds."""

        def draw_recursive(node, level=0):
            if node.id not in positions:
                return

            pos = positions[node.id]

            # Taille du nœud basée sur le niveau
            size = 80 - level * 10
            size = max(size, 40)

            # Dessiner le cercle
            circle = mpatches.Circle(
                pos,
                size / 2,
                color=node.color,
                ec="white",
                linewidth=2,
                zorder=2,
            )
            ax.add_patch(circle)

            # Texte du nœud
            label = node.name
            if len(label) > 15:
                label = label[:12] + "..."

            ax.text(
                pos[0],
                pos[1],
                label,
                ha="center",
                va="center",
                fontsize=max(8, 12 - level),
                fontweight="bold",
                color="white",
                zorder=3,
            )

            # Nombre de références
            if show_references and node.reference_count > 0:
                ax.text(
                    pos[0] + size / 2,
                    pos[1] + size / 2,
                    str(node.reference_count),
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="#666666",
                    bbox=dict(boxstyle="circle", facecolor="white", edgecolor="#cccccc"),
                    zorder=4,
                )

            for child in node.children:
                draw_recursive(child, level + 1)

        for node in nodes:
            draw_recursive(node)

    def export_json(self, root_node_id: Optional[str] = None) -> str:
        """
        Exporte la carte mentale en JSON (compatible avec d3.js, etc.)

        Returns:
            JSON string
        """
        if root_node_id:
            root = Node.get(self.db, root_node_id)
            if root:
                root.children = Node._get_children_recursive(self.db, root.id)
                nodes = [root]
            else:
                return "{}"
        else:
            nodes = Node.get_tree(self.db)

        def node_to_dict(node):
            return {
                "id": node.id,
                "name": node.name,
                "color": node.color,
                "references": node.reference_count,
                "children": [node_to_dict(c) for c in node.children],
            }

        data = {"name": "Root", "children": [node_to_dict(n) for n in nodes]}

        return json.dumps(data, indent=2, ensure_ascii=False)

    def export_html(
        self,
        output_path: Path,
        root_node_id: Optional[str] = None,
    ) -> bool:
        """
        Exporte une carte mentale interactive en HTML (utilise D3.js).

        Returns:
            True si succès
        """
        json_data = self.export_json(root_node_id)

        html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Mind Map</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body { margin: 0; overflow: hidden; }
        .node circle { cursor: pointer; }
        .node text { font: 12px sans-serif; }
        .link { fill: none; stroke: #ccc; stroke-width: 1.5px; }
    </style>
</head>
<body>
    <svg id="mindmap"></svg>
    <script>
        const data = DATA_PLACEHOLDER;

        const width = window.innerWidth;
        const height = window.innerHeight;

        const svg = d3.select("#mindmap")
            .attr("width", width)
            .attr("height", height);

        const g = svg.append("g")
            .attr("transform", `translate(${width/2},${height/2})`);

        const tree = d3.tree()
            .size([2 * Math.PI, Math.min(width, height) / 2 - 100])
            .separation((a, b) => (a.parent == b.parent ? 1 : 2) / a.depth);

        const root = d3.hierarchy(data);
        tree(root);

        // Links
        g.selectAll(".link")
            .data(root.links())
            .join("path")
            .attr("class", "link")
            .attr("d", d3.linkRadial()
                .angle(d => d.x)
                .radius(d => d.y));

        // Nodes
        const node = g.selectAll(".node")
            .data(root.descendants())
            .join("g")
            .attr("class", "node")
            .attr("transform", d => `rotate(${d.x * 180 / Math.PI - 90}) translate(${d.y},0)`);

        node.append("circle")
            .attr("r", d => d.data.references ? Math.max(5, Math.min(20, d.data.references)) : 5)
            .attr("fill", d => d.data.color || "#3498db");

        node.append("text")
            .attr("dy", "0.31em")
            .attr("x", d => d.x < Math.PI === !d.children ? 6 : -6)
            .attr("text-anchor", d => d.x < Math.PI === !d.children ? "start" : "end")
            .attr("transform", d => d.x >= Math.PI ? "rotate(180)" : null)
            .text(d => d.data.name);
    </script>
</body>
</html>
        """.replace("DATA_PLACEHOLDER", json_data)

        Path(output_path).write_text(html_template)
        return True

    def save(self, output_path: Path, **kwargs) -> bool:
        """Génère et sauvegarde une carte mentale."""
        image_data = self.generate(**kwargs)
        if image_data:
            Path(output_path).write_bytes(image_data)
            return True
        return False
