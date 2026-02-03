"""Moteur de recherche full-text."""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from ..models.source import Source
from ..models.memo import Memo

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Résultat d'une recherche."""

    item_type: str  # 'source', 'memo', 'node'
    item_id: str
    item_name: str
    snippet: str
    score: float = 0.0
    matches: list[tuple[int, int]] = field(default_factory=list)


class SearchEngine:
    """Moteur de recherche full-text."""

    def __init__(self, db):
        self.db = db

    def search(
        self,
        query: str,
        search_sources: bool = True,
        search_memos: bool = True,
        source_types: Optional[list] = None,
        limit: int = 100,
    ) -> list[SearchResult]:
        """
        Effectue une recherche full-text.

        Args:
            query: Termes de recherche
            search_sources: Chercher dans les sources
            search_memos: Chercher dans les mémos
            source_types: Types de sources à inclure (None = tous)
            limit: Nombre max de résultats

        Returns:
            Liste de SearchResult triés par pertinence
        """
        results = []

        if search_sources:
            results.extend(self._search_sources(query, source_types, limit))

        if search_memos:
            results.extend(self._search_memos(query, limit))

        # Trier par score
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def _search_sources(
        self, query: str, source_types: Optional[list], limit: int
    ) -> list[SearchResult]:
        """Recherche dans les sources."""
        results = []

        # Utiliser FTS5
        try:
            cursor = self.db.execute(
                """
                SELECT id, name, content, rank
                FROM sources_fts
                WHERE sources_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (query, limit),
            )

            for row in cursor.fetchall():
                # Filtrer par type si nécessaire
                if source_types:
                    source = Source.get(self.db, row["id"])
                    if source and source.type not in source_types:
                        continue

                snippet = self._create_snippet(row["content"], query)
                matches = self._find_matches(row["content"], query)

                results.append(
                    SearchResult(
                        item_type="source",
                        item_id=row["id"],
                        item_name=row["name"],
                        snippet=snippet,
                        score=-row["rank"],  # FTS5 rank is negative
                        matches=matches,
                    )
                )

        except Exception as e:
            # Fallback: recherche simple si FTS échoue
            logger.debug("FTS5 search failed, falling back to simple search: %s", e)
            results = self._search_sources_simple(query, source_types, limit)

        return results

    def _search_sources_simple(
        self, query: str, source_types: Optional[list], limit: int
    ) -> list[SearchResult]:
        """Recherche simple sans FTS."""
        results = []
        pattern = re.compile(re.escape(query), re.IGNORECASE)

        cursor = self.db.execute("SELECT * FROM sources")
        for row in cursor.fetchall():
            source = Source.from_row(dict(row))

            if source_types and source.type not in source_types:
                continue

            content = source.content or ""
            name = source.name

            # Chercher dans le nom et le contenu
            name_matches = list(pattern.finditer(name))
            content_matches = list(pattern.finditer(content))

            if name_matches or content_matches:
                score = len(name_matches) * 10 + len(content_matches)
                snippet = self._create_snippet(content, query)
                matches = [(m.start(), m.end()) for m in content_matches]

                results.append(
                    SearchResult(
                        item_type="source",
                        item_id=source.id,
                        item_name=source.name,
                        snippet=snippet,
                        score=score,
                        matches=matches,
                    )
                )

        return sorted(results, key=lambda r: r.score, reverse=True)[:limit]

    def _search_memos(self, query: str, limit: int) -> list[SearchResult]:
        """Recherche dans les mémos."""
        results = []

        try:
            cursor = self.db.execute(
                """
                SELECT id, title, content, rank
                FROM memos_fts
                WHERE memos_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (query, limit),
            )

            for row in cursor.fetchall():
                snippet = self._create_snippet(row["content"], query)
                matches = self._find_matches(row["content"], query)

                results.append(
                    SearchResult(
                        item_type="memo",
                        item_id=row["id"],
                        item_name=row["title"],
                        snippet=snippet,
                        score=-row["rank"],
                        matches=matches,
                    )
                )

        except Exception as e:
            # Fallback simple si FTS échoue
            logger.debug("FTS5 memo search failed, falling back to simple search: %s", e)
            pattern = re.compile(re.escape(query), re.IGNORECASE)
            for memo in Memo.get_all(self.db):
                content = memo.content or ""
                matches = list(pattern.finditer(content))
                title_matches = list(pattern.finditer(memo.title))

                if matches or title_matches:
                    results.append(
                        SearchResult(
                            item_type="memo",
                            item_id=memo.id,
                            item_name=memo.title,
                            snippet=self._create_snippet(content, query),
                            score=len(title_matches) * 10 + len(matches),
                            matches=[(m.start(), m.end()) for m in matches],
                        )
                    )

        return results

    def _create_snippet(self, content: str, query: str, context: int = 100) -> str:
        """Crée un extrait de texte autour de la première occurrence."""
        if not content:
            return ""

        pattern = re.compile(re.escape(query), re.IGNORECASE)
        match = pattern.search(content)

        if not match:
            return content[:200] + "..." if len(content) > 200 else content

        start = max(0, match.start() - context)
        end = min(len(content), match.end() + context)

        snippet = content[start:end]

        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."

        return snippet

    def _find_matches(self, content: str, query: str) -> list[tuple[int, int]]:
        """Trouve toutes les occurrences de la requête."""
        if not content:
            return []

        pattern = re.compile(re.escape(query), re.IGNORECASE)
        return [(m.start(), m.end()) for m in pattern.finditer(content)]

    def search_regex(self, pattern: str, limit: int = 100) -> list[SearchResult]:
        """Recherche avec une expression régulière."""
        results = []

        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error:
            return []

        cursor = self.db.execute("SELECT * FROM sources")
        for row in cursor.fetchall():
            source = Source.from_row(dict(row))
            content = source.content or ""

            matches = list(regex.finditer(content))
            if matches:
                snippet = self._create_snippet(content, matches[0].group())
                results.append(
                    SearchResult(
                        item_type="source",
                        item_id=source.id,
                        item_name=source.name,
                        snippet=snippet,
                        score=len(matches),
                        matches=[(m.start(), m.end()) for m in matches],
                    )
                )

        return sorted(results, key=lambda r: r.score, reverse=True)[:limit]

    def get_word_frequencies(
        self,
        source_ids: Optional[list[str]] = None,
        min_length: int = 3,
        exclude_words: Optional[set[str]] = None,
    ) -> dict[str, int]:
        """
        Calcule les fréquences de mots.

        Args:
            source_ids: IDs des sources à analyser (None = toutes)
            min_length: Longueur minimale des mots
            exclude_words: Mots à exclure (stop words)

        Returns:
            Dictionnaire {mot: fréquence}
        """
        if exclude_words is None:
            exclude_words = self._get_stop_words()

        frequencies = {}
        word_pattern = re.compile(r"\b[a-zA-ZÀ-ÿ]+\b")

        if source_ids:
            sources = [Source.get(self.db, sid) for sid in source_ids]
            sources = [s for s in sources if s]
        else:
            sources = Source.get_all(self.db)

        for source in sources:
            content = source.content or ""
            words = word_pattern.findall(content.lower())

            for word in words:
                if len(word) >= min_length and word not in exclude_words:
                    frequencies[word] = frequencies.get(word, 0) + 1

        return frequencies

    def _get_stop_words(self) -> set[str]:
        """Retourne les mots vides français et anglais."""
        return {
            # Français
            "le",
            "la",
            "les",
            "un",
            "une",
            "des",
            "du",
            "de",
            "et",
            "est",
            "en",
            "que",
            "qui",
            "dans",
            "ce",
            "il",
            "ne",
            "sur",
            "se",
            "pas",
            "plus",
            "par",
            "pour",
            "au",
            "avec",
            "son",
            "sont",
            "mais",
            "nous",
            "vous",
            "ils",
            "elle",
            "été",
            "cette",
            "ou",
            "ses",
            "tout",
            "leur",
            "ont",
            "comme",
            "être",
            "avoir",
            "fait",
            "faire",
            "peut",
            "aussi",
            # Anglais
            "the",
            "be",
            "to",
            "of",
            "and",
            "a",
            "in",
            "that",
            "have",
            "i",
            "it",
            "for",
            "not",
            "on",
            "with",
            "he",
            "as",
            "you",
            "do",
            "at",
            "this",
            "but",
            "his",
            "by",
            "from",
            "they",
            "we",
            "say",
            "her",
            "she",
            "or",
            "an",
            "will",
            "my",
            "one",
            "all",
            "would",
            "there",
            "their",
            "what",
            "so",
            "up",
            "out",
            "if",
            "about",
            "who",
            "get",
            "which",
            "go",
            "me",
            "when",
            "make",
            "can",
            "like",
            "time",
            "no",
            "just",
            "him",
            "know",
            "take",
            "people",
            "into",
            "year",
            "your",
            "good",
            "some",
            "could",
            "them",
            "see",
            "other",
            "than",
            "then",
            "now",
            "look",
            "only",
            "come",
            "its",
            "over",
            "think",
            "also",
        }
