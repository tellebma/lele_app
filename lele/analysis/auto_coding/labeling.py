"""Labeling automatique des clusters par LLM ou mots-clés.

Ce module gère la génération de noms et descriptions pour les thèmes
détectés, avec support pour LLM local (Ollama) ou API, et fallback
par extraction de mots-clés.
"""

import json
import re
import subprocess
from collections import Counter
from typing import Callable

from ... import get_logger
from .models import ClusterResult, LLMLabelingResult, LLMProvider, Segment

logger = get_logger("analysis.auto_coding.labeling")

# Prompt pour le labeling par LLM
LABELING_PROMPT_FR = """Tu es un expert en analyse qualitative de données.
Voici {n} extraits de texte appartenant au même thème :

{excerpts}

Génère un nom et une description pour ce thème.

RÈGLES :
- Le nom doit être concis (2-4 mots maximum)
- La description doit être une phrase explicative
- Les mots-clés doivent être 3-5 termes représentatifs

Réponds UNIQUEMENT en JSON valide, sans commentaire :
{{"name": "...", "description": "...", "keywords": ["...", "...", "..."]}}"""


class ThemeLabeler:
    """Génère des labels pour les clusters de thèmes.

    Supporte plusieurs backends : Ollama (local), API Anthropic/OpenAI,
    ou extraction de mots-clés en fallback.
    """

    # Stopwords français étendus pour l'analyse qualitative
    FRENCH_STOPWORDS = {
        # Articles et déterminants
        "le",
        "la",
        "les",
        "un",
        "une",
        "des",
        "du",
        "de",
        "d",
        "l",
        # Pronoms
        "je",
        "tu",
        "il",
        "elle",
        "on",
        "nous",
        "vous",
        "ils",
        "elles",
        "me",
        "te",
        "se",
        "lui",
        "leur",
        "y",
        "en",
        "qui",
        "que",
        "quoi",
        "dont",
        "où",
        "ce",
        "cela",
        "ça",
        "ceci",
        # Verbes auxiliaires
        "être",
        "avoir",
        "est",
        "sont",
        "était",
        "été",
        "a",
        "ai",
        "ont",
        "fait",
        "faire",
        "va",
        "vais",
        "vont",
        "peut",
        "peux",
        "peuvent",
        # Prépositions et conjonctions
        "à",
        "au",
        "aux",
        "avec",
        "dans",
        "pour",
        "par",
        "sur",
        "sous",
        "entre",
        "vers",
        "chez",
        "sans",
        "contre",
        "mais",
        "ou",
        "et",
        "donc",
        "or",
        "ni",
        "car",
        "si",
        "comme",
        "quand",
        "lorsque",
        # Adverbes courants
        "très",
        "bien",
        "mal",
        "plus",
        "moins",
        "aussi",
        "trop",
        "peu",
        "encore",
        "toujours",
        "jamais",
        "souvent",
        "parfois",
        "déjà",
        "alors",
        "puis",
        "ensuite",
        "enfin",
        "vraiment",
        "peut-être",
        # Mots d'entretien qualitatif
        "euh",
        "hein",
        "bon",
        "ben",
        "bah",
        "voilà",
        "donc",
        "alors",
        "oui",
        "non",
        "ouais",
        "nan",
        "ok",
        "d'accord",
        "effectivement",
        "interviewer",
        "intervieweur",
        "enquêteur",
        "question",
        "réponse",
        # Autres
        "tout",
        "tous",
        "toute",
        "toutes",
        "autre",
        "autres",
        "même",
        "chaque",
        "quelque",
        "quelques",
        "aucun",
        "aucune",
        "certain",
        "certains",
        "certaine",
        "certaines",
        "plusieurs",
        "beaucoup",
        "peu",
        "assez",
        "tellement",
    }

    def __init__(
        self,
        provider: LLMProvider = LLMProvider.LOCAL_OLLAMA,
        model: str = "mistral",
        ollama_url: str = "http://localhost:11434",
        api_key: str | None = None,
    ):
        """Initialise le labeler.

        Args:
            provider: Fournisseur de LLM à utiliser
            model: Nom du modèle (dépend du provider)
            ollama_url: URL du serveur Ollama (si provider=OLLAMA)
            api_key: Clé API (si provider=ANTHROPIC ou OPENAI)
        """
        self.provider = provider
        self.model = model
        self.ollama_url = ollama_url
        self.api_key = api_key

    def label_cluster(
        self,
        cluster: ClusterResult,
        max_excerpts: int = 5,
    ) -> LLMLabelingResult:
        """Génère un label pour un cluster.

        Args:
            cluster: Cluster à labeler
            max_excerpts: Nombre max d'extraits pour le prompt

        Returns:
            Résultat du labeling avec nom, description, mots-clés
        """
        if self.provider == LLMProvider.NONE:
            return self._label_by_keywords(cluster)

        # Sélectionner les segments représentatifs
        representative = cluster.get_representative_segments(max_excerpts)
        if not representative:
            representative = cluster.segments[:max_excerpts]

        try:
            logger.debug(f"Labeling cluster {cluster.cluster_id} avec {self.provider.value}")
            if self.provider == LLMProvider.LOCAL_OLLAMA:
                return self._label_with_ollama(representative)
            elif self.provider == LLMProvider.API_ANTHROPIC:
                return self._label_with_anthropic(representative)
            elif self.provider == LLMProvider.API_OPENAI:
                return self._label_with_openai(representative)
            else:
                return self._label_by_keywords(cluster)
        except Exception as e:
            # Fallback sur mots-clés en cas d'erreur
            logger.warning(f"Erreur LLM, fallback sur mots-clés: {e}")
            result = self._label_by_keywords(cluster)
            result.error_message = f"Fallback mots-clés (erreur LLM: {e})"
            return result

    def label_clusters(
        self,
        clusters: list[ClusterResult],
        max_excerpts: int = 5,
        progress_callback: Callable[[float, str], None] | None = None,
    ) -> list[LLMLabelingResult]:
        """Labelle une liste de clusters.

        Args:
            clusters: Liste de clusters à labeler
            max_excerpts: Nombre max d'extraits par cluster
            progress_callback: Callback pour la progression

        Returns:
            Liste de résultats de labeling
        """
        results = []

        for i, cluster in enumerate(clusters):
            if progress_callback:
                progress = (i + 1) / len(clusters)
                progress_callback(progress, f"Nommage du thème {i + 1}/{len(clusters)}...")

            result = self.label_cluster(cluster, max_excerpts)
            result.model_used = f"{self.provider.value}:{self.model}"
            results.append(result)

        return results

    def _label_with_ollama(self, segments: list[Segment]) -> LLMLabelingResult:
        """Labelling via Ollama (LLM local)."""
        import urllib.request
        import urllib.error

        excerpts = self._format_excerpts(segments)
        prompt = LABELING_PROMPT_FR.format(n=len(segments), excerpts=excerpts)

        payload = json.dumps(
            {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 200,
                },
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            f"{self.ollama_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))
                raw_response = data.get("response", "")
                return self._parse_llm_response(raw_response)
        except urllib.error.URLError as e:
            raise ConnectionError(f"Impossible de contacter Ollama: {e}")

    def _label_with_anthropic(self, segments: list[Segment]) -> LLMLabelingResult:
        """Labelling via l'API Anthropic (Claude)."""
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError("anthropic n'est pas installé")

        excerpts = self._format_excerpts(segments)
        prompt = LABELING_PROMPT_FR.format(n=len(segments), excerpts=excerpts)

        client = Anthropic(api_key=self.api_key)
        response = client.messages.create(
            model=self.model or "claude-3-haiku-20240307",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )

        raw_response = response.content[0].text
        return self._parse_llm_response(raw_response)

    def _label_with_openai(self, segments: list[Segment]) -> LLMLabelingResult:
        """Labelling via l'API OpenAI."""
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai n'est pas installé")

        excerpts = self._format_excerpts(segments)
        prompt = LABELING_PROMPT_FR.format(n=len(segments), excerpts=excerpts)

        client = OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model or "gpt-3.5-turbo",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )

        raw_response = response.choices[0].message.content
        return self._parse_llm_response(raw_response)

    def _label_by_keywords(self, cluster: ClusterResult) -> LLMLabelingResult:
        """Fallback : labelling par extraction de mots-clés (TF-IDF simplifié)."""
        # Collecter tous les mots des segments
        all_words: list[str] = []
        for segment in cluster.segments:
            words = self._extract_words(segment.text)
            all_words.extend(words)

        if not all_words:
            return LLMLabelingResult(
                name="Thème sans nom",
                description="Aucun mot-clé significatif détecté",
                keywords=[],
                success=True,
            )

        # Compter les fréquences
        word_counts = Counter(all_words)

        # Prendre les mots les plus fréquents
        top_words = [word for word, _ in word_counts.most_common(10)]

        # Générer le nom à partir des 2-3 premiers mots
        name_words = top_words[:3]
        name = " / ".join(name_words).title() if name_words else "Thème"

        # Générer la description
        keywords = top_words[:5]
        description = f"Thème regroupant les concepts de {', '.join(keywords[:3])}"

        return LLMLabelingResult(
            name=name,
            description=description,
            keywords=keywords,
            success=True,
            model_used="keywords",
        )

    def _extract_words(self, text: str) -> list[str]:
        """Extrait les mots significatifs d'un texte."""
        # Nettoyer et tokeniser
        text = text.lower()
        words = re.findall(r"\b[a-zàâäéèêëïîôùûüç]{3,}\b", text)

        # Filtrer les stopwords
        return [w for w in words if w not in self.FRENCH_STOPWORDS]

    def _format_excerpts(self, segments: list[Segment]) -> str:
        """Formate les segments pour le prompt."""
        excerpts = []
        for i, seg in enumerate(segments):
            text = seg.text[:300]
            if len(seg.text) > 300:
                text += "..."
            excerpts.append(f"[{i + 1}] {text}")
        return "\n---\n".join(excerpts)

    def _parse_llm_response(self, raw_response: str) -> LLMLabelingResult:
        """Parse la réponse JSON du LLM."""
        # Nettoyer la réponse
        raw_response = raw_response.strip()

        # Essayer d'extraire le JSON
        json_match = re.search(r"\{[^{}]*\}", raw_response, re.DOTALL)
        if not json_match:
            return LLMLabelingResult(
                name="Thème détecté",
                description="Impossible de parser la réponse du LLM",
                keywords=[],
                raw_response=raw_response,
                success=False,
                error_message="Pas de JSON valide dans la réponse",
            )

        try:
            data = json.loads(json_match.group())
            return LLMLabelingResult(
                name=data.get("name", "Thème détecté"),
                description=data.get("description", ""),
                keywords=data.get("keywords", []),
                raw_response=raw_response,
                success=True,
            )
        except json.JSONDecodeError as e:
            return LLMLabelingResult(
                name="Thème détecté",
                description=raw_response[:100],
                keywords=[],
                raw_response=raw_response,
                success=False,
                error_message=f"Erreur JSON: {e}",
            )


def check_ollama_available(url: str = "http://localhost:11434") -> tuple[bool, str]:
    """Vérifie si Ollama est disponible et retourne les modèles installés.

    Returns:
        (is_available, message_or_models)
    """
    import urllib.request
    import urllib.error

    try:
        req = urllib.request.Request(f"{url}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            models = [m["name"] for m in data.get("models", [])]
            if models:
                return True, f"Modèles disponibles: {', '.join(models)}"
            return True, "Ollama actif mais aucun modèle installé"
    except urllib.error.URLError:
        return False, "Ollama non disponible. Démarrez-le avec 'ollama serve'"
    except Exception as e:
        return False, f"Erreur: {e}"


def get_ollama_models(url: str = "http://localhost:11434") -> list[str]:
    """Retourne la liste des modèles Ollama installés."""
    import urllib.request
    import urllib.error

    try:
        req = urllib.request.Request(f"{url}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def download_ollama_model(
    model_name: str,
    url: str = "http://localhost:11434",
    progress_callback: Callable[[float, str], None] | None = None,
) -> bool:
    """Télécharge un modèle Ollama.

    Args:
        model_name: Nom du modèle à télécharger (ex: "mistral", "llama2")
        url: URL du serveur Ollama
        progress_callback: Callback pour la progression

    Returns:
        True si le téléchargement a réussi
    """
    import urllib.request
    import urllib.error

    if progress_callback:
        progress_callback(0.0, f"Téléchargement de {model_name}...")

    payload = json.dumps({"name": model_name, "stream": True}).encode("utf-8")
    req = urllib.request.Request(
        f"{url}/api/pull",
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=600) as response:
            while True:
                line = response.readline()
                if not line:
                    break
                try:
                    data = json.loads(line.decode("utf-8"))
                    status = data.get("status", "")

                    # Extraire la progression si disponible
                    if "completed" in data and "total" in data:
                        total = data["total"]
                        completed = data["completed"]
                        if total > 0:
                            progress = completed / total
                            if progress_callback:
                                progress_callback(progress, status)
                    elif progress_callback:
                        progress_callback(0.5, status)

                except json.JSONDecodeError:
                    continue

        if progress_callback:
            progress_callback(1.0, f"{model_name} téléchargé avec succès")
        return True

    except Exception as e:
        if progress_callback:
            progress_callback(0.0, f"Erreur: {e}")
        return False


# Modèles Ollama recommandés pour le labeling
RECOMMENDED_OLLAMA_MODELS = [
    {
        "name": "mistral",
        "display_name": "Mistral 7B",
        "size_gb": 4.1,
        "description": "Excellent rapport qualité/taille, multilingue",
    },
    {
        "name": "llama2",
        "display_name": "Llama 2 7B",
        "size_gb": 3.8,
        "description": "Modèle Meta, bon en anglais",
    },
    {
        "name": "phi",
        "display_name": "Phi-2",
        "size_gb": 1.7,
        "description": "Très léger, Microsoft",
    },
    {
        "name": "gemma:2b",
        "display_name": "Gemma 2B",
        "size_gb": 1.4,
        "description": "Très léger, Google",
    },
    {
        "name": "mixtral",
        "display_name": "Mixtral 8x7B",
        "size_gb": 26,
        "description": "Meilleure qualité, nécessite beaucoup de RAM",
    },
]
