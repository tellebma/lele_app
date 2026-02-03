"""Pipeline de clustering pour la détection de thèmes.

Ce module implémente le clustering des segments de texte en utilisant
UMAP pour la réduction dimensionnelle et HDBSCAN pour le clustering.
"""

from typing import Callable

import numpy as np

from .models import ClusterResult, Segment


class ClusteringPipeline:
    """Pipeline UMAP → HDBSCAN pour le clustering de segments.

    Utilise UMAP pour réduire la dimensionnalité des embeddings,
    puis HDBSCAN pour identifier les clusters de manière adaptative.
    """

    def __init__(
        self,
        min_cluster_size: int = 3,
        min_samples: int = 2,
        n_components: int = 5,
        n_neighbors: int = 15,
        metric: str = "cosine",
    ):
        """Initialise le pipeline de clustering.

        Args:
            min_cluster_size: Taille minimum d'un cluster (HDBSCAN)
            min_samples: Nombre minimum d'échantillons pour un core point
            n_components: Dimensions après réduction UMAP
            n_neighbors: Voisins pour UMAP (structure locale)
            metric: Métrique de distance ('cosine', 'euclidean')
        """
        self.min_cluster_size = min_cluster_size
        self.min_samples = min_samples
        self.n_components = n_components
        self.n_neighbors = n_neighbors
        self.metric = metric

        self._umap_reducer = None
        self._clusterer = None

    @property
    def is_available(self) -> bool:
        """Vérifie si les dépendances sont installées."""
        try:
            import hdbscan
            import umap

            return True
        except ImportError:
            return False

    def cluster_segments(
        self,
        segments: list[Segment],
        max_clusters: int | None = None,
        progress_callback: Callable[[float, str], None] | None = None,
    ) -> tuple[list[ClusterResult], list[Segment]]:
        """Effectue le clustering des segments.

        Args:
            segments: Liste de segments avec embeddings
            max_clusters: Limite optionnelle du nombre de clusters
            progress_callback: Callback pour la progression

        Returns:
            (clusters, noise_segments) - Clusters identifiés et segments bruit
        """
        if not self.is_available:
            raise ImportError(
                "umap-learn et hdbscan sont requis. "
                "Installez-les avec: pip install umap-learn hdbscan"
            )

        import hdbscan
        import umap

        # Vérifier que les segments ont des embeddings
        valid_segments = [s for s in segments if s.embedding is not None]
        if len(valid_segments) < self.min_cluster_size:
            return [], valid_segments

        if progress_callback:
            progress_callback(0.1, "Préparation des embeddings...")

        # Construire la matrice d'embeddings
        embeddings = np.array([s.embedding for s in valid_segments])

        # Adapter n_components si nécessaire
        n_components = min(self.n_components, embeddings.shape[1], len(valid_segments) - 1)
        n_neighbors = min(self.n_neighbors, len(valid_segments) - 1)

        if progress_callback:
            progress_callback(0.2, "Réduction dimensionnelle (UMAP)...")

        # Réduction dimensionnelle avec UMAP
        self._umap_reducer = umap.UMAP(
            n_components=n_components,
            n_neighbors=n_neighbors,
            min_dist=0.1,
            metric=self.metric,
            random_state=42,
            verbose=False,
        )
        reduced = self._umap_reducer.fit_transform(embeddings)

        if progress_callback:
            progress_callback(0.5, "Clustering (HDBSCAN)...")

        # Clustering avec HDBSCAN
        self._clusterer = hdbscan.HDBSCAN(
            min_cluster_size=self.min_cluster_size,
            min_samples=self.min_samples,
            metric="euclidean",  # UMAP a déjà transformé l'espace
            cluster_selection_method="eom",
            prediction_data=True,
        )
        labels = self._clusterer.fit_predict(reduced)
        probabilities = self._clusterer.probabilities_

        if progress_callback:
            progress_callback(0.8, "Organisation des résultats...")

        # Organiser les résultats par cluster
        cluster_data: dict[int, dict] = {}
        noise_segments: list[Segment] = []

        for i, (segment, label, prob) in enumerate(zip(valid_segments, labels, probabilities)):
            if label == -1:  # Bruit
                noise_segments.append(segment)
            else:
                if label not in cluster_data:
                    cluster_data[label] = {
                        "segments": [],
                        "embeddings": [],
                        "probs": [],
                    }
                cluster_data[label]["segments"].append(segment)
                cluster_data[label]["embeddings"].append(embeddings[i])
                cluster_data[label]["probs"].append(prob)

        # Construire les ClusterResult
        clusters: list[ClusterResult] = []
        for cluster_id, data in cluster_data.items():
            cluster_embeddings = np.array(data["embeddings"])
            centroid = cluster_embeddings.mean(axis=0).tolist()
            coherence = float(np.mean(data["probs"]))

            clusters.append(
                ClusterResult(
                    cluster_id=cluster_id,
                    segments=data["segments"],
                    centroid=centroid,
                    coherence_score=coherence,
                )
            )

        # Trier par taille décroissante
        clusters.sort(key=lambda c: c.size, reverse=True)

        # Limiter le nombre de clusters si demandé
        if max_clusters and len(clusters) > max_clusters:
            # Garder les plus gros clusters, le reste devient du bruit
            kept_clusters = clusters[:max_clusters]
            for cluster in clusters[max_clusters:]:
                noise_segments.extend(cluster.segments)
            clusters = kept_clusters

        if progress_callback:
            progress_callback(
                1.0,
                f"{len(clusters)} thèmes détectés, {len(noise_segments)} segments non classés",
            )

        return clusters, noise_segments

    def compute_coherence(self, embeddings: np.ndarray) -> float:
        """Calcule le score de cohérence d'un cluster.

        Args:
            embeddings: Matrice d'embeddings du cluster

        Returns:
            Score de cohérence (0-1)
        """
        if len(embeddings) < 2:
            return 1.0

        centroid = embeddings.mean(axis=0)
        distances = self._cosine_distances(centroid.reshape(1, -1), embeddings)[0]
        return float(1 - distances.mean())

    def _cosine_distances(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Calcule les distances cosinus entre vecteurs."""
        # Normalisation (si pas déjà fait)
        a_norm = a / np.linalg.norm(a, axis=1, keepdims=True)
        b_norm = b / np.linalg.norm(b, axis=1, keepdims=True)
        similarities = np.dot(a_norm, b_norm.T)
        return 1 - similarities


def merge_similar_clusters(
    clusters: list[ClusterResult],
    threshold: float = 0.8,
    progress_callback: Callable[[float, str], None] | None = None,
) -> list[ClusterResult]:
    """Fusionne les clusters avec des centroïdes similaires.

    Args:
        clusters: Liste de clusters à potentiellement fusionner
        threshold: Seuil de similarité pour la fusion (0-1)
        progress_callback: Callback pour la progression

    Returns:
        Liste de clusters après fusion
    """
    if len(clusters) <= 1:
        return clusters

    if progress_callback:
        progress_callback(0.1, "Analyse des similarités entre thèmes...")

    # Calculer la matrice de similarité
    centroids = np.array([c.centroid for c in clusters])
    n = len(clusters)

    # Normaliser pour similarité cosinus
    centroids_norm = centroids / np.linalg.norm(centroids, axis=1, keepdims=True)
    similarities = np.dot(centroids_norm, centroids_norm.T)

    # Union-Find pour grouper les clusters à fusionner
    parent = list(range(n))

    def find(x):
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    # Identifier les paires à fusionner
    for i in range(n):
        for j in range(i + 1, n):
            if similarities[i, j] >= threshold:
                union(i, j)

    if progress_callback:
        progress_callback(0.5, "Fusion des thèmes similaires...")

    # Grouper les clusters par racine
    groups: dict[int, list[int]] = {}
    for i in range(n):
        root = find(i)
        if root not in groups:
            groups[root] = []
        groups[root].append(i)

    # Fusionner les clusters de chaque groupe
    merged_clusters: list[ClusterResult] = []
    for root, indices in groups.items():
        if len(indices) == 1:
            merged_clusters.append(clusters[indices[0]])
        else:
            # Fusionner plusieurs clusters
            all_segments: list[Segment] = []
            all_embeddings: list[list[float]] = []

            for idx in indices:
                all_segments.extend(clusters[idx].segments)
                for seg in clusters[idx].segments:
                    if seg.embedding:
                        all_embeddings.append(seg.embedding)

            if all_embeddings:
                new_centroid = np.array(all_embeddings).mean(axis=0).tolist()
            else:
                new_centroid = clusters[indices[0]].centroid

            # Recalculer la cohérence
            coherence = np.mean([clusters[i].coherence_score for i in indices])

            merged_clusters.append(
                ClusterResult(
                    cluster_id=root,
                    segments=all_segments,
                    centroid=new_centroid,
                    coherence_score=float(coherence),
                )
            )

    if progress_callback:
        n_merged = len(clusters) - len(merged_clusters)
        progress_callback(1.0, f"{n_merged} thèmes fusionnés")

    return merged_clusters


def find_similar_to_existing(
    cluster: ClusterResult,
    existing_embeddings: list[list[float]],
    existing_names: list[str],
    existing_ids: list[str],
    threshold: float = 0.75,
) -> tuple[str | None, str | None, float]:
    """Trouve un nœud existant similaire à un cluster.

    Args:
        cluster: Cluster à comparer
        existing_embeddings: Embeddings des nœuds existants
        existing_names: Noms des nœuds existants
        existing_ids: IDs des nœuds existants
        threshold: Seuil de similarité

    Returns:
        (node_id, node_name, similarity) ou (None, None, 0) si pas de match
    """
    if not existing_embeddings:
        return None, None, 0.0

    centroid = np.array(cluster.centroid).reshape(1, -1)
    existing = np.array(existing_embeddings)

    # Normaliser
    centroid_norm = centroid / np.linalg.norm(centroid)
    existing_norm = existing / np.linalg.norm(existing, axis=1, keepdims=True)

    # Similarités
    similarities = np.dot(centroid_norm, existing_norm.T)[0]
    max_idx = similarities.argmax()
    max_sim = similarities[max_idx]

    if max_sim >= threshold:
        return existing_ids[max_idx], existing_names[max_idx], float(max_sim)

    return None, None, 0.0


def check_clustering_dependencies() -> tuple[bool, str]:
    """Vérifie si les dépendances de clustering sont installées.

    Returns:
        (is_available, message)
    """
    missing = []

    try:
        import umap

        umap_version = getattr(umap, "__version__", "installed")
    except ImportError:
        missing.append("umap-learn")
        umap_version = None

    try:
        import hdbscan

        # hdbscan n'a pas toujours __version__, utiliser importlib.metadata
        try:
            from importlib.metadata import version

            hdbscan_version = version("hdbscan")
        except Exception:
            hdbscan_version = "installed"
    except ImportError:
        missing.append("hdbscan")
        hdbscan_version = None

    if missing:
        return False, f"Dépendances manquantes: {', '.join(missing)}"

    return True, f"umap-learn {umap_version}, hdbscan {hdbscan_version}"
