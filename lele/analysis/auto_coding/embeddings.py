"""Moteur d'embeddings pour la vectorisation des segments.

Ce module gère le chargement des modèles de sentence-transformers
et la génération d'embeddings pour les segments de texte.
"""

import hashlib
from pathlib import Path
from typing import Callable

import numpy as np

from ... import get_logger
from .models import Segment

logger = get_logger("analysis.auto_coding.embeddings")

# Cache global pour les embeddings
_embedding_cache: dict[str, list[float]] = {}


class EmbeddingEngine:
    """Moteur de génération d'embeddings avec sentence-transformers.

    Supporte plusieurs modèles multilingues avec cache pour les performances.
    """

    # Modèles recommandés par ordre de qualité/taille
    AVAILABLE_MODELS = {
        "paraphrase-multilingual-MiniLM-L12-v2": {
            "name": "MiniLM Multilingue",
            "size_mb": 420,
            "description": "Bon rapport qualité/taille, multilingue",
            "dimensions": 384,
        },
        "paraphrase-multilingual-mpnet-base-v2": {
            "name": "MPNet Multilingue",
            "size_mb": 970,
            "description": "Meilleure qualité, multilingue",
            "dimensions": 768,
        },
        "distiluse-base-multilingual-cased-v1": {
            "name": "DistilUSE Multilingue",
            "size_mb": 480,
            "description": "Rapide et léger, multilingue",
            "dimensions": 512,
        },
        "all-MiniLM-L6-v2": {
            "name": "MiniLM Anglais",
            "size_mb": 80,
            "description": "Très rapide, anglais uniquement",
            "dimensions": 384,
        },
    }

    DEFAULT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
        use_cache: bool = True,
    ):
        """Initialise le moteur d'embeddings.

        Args:
            model_name: Nom du modèle sentence-transformers à utiliser
            device: Device cible ('cuda', 'cpu', ou None pour auto-détection)
            use_cache: Active le cache des embeddings
        """
        self.model_name = model_name or self.DEFAULT_MODEL
        self.device = device
        self.use_cache = use_cache
        self._model = None
        self._is_loaded = False

    @property
    def is_available(self) -> bool:
        """Vérifie si sentence-transformers est installé."""
        try:
            import sentence_transformers

            return True
        except ImportError:
            return False

    def load_model(
        self, progress_callback: Callable[[float, str], None] | None = None
    ) -> bool:
        """Charge le modèle en mémoire.

        Args:
            progress_callback: Callback pour signaler la progression

        Returns:
            True si le chargement a réussi
        """
        if self._is_loaded:
            return True

        if not self.is_available:
            raise ImportError(
                "sentence-transformers n'est pas installé. "
                "Installez-le avec: pip install sentence-transformers"
            )

        try:
            from sentence_transformers import SentenceTransformer

            if progress_callback:
                progress_callback(0.1, f"Chargement du modèle {self.model_name}...")

            # Auto-détection du device
            if self.device is None:
                self.device = self._detect_device()

            if progress_callback:
                progress_callback(0.3, f"Utilisation de {self.device.upper()}...")

            self._model = SentenceTransformer(self.model_name, device=self.device)

            if progress_callback:
                progress_callback(1.0, "Modèle chargé")

            self._is_loaded = True
            logger.info(f"Modèle {self.model_name} chargé sur {self.device}")
            return True

        except Exception as e:
            logger.error(f"Erreur chargement modèle {self.model_name}: {e}")
            raise RuntimeError(f"Erreur lors du chargement du modèle: {e}")

    def _detect_device(self) -> str:
        """Détecte le meilleur device disponible."""
        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"  # Apple Silicon
        except ImportError:
            pass
        return "cpu"

    def _get_cache_key(self, text: str) -> str:
        """Génère une clé de cache pour un texte."""
        return hashlib.md5(f"{self.model_name}:{text}".encode()).hexdigest()

    def encode_text(self, text: str) -> list[float]:
        """Encode un seul texte en vecteur.

        Args:
            text: Texte à encoder

        Returns:
            Vecteur d'embedding
        """
        if not self._is_loaded:
            self.load_model()

        # Vérifier le cache
        if self.use_cache:
            cache_key = self._get_cache_key(text)
            if cache_key in _embedding_cache:
                return _embedding_cache[cache_key]

        # Générer l'embedding
        embedding = self._model.encode(
            text, normalize_embeddings=True, show_progress_bar=False
        )
        result = embedding.tolist()

        # Mettre en cache
        if self.use_cache:
            _embedding_cache[cache_key] = result

        return result

    def encode_segments(
        self,
        segments: list[Segment],
        batch_size: int = 32,
        progress_callback: Callable[[float, str], None] | None = None,
    ) -> None:
        """Encode une liste de segments en place.

        Les embeddings sont stockés directement dans les objets Segment.

        Args:
            segments: Liste de segments à encoder
            batch_size: Taille des batchs pour le traitement
            progress_callback: Callback pour la progression
        """
        if not self._is_loaded:
            self.load_model(progress_callback)

        # Séparer les segments avec/sans cache
        to_encode_indices = []
        to_encode_texts = []

        for i, segment in enumerate(segments):
            if self.use_cache:
                cache_key = self._get_cache_key(segment.text)
                if cache_key in _embedding_cache:
                    segment.embedding = _embedding_cache[cache_key]
                    continue

            to_encode_indices.append(i)
            to_encode_texts.append(segment.text)

        if not to_encode_texts:
            if progress_callback:
                progress_callback(1.0, f"Tous les {len(segments)} segments en cache")
            return

        # Encoder les segments manquants par batch
        total_batches = (len(to_encode_texts) + batch_size - 1) // batch_size

        for batch_idx in range(total_batches):
            start = batch_idx * batch_size
            end = min(start + batch_size, len(to_encode_texts))
            batch_texts = to_encode_texts[start:end]

            if progress_callback:
                progress = (batch_idx + 1) / total_batches
                progress_callback(
                    progress,
                    f"Vectorisation {end}/{len(to_encode_texts)} segments...",
                )

            # Encoder le batch
            embeddings = self._model.encode(
                batch_texts, normalize_embeddings=True, show_progress_bar=False
            )

            # Assigner et cacher
            for j, embedding in enumerate(embeddings):
                idx = to_encode_indices[start + j]
                emb_list = embedding.tolist()
                segments[idx].embedding = emb_list

                if self.use_cache:
                    cache_key = self._get_cache_key(batch_texts[j])
                    _embedding_cache[cache_key] = emb_list

    def encode_texts(
        self,
        texts: list[str],
        batch_size: int = 32,
        progress_callback: Callable[[float, str], None] | None = None,
    ) -> np.ndarray:
        """Encode une liste de textes en matrice de vecteurs.

        Args:
            texts: Liste de textes à encoder
            batch_size: Taille des batchs
            progress_callback: Callback pour la progression

        Returns:
            Matrice numpy (n_texts, embedding_dim)
        """
        if not self._is_loaded:
            self.load_model(progress_callback)

        if progress_callback:
            progress_callback(0.1, f"Vectorisation de {len(texts)} textes...")

        embeddings = self._model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        if progress_callback:
            progress_callback(1.0, "Vectorisation terminée")

        return embeddings

    def get_model_info(self) -> dict:
        """Retourne les informations sur le modèle actuel."""
        info = self.AVAILABLE_MODELS.get(self.model_name, {})
        return {
            "model_name": self.model_name,
            "device": self.device or "non chargé",
            "is_loaded": self._is_loaded,
            "cache_size": len(_embedding_cache),
            **info,
        }

    @classmethod
    def get_available_models(cls) -> list[dict]:
        """Retourne la liste des modèles disponibles avec leurs infos."""
        return [
            {"id": model_id, **info}
            for model_id, info in cls.AVAILABLE_MODELS.items()
        ]


def clear_embedding_cache():
    """Vide le cache global des embeddings."""
    global _embedding_cache
    _embedding_cache.clear()


def get_cache_size() -> int:
    """Retourne le nombre d'entrées dans le cache."""
    return len(_embedding_cache)


def check_sentence_transformers() -> tuple[bool, str]:
    """Vérifie si sentence-transformers est installé et fonctionnel.

    Returns:
        (is_available, message)
    """
    try:
        import sentence_transformers

        version = sentence_transformers.__version__
        return True, f"sentence-transformers {version} installé"
    except ImportError:
        return False, (
            "sentence-transformers non installé. "
            "Installez avec: pip install sentence-transformers"
        )


def check_torch_device() -> dict:
    """Vérifie les devices disponibles pour PyTorch.

    Returns:
        Dict avec les infos sur les devices disponibles
    """
    result = {
        "cpu": True,
        "cuda": False,
        "cuda_device_name": None,
        "mps": False,
        "recommended": "cpu",
    }

    try:
        import torch

        if torch.cuda.is_available():
            result["cuda"] = True
            result["cuda_device_name"] = torch.cuda.get_device_name(0)
            result["recommended"] = "cuda"

        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            result["mps"] = True
            if not result["cuda"]:
                result["recommended"] = "mps"

    except ImportError:
        pass

    return result
