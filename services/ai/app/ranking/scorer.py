from app.ranking.semantic import canonical_query, tfidf_cosine
from app.ranking.weights import RANKING_VERSION, TOP_K_LIMIT, WITH_DURATION, WITHOUT_DURATION
from app.schemas.models import (
    CandidateEvidence,
    EvidenceItem,
    RankRequest,
    RankResponse,
    RankedCandidate,
    ScoreBreakdown,
)


_FORMAT_ALIASES = {"corporate": "корпоратив", "wedding": "свадьба", "birthday": "день рождения"}
_LANGUAGE_ALIASES = {"ru": "русский", "kk": "казахский", "kz": "казахский", "en": "английский"}


def _norm(value: str) -> str:
    folded = " ".join(value.casefold().replace("ё", "е").split())
    return _FORMAT_ALIASES.get(folded, _LANGUAGE_ALIASES.get(folded, folded))


def _score(candidate, query, semantic: float, lexical: float) -> tuple[float, ScoreBreakdown]:
    budget_fit = max(0.0, min(1.0, 1 - candidate.price / query.budget))
    if query.duration is not None and candidate.max_hours is not None:
        duration_fit = max(0.0, min(1.0, (candidate.max_hours - query.duration) / max(query.duration, 1)))
        weights = WITH_DURATION
    else:
        duration_fit = 0.0
        weights = WITHOUT_DURATION
    score = (
        weights["semantic"] * semantic
        + weights["lexical"] * lexical
        + weights["budget"] * budget_fit
        + weights.get("duration", 0.0) * duration_fit
    )
    breakdown = ScoreBreakdown(
        semantic=round(semantic, 6),
        lexical=round(lexical, 6),
        budget=round(budget_fit, 6),
        duration=round(duration_fit, 6),
    )
    return round(score, 6), breakdown


def _lexical_score(query_text: str, description: str) -> float:
    query_terms = set(query_text.casefold().split())
    document_terms = set(description.casefold().split())
    if not query_terms or not document_terms:
        return 0.0
    return len(query_terms & document_terms) / len(query_terms | document_terms)


def rank_candidates(request: RankRequest) -> RankResponse:
    query = request.query
    query_text = canonical_query(query.category, query.event_type, query.preferences)
    semantic_scores = tfidf_cosine(query_text, [candidate.description for candidate in request.candidates])
    ranked: list[RankedCandidate] = []

    for candidate, semantic in zip(request.candidates, semantic_scores):
        budget_match = candidate.price <= query.budget
        format_match = _norm(query.event_type) in {_norm(value) for value in candidate.formats}
        language_match = query.language is None or _norm(query.language) in {
            _norm(value) for value in candidate.languages
        }
        duration_applicable = query.duration is not None and candidate.max_hours is not None
        duration_match = not duration_applicable or candidate.max_hours >= query.duration

        # The AI endpoint receives candidates filtered by the backend. Keep a defensive
        # check here so an inconsistent caller cannot rank a known hard-constraint failure.
        if not (budget_match and format_match and language_match and duration_match):
            continue

        lexical = _lexical_score(query_text, candidate.description)
        score, breakdown = _score(candidate, query, semantic, lexical)
        budget_reason = (
            f"Цена {candidate.price:,} ₸ входит в бюджет {query.budget:,} ₸".replace(",", " ")
            if budget_match
            else f"Цена {candidate.price:,} ₸ превышает бюджет {query.budget:,} ₸".replace(",", " ")
        )
        language_reason = (
            "Язык не ограничен запросом"
            if query.language is None
            else f"Работает на {query.language} языке"
            if language_match
            else f"Нет подтверждения работы на языке: {query.language}"
        )
        format_reason = (
            f"Формат «{query.event_type}» указан среди услуг"
            if format_match
            else f"Формат «{query.event_type}» не указан среди услуг"
        )
        duration_reason = (
            "Ограничение по длительности неприменимо для этой услуги"
            if query.duration is None or candidate.max_hours is None
            else f"Максимум {candidate.max_hours:g} ч; запрос — {query.duration:g} ч"
        )
        ranked.append(
            RankedCandidate(
                id=candidate.id,
                name=candidate.name,
                category=candidate.category or query.category,
                city=candidate.city or query.city,
                price=candidate.price,
                score=score,
                semantic_score=round(semantic, 6),
                score_breakdown=breakdown,
                evidence=CandidateEvidence(
                    budget=EvidenceItem(
                        matched=budget_match,
                        score=breakdown.budget,
                        reason=budget_reason,
                        source_field="price_from_kzt",
                    ),
                    language=EvidenceItem(
                        matched=language_match,
                        reason=language_reason,
                        source_field="languages",
                    ),
                    format=EvidenceItem(
                        matched=format_match,
                        reason=format_reason,
                        source_field="event_formats",
                    ),
                    duration=EvidenceItem(
                        matched=duration_match,
                        reason=duration_reason,
                        source_field="max_hours",
                    ),
                    semantic=EvidenceItem(
                        score=round(semantic, 6),
                        reason=(
                            f"Совпадение описания с запросом: {semantic:.2f} по TF-IDF"
                            if query.preferences.strip()
                            else f"Совпадение описания с категорией и форматом: {semantic:.2f} по TF-IDF"
                        ),
                        source_field="description",
                    ),
                ),
                synthetic=candidate.synthetic,
            )
        )

    ranked.sort(key=lambda item: (-item.score, item.price, item.id))
    return RankResponse(
        outcome="matched" if ranked else "no_candidates",
        candidates=ranked[: min(request.limit, TOP_K_LIMIT)],
        total_eligible=len(ranked),
        model_info={"ranking_version": RANKING_VERSION, "semantic_model": "tfidf-fallback", "fallback_used": True},
    )
