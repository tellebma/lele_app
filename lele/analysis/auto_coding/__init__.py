"""Module de détection automatique de nœuds pour l'analyse qualitative.

Ce module fournit un pipeline complet pour détecter automatiquement
des thèmes dans des textes et proposer des nœuds de codage.

Architecture :
    - models.py : Structures de données (Segment, NodeProposal, etc.)
    - embeddings.py : Vectorisation avec sentence-transformers
    - clustering.py : Clustering UMAP + HDBSCAN
    - labeling.py : Génération de noms par LLM ou mots-clés
    - engine.py : Orchestration du pipeline complet

Exemple d'utilisation :
    >>> from lele.analysis.auto_coding import AutoCodingEngine, AutoCodingConfig
    >>>
    >>> engine = AutoCodingEngine(
    ...     llm_provider=LLMProvider.LOCAL_OLLAMA,
    ...     llm_model="mistral"
    ... )
    >>>
    >>> config = AutoCodingConfig(
    ...     source_ids=["source-1", "source-2"],
    ...     max_themes=15,
    ...     min_cluster_size=3,
    ... )
    >>>
    >>> sources = [
    ...     {"id": "source-1", "name": "Entretien 1", "content": "..."},
    ...     {"id": "source-2", "name": "Entretien 2", "content": "..."},
    ... ]
    >>>
    >>> result = engine.analyze(sources, config)
    >>> for proposal in result.proposals:
    ...     print(f"{proposal.suggested_name}: {proposal.segment_count} segments")
"""

from .models import (
    AutoCodingConfig,
    AutoCodingResult,
    ClusterResult,
    LLMLabelingResult,
    LLMProvider,
    NodeProposal,
    Segment,
    SegmentationStrategy,
    get_theme_color,
)

from .embeddings import (
    EmbeddingEngine,
    check_sentence_transformers,
    check_torch_device,
    clear_embedding_cache,
)

from .clustering import (
    ClusteringPipeline,
    check_clustering_dependencies,
    merge_similar_clusters,
)

from .labeling import (
    ThemeLabeler,
    check_ollama_available,
    get_ollama_models,
    download_ollama_model,
    RECOMMENDED_OLLAMA_MODELS,
)

from .engine import (
    AutoCodingEngine,
    check_dependencies,
    create_nodes_from_proposals,
)

__all__ = [
    # Models
    "Segment",
    "ClusterResult",
    "NodeProposal",
    "AutoCodingConfig",
    "AutoCodingResult",
    "LLMLabelingResult",
    "SegmentationStrategy",
    "LLMProvider",
    "get_theme_color",
    # Embeddings
    "EmbeddingEngine",
    "check_sentence_transformers",
    "check_torch_device",
    "clear_embedding_cache",
    # Clustering
    "ClusteringPipeline",
    "check_clustering_dependencies",
    "merge_similar_clusters",
    # Labeling
    "ThemeLabeler",
    "check_ollama_available",
    "get_ollama_models",
    "download_ollama_model",
    "RECOMMENDED_OLLAMA_MODELS",
    # Engine
    "AutoCodingEngine",
    "check_dependencies",
    "create_nodes_from_proposals",
]
