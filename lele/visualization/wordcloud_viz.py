"""Génération de nuages de mots."""

from pathlib import Path
from typing import Optional
import io

from ..analysis.search import SearchEngine


class WordCloudGenerator:
    """Génère des nuages de mots à partir des données."""

    def __init__(self, db):
        self.db = db
        self.search_engine = SearchEngine(db)

    def generate(
        self,
        source_ids: Optional[list[str]] = None,
        node_ids: Optional[list[str]] = None,
        width: int = 800,
        height: int = 400,
        max_words: int = 100,
        min_font_size: int = 10,
        max_font_size: int = 100,
        background_color: str = "white",
        colormap: str = "viridis",
        exclude_words: Optional[set[str]] = None,
    ) -> Optional[bytes]:
        """
        Génère un nuage de mots.

        Args:
            source_ids: Sources à analyser (None = toutes)
            node_ids: Limiter aux passages codés avec ces nœuds
            width: Largeur de l'image
            height: Hauteur de l'image
            max_words: Nombre maximum de mots
            min_font_size: Taille minimale de police
            max_font_size: Taille maximale de police
            background_color: Couleur de fond
            colormap: Palette de couleurs matplotlib
            exclude_words: Mots à exclure

        Returns:
            Image PNG en bytes ou None si erreur
        """
        try:
            from wordcloud import WordCloud
            import matplotlib.pyplot as plt
        except ImportError:
            return None

        # Obtenir les fréquences de mots
        if node_ids:
            frequencies = self._get_frequencies_from_codes(node_ids, exclude_words)
        else:
            frequencies = self.search_engine.get_word_frequencies(
                source_ids=source_ids,
                exclude_words=exclude_words,
            )

        if not frequencies:
            return None

        # Créer le nuage de mots
        wc = WordCloud(
            width=width,
            height=height,
            max_words=max_words,
            min_font_size=min_font_size,
            max_font_size=max_font_size,
            background_color=background_color,
            colormap=colormap,
        )

        wc.generate_from_frequencies(frequencies)

        # Convertir en image PNG
        buf = io.BytesIO()
        plt.figure(figsize=(width / 100, height / 100))
        plt.imshow(wc, interpolation="bilinear")
        plt.axis("off")
        plt.tight_layout(pad=0)
        plt.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        plt.close()
        buf.seek(0)

        return buf.read()

    def _get_frequencies_from_codes(
        self, node_ids: list[str], exclude_words: Optional[set[str]]
    ) -> dict[str, int]:
        """Calcule les fréquences à partir des passages codés."""
        import re

        if exclude_words is None:
            exclude_words = self.search_engine._get_stop_words()

        frequencies = {}
        word_pattern = re.compile(r"\b[a-zA-ZÀ-ÿ]+\b")

        from ..models.coding import CodeReference

        for node_id in node_ids:
            refs = CodeReference.get_by_node(self.db, node_id)
            for ref in refs:
                if ref.content:
                    words = word_pattern.findall(ref.content.lower())
                    for word in words:
                        if len(word) >= 3 and word not in exclude_words:
                            frequencies[word] = frequencies.get(word, 0) + 1

        return frequencies

    def generate_comparison(
        self,
        group1_source_ids: list[str],
        group2_source_ids: list[str],
        width: int = 800,
        height: int = 400,
    ) -> Optional[bytes]:
        """
        Génère deux nuages de mots côte à côte pour comparaison.

        Args:
            group1_source_ids: Sources du groupe 1
            group2_source_ids: Sources du groupe 2

        Returns:
            Image PNG en bytes
        """
        try:
            from wordcloud import WordCloud
            import matplotlib.pyplot as plt
        except ImportError:
            return None

        freq1 = self.search_engine.get_word_frequencies(source_ids=group1_source_ids)
        freq2 = self.search_engine.get_word_frequencies(source_ids=group2_source_ids)

        if not freq1 and not freq2:
            return None

        fig, axes = plt.subplots(1, 2, figsize=(width / 50, height / 100))

        # Groupe 1
        if freq1:
            wc1 = WordCloud(width=width // 2, height=height, background_color="white")
            wc1.generate_from_frequencies(freq1)
            axes[0].imshow(wc1, interpolation="bilinear")
            axes[0].set_title("Groupe 1")
        axes[0].axis("off")

        # Groupe 2
        if freq2:
            wc2 = WordCloud(width=width // 2, height=height, background_color="white")
            wc2.generate_from_frequencies(freq2)
            axes[1].imshow(wc2, interpolation="bilinear")
            axes[1].set_title("Groupe 2")
        axes[1].axis("off")

        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        plt.close()
        buf.seek(0)

        return buf.read()

    def save(
        self,
        output_path: Path,
        source_ids: Optional[list[str]] = None,
        **kwargs,
    ) -> bool:
        """Génère et sauvegarde un nuage de mots."""
        image_data = self.generate(source_ids=source_ids, **kwargs)
        if image_data:
            Path(output_path).write_bytes(image_data)
            return True
        return False
