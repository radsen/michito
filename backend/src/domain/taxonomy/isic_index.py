"""
Universal ISIC / CIIU Rev. 4 In-Memory Token & BM25 Search Index.
Provides sub-millisecond resolution of freeform economic activity text,
company names, or sector queries to official 4-digit UN ISIC / DANE CIIU codes.
"""

from collections import defaultdict
import math
import re
from typing import Dict, List, Optional, Set, Tuple
import unicodedata

from backend.src.domain.taxonomy.isic_catalog import UNIVERSAL_ISIC_CATALOG, IsicEntry


def normalize_text(text: str) -> str:
    """Removes accents, lowercases, and strips non-alphanumeric characters."""
    if not text:
        return ""
    # Normalize unicode to decomposed form and remove combining marks (accents)
    nfkd = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Lowercase and replace non-alphanumeric with spaces
    lowered = stripped.lower()
    cleaned = re.sub(r"[^a-z0-9\s]", " ", lowered)
    return re.sub(r"\s+", " ", cleaned).strip()


def tokenize(text: str) -> List[str]:
    """Tokenizes normalized text into words, omitting common stop words."""
    norm = normalize_text(text)
    if not norm:
        return []
    
    stop_words = {
        "de", "la", "el", "los", "las", "un", "una", "unos", "unas", "y", "o", "en",
        "a", "para", "por", "con", "sin", "del", "al", "actividades", "actividad",
        "otras", "otros", "demas", "conexas", "conexos", "excepto", "ncp", "incluye",
        "servicios", "servicio", "empresas", "empresa"
    }
    
    tokens = [t for t in norm.split() if len(t) > 1 and t not in stop_words]
    return tokens


class IsicIndex:
    """
    Sub-millisecond token & BM25 search index for the Universal ISIC Rev. 4 catalog.
    Zero external dependencies and instant in-memory lookup.
    """

    def __init__(self, catalog: Optional[Dict[str, IsicEntry]] = None):
        self.catalog = catalog or UNIVERSAL_ISIC_CATALOG
        self.doc_count = len(self.catalog)
        self.inverted_index: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
        self.code_lookup: Dict[str, IsicEntry] = {}
        self.doc_lengths: Dict[str, int] = {}
        self._build_index()

    def _build_index(self) -> None:
        total_len = 0
        for code, entry in self.catalog.items():
            self.code_lookup[code] = entry
            
            # Extract document tokens with weighted sources
            token_weights: Dict[str, float] = defaultdict(float)
            
            # Exact code token
            token_weights[code] += 10.0
            token_weights[entry.division] += 4.0
            
            # Keywords (highest semantic relevance)
            for kw in entry.keywords:
                for token in tokenize(kw):
                    token_weights[token] += 5.0
            
            # Title tokens
            for token in tokenize(entry.title):
                token_weights[token] += 3.0
                
            # Sector macro tokens
            for token in tokenize(entry.sector_macro):
                token_weights[token] += 2.0
                
            # Section title tokens
            for token in tokenize(entry.section_title):
                token_weights[token] += 1.0

            doc_len = len(token_weights)
            self.doc_lengths[code] = doc_len
            total_len += doc_len
            
            for token, weight in token_weights.items():
                self.inverted_index[token].append((code, weight))

        self.avg_doc_len = total_len / max(1, self.doc_count)

    def search(self, query: str, limit: int = 5) -> List[Tuple[IsicEntry, float]]:
        """
        Searches the catalog using BM25-inspired term frequency and inverted index weights.
        Returns ranked list of (IsicEntry, score).
        """
        if not query:
            return []

        # Check for direct 4-digit or 2-digit code in query
        code_match = re.search(r"\b(\d{2,4})\b", query)
        if code_match:
            candidate_code = code_match.group(1).zfill(4)
            if candidate_code in self.code_lookup:
                entry = self.code_lookup[candidate_code]
                return [(entry, 100.0)]

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        # BM25 parameters
        k1 = 1.5
        b = 0.75

        scores: Dict[str, float] = defaultdict(float)

        for q_token in query_tokens:
            postings = self.inverted_index.get(q_token, [])
            
            # Partial prefix matching for tokens with len >= 4
            if not postings and len(q_token) >= 4:
                prefix = q_token[:4]
                matching_tokens = [t for t in self.inverted_index if t.startswith(prefix)]
                for mt in matching_tokens:
                    for code, weight in self.inverted_index[mt]:
                        scores[code] += weight * 0.5
                continue

            df = len(postings)
            if df == 0:
                continue

            # IDF calculation
            idf = math.log(1.0 + (self.doc_count - df + 0.5) / (df + 0.5))

            for code, weight in postings:
                doc_len = self.doc_lengths.get(code, self.avg_doc_len)
                norm_tf = (weight * (k1 + 1)) / (weight + k1 * (1 - b + b * (doc_len / self.avg_doc_len)))
                scores[code] += idf * norm_tf

        if not scores:
            return []

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]
        return [(self.code_lookup[code], score) for code, score in ranked]

    def resolve_best_match(self, query: str) -> Optional[IsicEntry]:
        """Returns the single top-ranked ISIC entry for a query, or None if no match."""
        results = self.search(query, limit=1)
        if results:
            return results[0][0]
        return None

    def get_by_code(self, code: str) -> Optional[IsicEntry]:
        """Direct lookup by 4-digit code (e.g. '8530' or '6201')."""
        clean = code.strip().zfill(4)
        return self.code_lookup.get(clean)

    def suggest_roles(self, code: str, country_code: str = "ALL") -> List[str]:
        """Retrieves typical buyer or vendor roles for a given ISIC code and country."""
        entry = self.get_by_code(code)
        if not entry:
            return ["Gerente General", "Director Comercial", "Director de Compras", "Director de Operaciones"]
        
        country = country_code.upper()
        if country in entry.typical_roles:
            return entry.typical_roles[country]
        if "ALL" in entry.typical_roles:
            return entry.typical_roles["ALL"]
        return ["Gerente General", "Director Comercial", "Director de Compras"]


# Global singleton instance for high-speed reuse across the application
GLOBAL_ISIC_INDEX = IsicIndex()


def get_isic_index() -> IsicIndex:
    """Returns the singleton ISIC index instance."""
    return GLOBAL_ISIC_INDEX

