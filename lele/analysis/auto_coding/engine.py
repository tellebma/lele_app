"""Moteur principal pour la détection automatique de nœuds.

Ce module orchestre le pipeline complet d'auto-codage :
segmentation → embeddings → clustering → labeling → propositions.
"""

import re
import time
from typing import Callable

from ... import get_logger
from .clustering import ClusteringPipeline, find_similar_to_existing, merge_similar_clusters
from .embeddings import EmbeddingEngine
from .labeling import ThemeLabeler
from .models import (
    AutoCodingConfig,
    AutoCodingResult,
    LLMProvider,
    NodeProposal,
    Segment,
    SegmentationStrategy,
    get_theme_color,
)

logger = get_logger("analysis.auto_coding")


class AutoCodingEngine:
    """Moteur de détection automatique de nœuds.

    Orchestre le pipeline complet pour analyser des sources textuelles
    et proposer des nœuds de codage basés sur les thèmes détectés.
    """

    def __init__(
        self,
        embedding_model: str | None = None,
        llm_provider: LLMProvider = LLMProvider.LOCAL_OLLAMA,
        llm_model: str = "mistral",
        ollama_url: str = "http://localhost:11434",
        api_key: str | None = None,
    ):
        """Initialise le moteur d'auto-codage.

        Args:
            embedding_model: Modèle pour les embeddings (sentence-transformers)
            llm_provider: Fournisseur de LLM pour le labeling
            llm_model: Modèle LLM à utiliser
            ollama_url: URL du serveur Ollama
            api_key: Clé API pour Anthropic/OpenAI
        """
        self.embedding_engine = EmbeddingEngine(model_name=embedding_model)
        self.labeler = ThemeLabeler(
            provider=llm_provider,
            model=llm_model,
            ollama_url=ollama_url,
            api_key=api_key,
        )
        self._spacy_nlp = None

    def analyze(
        self,
        sources: list[dict],
        config: AutoCodingConfig,
        existing_nodes: list[dict] | None = None,
        progress_callback: Callable[[float, str], None] | None = None,
    ) -> AutoCodingResult:
        """Exécute l'analyse complète d'auto-codage.

        Args:
            sources: Liste de dicts avec 'id', 'name', 'content'
            config: Configuration de l'analyse
            existing_nodes: Nœuds existants pour détection de doublons
            progress_callback: Callback (progress 0-1, message)

        Returns:
            Résultat avec les propositions de nœuds
        """
        start_time = time.time()
        existing_nodes = existing_nodes or []

        logger.info(
            f"Démarrage auto-codage: {len(sources)} sources, "
            f"max_themes={config.max_themes}, provider={config.llm_provider.value}"
        )

        # Étape 1 : Segmentation
        if progress_callback:
            progress_callback(0.05, "Segmentation des sources...")

        segments = self._segment_sources(sources, config)
        logger.info(f"Segmentation: {len(segments)} segments créés")

        if not segments:
            logger.warning("Aucun segment créé, abandon de l'analyse")
            return AutoCodingResult(
                proposals=[],
                config=config,
                total_segments=0,
            )

        # Étape 2 : Embeddings
        if progress_callback:
            progress_callback(0.15, f"Vectorisation de {len(segments)} segments...")

        def embedding_progress(p, msg):
            if progress_callback:
                progress_callback(0.15 + p * 0.35, msg)

        self.embedding_engine.load_model(embedding_progress)
        self.embedding_engine.encode_segments(segments, progress_callback=embedding_progress)
        logger.info(f"Embeddings générés pour {len(segments)} segments")

        # Étape 3 : Clustering
        if progress_callback:
            progress_callback(0.50, "Clustering des segments...")

        def clustering_progress(p, msg):
            if progress_callback:
                progress_callback(0.50 + p * 0.20, msg)

        clustering = ClusteringPipeline(
            min_cluster_size=config.min_cluster_size,
            min_samples=config.min_samples,
            n_components=config.umap_n_components,
            n_neighbors=config.umap_n_neighbors,
        )

        clusters, noise_segments = clustering.cluster_segments(
            segments,
            max_clusters=config.max_themes,
            progress_callback=clustering_progress,
        )
        logger.info(
            f"Clustering: {len(clusters)} clusters, {len(noise_segments)} segments bruit"
        )

        if not clusters:
            logger.warning("Aucun cluster détecté")
            return AutoCodingResult(
                proposals=[],
                config=config,
                total_segments=len(segments),
                clustered_segments=0,
                noise_segments=len(segments),
                processing_time_seconds=time.time() - start_time,
            )

        # Étape 3b : Fusion des clusters similaires
        if config.merge_similar_themes and len(clusters) > 1:
            if progress_callback:
                progress_callback(0.70, "Fusion des thèmes similaires...")
            clusters = merge_similar_clusters(clusters, threshold=0.8)

        # Étape 4 : Labeling
        if progress_callback:
            progress_callback(0.75, "Génération des noms de thèmes...")

        def labeling_progress(p, msg):
            if progress_callback:
                progress_callback(0.75 + p * 0.15, msg)

        # Mettre à jour le provider du labeler selon la config
        self.labeler.provider = config.llm_provider
        self.labeler.model = config.llm_model

        labels = self.labeler.label_clusters(
            clusters,
            max_excerpts=5,
            progress_callback=labeling_progress,
        )

        # Étape 5 : Créer les propositions
        if progress_callback:
            progress_callback(0.90, "Création des propositions...")

        # Préparer les embeddings des nœuds existants pour la détection de doublons
        existing_embeddings = []
        existing_names = []
        existing_ids = []

        if existing_nodes and config.similarity_threshold < 1.0:
            for node in existing_nodes:
                # Encoder le nom du nœud
                name_embedding = self.embedding_engine.encode_text(node["name"])
                existing_embeddings.append(name_embedding)
                existing_names.append(node["name"])
                existing_ids.append(node["id"])

        proposals = []
        for i, (cluster, label) in enumerate(zip(clusters, labels)):
            # Chercher un nœud existant similaire
            match_id, match_name, match_sim = None, None, 0.0
            if existing_embeddings:
                match_id, match_name, match_sim = find_similar_to_existing(
                    cluster,
                    existing_embeddings,
                    existing_names,
                    existing_ids,
                    threshold=config.similarity_threshold,
                )

            proposal = NodeProposal(
                suggested_name=label.name,
                description=label.description,
                segments=cluster.segments,
                confidence=cluster.coherence_score,
                cluster_id=cluster.cluster_id,
                keywords=label.keywords,
                color=get_theme_color(i),
                existing_node_id=match_id,
                existing_node_name=match_name,
                similarity_to_existing=match_sim,
                is_selected=cluster.coherence_score >= config.confidence_threshold,
            )
            proposals.append(proposal)

        # Trier par confiance décroissante
        proposals.sort(key=lambda p: p.confidence, reverse=True)

        if progress_callback:
            progress_callback(1.0, f"{len(proposals)} thèmes détectés")

        # Calculer les statistiques
        clustered_count = sum(len(c.segments) for c in clusters)
        elapsed = time.time() - start_time
        logger.info(
            f"Auto-codage terminé en {elapsed:.1f}s: "
            f"{len(proposals)} propositions, {clustered_count} segments classés"
        )

        return AutoCodingResult(
            proposals=proposals,
            config=config,
            total_segments=len(segments),
            clustered_segments=clustered_count,
            noise_segments=len(noise_segments),
            processing_time_seconds=time.time() - start_time,
        )

    def _segment_sources(
        self,
        sources: list[dict],
        config: AutoCodingConfig,
    ) -> list[Segment]:
        """Segmente les sources selon la stratégie configurée.

        Args:
            sources: Liste de sources avec 'id', 'name', 'content'
            config: Configuration avec la stratégie de segmentation

        Returns:
            Liste de segments
        """
        segments = []

        for source in sources:
            source_id = source["id"]
            source_name = source.get("name", "")
            content = source.get("content", "")

            if not content:
                continue

            source_segments = self._segment_text(
                text=content,
                source_id=source_id,
                source_name=source_name,
                strategy=config.segmentation_strategy,
                min_length=config.min_segment_length,
                max_length=config.max_segment_length,
            )
            segments.extend(source_segments)

        return segments

    def _segment_text(
        self,
        text: str,
        source_id: str,
        source_name: str,
        strategy: SegmentationStrategy,
        min_length: int,
        max_length: int,
    ) -> list[Segment]:
        """Découpe un texte en segments selon la stratégie.

        Args:
            text: Texte à segmenter
            source_id: ID de la source
            source_name: Nom de la source
            strategy: Stratégie de segmentation
            min_length: Longueur minimum d'un segment
            max_length: Longueur maximum d'un segment

        Returns:
            Liste de segments
        """
        raw_segments: list[tuple[str, int, int]] = []  # (text, start, end)

        if strategy == SegmentationStrategy.PARAGRAPH:
            raw_segments = self._split_by_paragraphs(text)
        elif strategy == SegmentationStrategy.SENTENCE:
            raw_segments = self._split_by_sentences(text)
        elif strategy == SegmentationStrategy.FIXED_WINDOW:
            raw_segments = self._split_by_window(text, window_size=200, overlap=50)
        else:
            raw_segments = self._split_by_paragraphs(text)

        # Normaliser les segments (fusion des trop courts, découpe des trop longs)
        normalized = self._normalize_segments(
            raw_segments, min_length, max_length
        )

        # Créer les objets Segment
        segments = []
        for i, (seg_text, start, end) in enumerate(normalized):
            segments.append(
                Segment(
                    text=seg_text.strip(),
                    source_id=source_id,
                    source_name=source_name,
                    start_char=start,
                    end_char=end,
                    paragraph_index=i,
                )
            )

        return segments

    def _split_by_paragraphs(self, text: str) -> list[tuple[str, int, int]]:
        """Découpe par paragraphes (double saut de ligne)."""
        segments = []
        pattern = r"\n\s*\n"

        last_end = 0
        for match in re.finditer(pattern, text):
            start = last_end
            end = match.start()
            if start < end:
                segments.append((text[start:end], start, end))
            last_end = match.end()

        # Dernier segment
        if last_end < len(text):
            segments.append((text[last_end:], last_end, len(text)))

        return segments

    def _split_by_sentences(self, text: str) -> list[tuple[str, int, int]]:
        """Découpe par phrases."""
        # Utiliser spaCy si disponible pour une meilleure segmentation
        try:
            if self._spacy_nlp is None:
                import spacy
                try:
                    self._spacy_nlp = spacy.load("fr_core_news_sm")
                except OSError:
                    self._spacy_nlp = spacy.blank("fr")
                    self._spacy_nlp.add_pipe("sentencizer")

            doc = self._spacy_nlp(text)
            segments = []
            for sent in doc.sents:
                segments.append((sent.text, sent.start_char, sent.end_char))
            return segments

        except ImportError:
            # Fallback sur regex simple
            pattern = r"[.!?]+\s+"
            segments = []
            last_end = 0

            for match in re.finditer(pattern, text):
                end = match.end()
                if last_end < end:
                    segments.append((text[last_end:end].strip(), last_end, end))
                last_end = end

            if last_end < len(text):
                segments.append((text[last_end:].strip(), last_end, len(text)))

            return segments

    def _split_by_window(
        self, text: str, window_size: int = 200, overlap: int = 50
    ) -> list[tuple[str, int, int]]:
        """Découpe par fenêtre glissante de mots."""
        words = text.split()
        segments = []

        i = 0
        while i < len(words):
            end_idx = min(i + window_size, len(words))
            window_words = words[i:end_idx]
            window_text = " ".join(window_words)

            # Calculer les positions approximatives
            start_char = len(" ".join(words[:i])) + (1 if i > 0 else 0)
            end_char = start_char + len(window_text)

            segments.append((window_text, start_char, end_char))

            i += window_size - overlap
            if i >= len(words):
                break

        return segments

    def _normalize_segments(
        self,
        segments: list[tuple[str, int, int]],
        min_length: int,
        max_length: int,
    ) -> list[tuple[str, int, int]]:
        """Normalise les segments : fusionne les courts, découpe les longs."""
        normalized = []
        buffer_text = ""
        buffer_start = 0

        for text, start, end in segments:
            text = text.strip()
            if not text:
                continue

            if len(text) < min_length:
                # Accumuler dans le buffer
                if not buffer_text:
                    buffer_start = start
                buffer_text += " " + text if buffer_text else text
            else:
                # Vider le buffer d'abord
                if buffer_text:
                    if len(buffer_text) >= min_length:
                        normalized.append((buffer_text, buffer_start, start))
                    buffer_text = ""

                # Traiter le segment actuel
                if len(text) > max_length:
                    # Découper en morceaux
                    chunks = self._split_long_text(text, max_length)
                    pos = start
                    for chunk in chunks:
                        chunk_end = pos + len(chunk)
                        normalized.append((chunk, pos, chunk_end))
                        pos = chunk_end
                else:
                    normalized.append((text, start, end))

        # Vider le buffer final
        if buffer_text and len(buffer_text) >= min_length:
            normalized.append((buffer_text, buffer_start, len(buffer_text) + buffer_start))

        return normalized

    def _split_long_text(self, text: str, max_length: int) -> list[str]:
        """Découpe un texte trop long en morceaux."""
        chunks = []
        words = text.split()
        current_chunk = []
        current_length = 0

        for word in words:
            word_length = len(word) + 1  # +1 pour l'espace
            if current_length + word_length > max_length and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_length = len(word)
            else:
                current_chunk.append(word)
                current_length += word_length

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks


def create_nodes_from_proposals(
    db,
    proposals: list[NodeProposal],
    parent_id: str | None = None,
) -> list[dict]:
    """Crée les nœuds en base de données à partir des propositions validées.

    Args:
        db: Connexion à la base de données du projet
        proposals: Liste des propositions (seules les sélectionnées seront créées)
        parent_id: ID du nœud parent (pour créer dans un dossier)

    Returns:
        Liste des nœuds créés avec leurs IDs
    """
    from lele.models.coding import CodeReference
    from lele.models.node import Node

    created_nodes = []

    for proposal in proposals:
        if not proposal.is_selected:
            continue

        # Utiliser le nœud existant si c'est une fusion
        if proposal.existing_node_id and proposal.similarity_to_existing >= 0.75:
            node_id = proposal.existing_node_id
            node_name = proposal.existing_node_name
        else:
            # Créer un nouveau nœud
            node = Node(
                name=proposal.display_name,
                description=proposal.description,
                color=proposal.color,
                parent_id=parent_id,
            )
            node.save(db)
            node_id = node.id
            node_name = node.name

            created_nodes.append({
                "id": node_id,
                "name": node_name,
                "is_new": True,
            })

        # Créer les références de codage
        for segment in proposal.segments:
            ref = CodeReference(
                node_id=node_id,
                source_id=segment.source_id,
                start_pos=segment.start_char,
                end_pos=segment.end_char,
                content=segment.text[:500],  # Limiter la taille du contenu
            )
            ref.save(db)

    return created_nodes


def check_dependencies() -> dict:
    """Vérifie toutes les dépendances requises pour l'auto-codage.

    Returns:
        Dict avec l'état de chaque dépendance
    """
    from .clustering import check_clustering_dependencies
    from .embeddings import check_sentence_transformers, check_torch_device
    from .labeling import check_ollama_available

    st_ok, st_msg = check_sentence_transformers()
    cluster_ok, cluster_msg = check_clustering_dependencies()
    ollama_ok, ollama_msg = check_ollama_available()
    torch_info = check_torch_device()

    return {
        "sentence_transformers": {"available": st_ok, "message": st_msg},
        "clustering": {"available": cluster_ok, "message": cluster_msg},
        "ollama": {"available": ollama_ok, "message": ollama_msg},
        "torch_device": torch_info,
        "all_required_ok": st_ok and cluster_ok,
        "llm_available": ollama_ok,
    }
