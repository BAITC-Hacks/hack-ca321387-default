from functools import lru_cache
import math
import re
from collections import Counter


_TOKEN_RE = re.compile(r"[\w-]+", re.UNICODE)
_STOP_WORDS = {
    "и", "в", "во", "на", "для", "с", "со", "по", "к", "из", "от",
    "до", "а", "но", "или", "это", "как", "что", "мы", "я", "мне",
}


def tokenize(text: str) -> list[str]:
    return [
        token.casefold().replace("ё", "е")
        for token in _TOKEN_RE.findall(text)
        if len(token) > 1 and token.casefold() not in _STOP_WORDS
    ]


def tfidf_cosine(query: str, documents: list[str]) -> list[float]:
    """Small-corpus TF-IDF cosine; deterministic and dependency-free fallback."""
    query_tokens = tokenize(query)
    document_tokens = [tokenize(document) for document in documents]
    corpus = [query_tokens, *document_tokens]
    document_frequency: Counter[str] = Counter()
    for tokens in corpus:
        document_frequency.update(set(tokens))
    corpus_size = len(corpus)

    def vector(tokens: list[str]) -> dict[str, float]:
        counts = Counter(tokens)
        total = len(tokens)
        if total == 0:
            return {}
        return {
            term: (count / total)
            * (math.log((1 + corpus_size) / (1 + document_frequency[term])) + 1)
            for term, count in counts.items()
        }

    query_vector = vector(query_tokens)
    query_norm = math.sqrt(sum(value * value for value in query_vector.values()))
    scores: list[float] = []
    for tokens in document_tokens:
        doc_vector = vector(tokens)
        doc_norm = math.sqrt(sum(value * value for value in doc_vector.values()))
        if not query_norm or not doc_norm:
            scores.append(0.0)
            continue
        dot = sum(weight * doc_vector.get(term, 0.0) for term, weight in query_vector.items())
        scores.append(min(1.0, max(0.0, dot / (query_norm * doc_norm))))
    return scores


def canonical_query(category: str, event_type: str, preferences: str) -> str:
    return " ".join(part.strip() for part in (category, event_type, preferences) if part.strip())


def lexical_overlap(query: str, description: str) -> float:
    query_terms = set(query.casefold().split())
    document_terms = set(description.casefold().split())
    if not query_terms or not document_terms:
        return 0.0
    return len(query_terms & document_terms) / len(query_terms | document_terms)


# The key contains the complete immutable corpus and query; data changes invalidate it.
# Bounded in-process memoization for the small demo dataset, no infrastructure needed.


@lru_cache(maxsize=128)
def cached_similarity(query: str, documents: tuple[str, ...]) -> tuple[tuple[float | None, float | None], ...]:
    semantic = tfidf_cosine(query, list(documents))
    return tuple((score, lexical_overlap(query, text)) if tokenize(text) else (None, None)
                 for text, score in zip(documents, semantic))
