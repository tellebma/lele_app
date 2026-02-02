"""Modèles de données pour la détection automatique de nœuds.

Ce module définit les structures de données utilisées par le pipeline
d'auto-codage : segments, thèmes proposés, résultats de clustering, etc.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class SegmentationStrategy(Enum):
    """Stratégie de segmentation du texte."""

    PARAGRAPH = "paragraph"      # Découpe par \n\n
    SENTENCE = "sentence"        # Découpe phrase par phrase
    SEMANTIC = "semantic"        # Découpe par cohérence sémantique (avancé)
    FIXED_WINDOW = "window"      # Fenêtre glissante (N tokens)


class LLMProvider(Enum):
    """Fournisseur de LLM pour le labeling."""

    LOCAL_OLLAMA = "ollama"           # Ollama (Mistral, Llama, etc.)
    LOCAL_LLAMACPP = "llamacpp"       # llama.cpp directement
    API_ANTHROPIC = "anthropic"       # Claude API
    API_OPENAI = "openai"             # OpenAI API
    NONE = "none"                     # Labeling par mots-clés uniquement


@dataclass
class Segment:
    """Un segment de texte extrait d'une source pour l'analyse.

    Représente une unité de texte qui sera vectorisée et clusterisée.
    """

    text: str
    source_id: str
    start_char: int
    end_char: int
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    embedding: list[float] | None = None

    # Métadonnées optionnelles
    source_name: str = ""
    paragraph_index: int = 0

    def __len__(self) -> int:
        return len(self.text)

    @property
    def preview(self) -> str:
        """Retourne un aperçu tronqué du texte."""
        if len(self.text) <= 100:
            return self.text
        return self.text[:97] + "..."


@dataclass
class ClusterResult:
    """Résultat du clustering pour un groupe de segments.

    Représente un cluster identifié par l'algorithme HDBSCAN.
    """

    cluster_id: int
    segments: list[Segment]
    centroid: list[float]
    coherence_score: float  # 0-1, mesure de cohésion intra-cluster

    @property
    def size(self) -> int:
        return len(self.segments)

    def get_representative_segments(self, n: int = 3) -> list[Segment]:
        """Retourne les N segments les plus proches du centroïde."""
        if not self.segments or self.centroid is None:
            return self.segments[:n]

        # Sera implémenté avec le calcul de distance
        return self.segments[:n]


@dataclass
class NodeProposal:
    """Proposition de nœud générée par l'auto-codage.

    Représente un thème détecté avec ses segments associés,
    prêt pour validation par l'utilisateur.
    """

    suggested_name: str
    description: str
    segments: list[Segment]
    confidence: float  # 0-1
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Métadonnées du clustering
    cluster_id: int = -1
    keywords: list[str] = field(default_factory=list)
    color: str = "#3498db"

    # Lien avec nœuds existants
    existing_node_id: str | None = None
    existing_node_name: str | None = None
    similarity_to_existing: float = 0.0

    # État de validation
    is_selected: bool = True
    is_validated: bool = False
    user_edited_name: str | None = None

    @property
    def display_name(self) -> str:
        """Retourne le nom à afficher (édité par l'utilisateur ou suggéré)."""
        return self.user_edited_name or self.suggested_name

    @property
    def segment_count(self) -> int:
        return len(self.segments)

    @property
    def confidence_level(self) -> str:
        """Retourne le niveau de confiance en texte."""
        if self.confidence >= 0.9:
            return "Très élevé"
        elif self.confidence >= 0.7:
            return "Élevé"
        elif self.confidence >= 0.5:
            return "Moyen"
        else:
            return "Faible"

    @property
    def has_existing_match(self) -> bool:
        """Vérifie si ce thème correspond à un nœud existant."""
        return self.existing_node_id is not None


@dataclass
class AutoCodingConfig:
    """Configuration pour l'exécution de l'auto-codage.

    Regroupe tous les paramètres utilisateur pour l'analyse.
    """

    # Sources à analyser
    source_ids: list[str] = field(default_factory=list)

    # Segmentation
    segmentation_strategy: SegmentationStrategy = SegmentationStrategy.PARAGRAPH
    min_segment_length: int = 50
    max_segment_length: int = 500

    # Clustering
    min_cluster_size: int = 3
    min_samples: int = 2
    max_themes: int = 20
    umap_n_neighbors: int = 15
    umap_n_components: int = 5

    # Seuils
    confidence_threshold: float = 0.6
    similarity_threshold: float = 0.75  # Pour matcher avec nœuds existants

    # LLM pour labeling
    llm_provider: LLMProvider = LLMProvider.LOCAL_OLLAMA
    llm_model: str = "mistral"

    # Options
    exclude_already_coded: bool = True
    merge_similar_themes: bool = True
    create_in_folder: str | None = None  # ID du nœud parent


@dataclass
class AutoCodingResult:
    """Résultat complet d'une analyse d'auto-codage.

    Contient toutes les propositions de nœuds et les métadonnées
    de l'analyse pour affichage et validation.
    """

    proposals: list[NodeProposal]
    config: AutoCodingConfig
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)

    # Statistiques
    total_segments: int = 0
    clustered_segments: int = 0
    noise_segments: int = 0
    processing_time_seconds: float = 0.0

    # État
    is_applied: bool = False
    applied_at: datetime | None = None

    @property
    def selected_proposals(self) -> list[NodeProposal]:
        """Retourne les propositions sélectionnées par l'utilisateur."""
        return [p for p in self.proposals if p.is_selected]

    @property
    def total_selected_segments(self) -> int:
        """Nombre total de segments dans les propositions sélectionnées."""
        return sum(p.segment_count for p in self.selected_proposals)

    @property
    def coverage_percentage(self) -> float:
        """Pourcentage de segments couverts par les clusters."""
        if self.total_segments == 0:
            return 0.0
        return (self.clustered_segments / self.total_segments) * 100


@dataclass
class LLMLabelingResult:
    """Résultat du labeling par LLM pour un cluster."""

    name: str
    description: str
    keywords: list[str]
    raw_response: str = ""
    model_used: str = ""
    success: bool = True
    error_message: str = ""


# Couleurs distinctes pour les thèmes générés
THEME_COLORS = [
    "#3498db",  # Bleu
    "#2ecc71",  # Vert
    "#e74c3c",  # Rouge
    "#9b59b6",  # Violet
    "#f39c12",  # Orange
    "#1abc9c",  # Turquoise
    "#e91e63",  # Rose
    "#00bcd4",  # Cyan
    "#8bc34a",  # Vert clair
    "#ff5722",  # Orange foncé
    "#673ab7",  # Violet foncé
    "#009688",  # Teal
    "#ffeb3b",  # Jaune
    "#795548",  # Marron
    "#607d8b",  # Gris bleu
    "#ff9800",  # Ambre
    "#4caf50",  # Vert mat
    "#2196f3",  # Bleu clair
    "#f44336",  # Rouge mat
    "#9c27b0",  # Violet mat
]


def get_theme_color(index: int) -> str:
    """Retourne une couleur distincte pour un thème basé sur son index."""
    return THEME_COLORS[index % len(THEME_COLORS)]
