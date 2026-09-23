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
