"""Application use case and deterministic scoring; no HTTP or provider-specific rules."""
from datetime import timedelta
from dataclasses import dataclass
from time import perf_counter_ns
from uuid import uuid4
from typing import Literal

from .catalog import Catalog
from .feature_schemas import DebugMatchResponse, DetailedMatchResponse, MatchTrace, TraceNotice
from .match_details import ScoreCalculation, build_details
from .trace import TraceRecorder, measured
from .rules import CheckedProfile, filter_profiles
from .schemas import (
    MAX_BUDGET, MAX_DATE, MIN_DATE, AvailabilityDay, BudgetAlternative, Contractor,
    Diagnostics, EvidenceItem, EvidenceLedger, MatchResponse, ModelInfo,
    ScoreBreakdown, SearchParams,
)
from .semantic import SemanticProvider, SemanticUnavailable, TextScore

RANKING_VERSION = 'eventlens-v2'
# Preserve the existing AI baseline. Missing components are omitted and weights renormalized.
WITH_DURATION = {'semantic': .50, 'lexical': .20, 'budget': .20, 'duration': .10}
WITHOUT_DURATION = {'semantic': .60, 'lexical': .20, 'budget': .20, 'duration': 0.0}


def _rank_card(checked: CheckedProfile, query: SearchParams, text: TextScore | None) -> tuple[Contractor, ScoreCalculation]:
    profile = checked.profile
    assert profile.price is not None  # A mandatory check already succeeded.
    duration = None
    if query.duration is not None and profile.max_hours is not None:
        duration = max(0.0, min(1.0, (profile.max_hours - query.duration) / query.duration))
    components = ScoreBreakdown(
        semantic=text.semantic if text else None, lexical=text.lexical if text else None,
        budget=max(0.0, min(1.0, 1 - profile.price / query.budget)), duration=duration,
    )
    base_weights = WITH_DURATION if duration is not None else WITHOUT_DURATION
    values: dict[str, float | None] = {key: getattr(components, key) for key in base_weights}
    divisor = sum(weight for key, weight in base_weights.items() if values[key] is not None)
    weights = {key: weight / divisor if values[key] is not None else None for key, weight in base_weights.items()}
    score = sum(value * (weights[key] or 0) for key, value in values.items() if value is not None)
    semantic = None if components.semantic is None else round(components.semantic, 6)
    semantic_evidence = EvidenceItem(
        matched=None, score=semantic, source_field='description', code='tfidf' if semantic is not None else 'unavailable',
        reason=f'Текстовая близость описания по TF-IDF: {semantic:.3f}' if semantic is not None else
        'Текстовая оценка не рассчитана; ранжирование использует доступные компоненты',
        requested=f'{query.category} {query.event_type}', actual=profile.description or None,
    )
    evidence = EvidenceLedger.model_validate({**checked.checks, 'semantic': semantic_evidence})
    facts = '; '.join(item.reason for item in checked.checks.values() if item.matched is True)
    # Verbatim excerpt is attributed; never invent a style from a keyword hit.
    excerpt = profile.description[:180].rstrip()
    explanation = facts + '.' + (f' В описании профиля: «{excerpt}{"…" if len(profile.description) > 180 else ""}».' if excerpt else '')
    card = Contractor(
        id=profile.id, name=profile.name, categories=list(profile.categories), city=profile.city,
        price=profile.price, score=round(score, 6), semantic_score=None if semantic is None else round(semantic, 6),
        synthetic=profile.synthetic, city_imputed=profile.city_imputed, price_imputed=profile.price_imputed,
        evidence=evidence, explanation=explanation,
        score_breakdown=ScoreBreakdown.model_validate({k: round(v, 6) if v is not None else None for k, v in values.items()}),
        score_weights=ScoreBreakdown.model_validate(weights), max_hours=profile.max_hours, duration_policy=profile.duration_policy,
        languages=list(profile.languages), description=profile.description,
    )

    return card, ScoreCalculation(components, ScoreBreakdown.model_validate(weights), score)


def rank_card(checked: CheckedProfile, query: SearchParams, text: TextScore | None) -> Contractor:
    """Keep the existing public helper; all consumers share the same calculation."""
    return _rank_card(checked, query, text)[0]


@dataclass(frozen=True)
class MatchExecution:
    query: SearchParams
    response: MatchResponse
    calculations: dict[str, ScoreCalculation]


class MatchingService:
    def __init__(self, catalog: Catalog, semantic: SemanticProvider | None = None):
        self.catalog = catalog
        self.semantic = semantic

    def match(self, request: SearchParams) -> MatchResponse:
        return self._execute(request).response

    def details(self, request: SearchParams) -> DetailedMatchResponse:
        execution = self._execute(request)
        return build_details(execution.query, execution.response, execution.calculations)

    def debug_match(self, request: SearchParams) -> DebugMatchResponse:
        started = perf_counter_ns()
        request_id = str(uuid4())
        recorder = TraceRecorder()
        execution = self._execute(request, recorder)
        with measured(recorder, 'details.assemble'):
            details = build_details(execution.query, execution.response, execution.calculations)
        response = execution.response
        return DebugMatchResponse(details=details, trace=MatchTrace(
            request_id=request_id, normalized_query=execution.query,
            catalog_count=len(self.catalog.profiles), total_eligible=response.total_eligible,
            returned_count=len(response.results), model_info=response.model_info,
            stages=recorder.stages, total_ms=(perf_counter_ns() - started) / 1_000_000,
            notices=recorder.notices,
        ))

    def _execute(self, request: SearchParams, recorder: TraceRecorder | None = None) -> MatchExecution:
        with measured(recorder, 'query.normalize'):
            query = self.catalog.canonical_query(request)
        pool, steps = filter_profiles(self.catalog.profiles, query, recorder.record if recorder else None)
        with measured(recorder, 'diagnostics.summarize'):
            counts = {step.stage: step.after for step in steps}
            status: Literal['matched', 'category_not_found', 'no_match'] = 'category_not_found' if counts['city'] == 0 else 'matched' if pool else 'no_match'
            blocker = next((step.stage for step in steps if step.before > 0 and step.after == 0), None)
            if status == 'category_not_found':
                summary = f'В городе {query.city} нет подрядчиков известной категории «{query.category}».'
            elif status == 'no_match':
                label = next(step.label for step in steps if step.stage == blocker)
                summary = (f'Первый нулевой этап: «{label}». Это результат порядка проверок; '
                           'изменение только этого условия не гарантирует совпадение без повторной проверки остальных.')
            elif len(pool) < 3:
                summary = f'Подходящих кандидатов {len(pool)}; остальные не прошли обязательные условия.'
            else:
                summary = f'Подходящих кандидатов {len(pool)}; показаны первые три по оценке соответствия.'
        alternative = None
        if status == 'no_match':
            with measured(recorder, 'alternatives.budget'):
                relaxed = query.model_copy(update={'budget': float(MAX_BUDGET)})
                affordable_pool, _ = filter_profiles(self.catalog.profiles, relaxed)
                prices = [item.profile.price for item in affordable_pool if item.profile.price is not None]
                if prices:
                    threshold = min(prices)
                    if threshold > query.budget:
                        verified, _ = filter_profiles(self.catalog.profiles, query.model_copy(update={'budget': threshold}))
                        alternative = BudgetAlternative(budget=threshold, available=len(verified))
        with measured(recorder, 'alternatives.dates'):
            availability = []
            for offset in (-2, -1, 0, 1, 2):
                day = query.date + timedelta(days=offset)
                if MIN_DATE <= day <= MAX_DATE:
                    eligible, _ = filter_profiles(self.catalog.profiles, query.model_copy(update={'date': day}))
                    availability.append(AvailabilityDay(date=day, available=len(eligible)))
        model = ModelInfo(ranking_version=RANKING_VERSION, data_version=self.catalog.version,
                          semantic_model='not_used' if not pool else 'disabled', fallback_used=False)
        text_scores: dict[str, TextScore] = {}
        if pool and self.semantic is not None:
            with measured(recorder, 'ranking.semantic'):
                try:
                    text_scores = self.semantic.score(query, self.catalog)
                    model.semantic_model = 'tfidf-v1'
                except SemanticUnavailable as exc:
                    model.semantic_model = 'unavailable'
                    model.fallback_used = True
                    if recorder:
                        recorder.notices.append(TraceNotice(code=exc.code, message='Текстовый сервис недоступен; применён существующий режим без текстовых компонентов.'))
        elif recorder:
            recorder.notices.append(TraceNotice(code='semantic_not_used' if not pool else 'semantic_disabled',
                                               message='Нет кандидатов для ранжирования.' if not pool else 'Текстовая оценка отключена конфигурацией.'))
        model.ranking_version += ':' + model.semantic_model
        with measured(recorder, 'ranking.score_and_sort'):
            scored = [_rank_card(item, query, text_scores.get(item.profile.id)) for item in pool]
            scored.sort(key=lambda item: (-item[0].score, item[0].price, item[0].id))
            ranked = [item[0] for item in scored]
            calculations = {item[0].id: item[1] for item in scored[:3]}
            if recorder and model.semantic_model == 'tfidf-v1':
                for card, calculation in scored:
                    if calculation.values.semantic is None or calculation.values.lexical is None:
                        recorder.notices.append(TraceNotice(code='text_score_missing', candidate_id=card.id,
                                                           message='Текстовый сервис не предоставил один или оба компонента; отсутствующие значения исключены из score.'))
        with measured(recorder, 'response.assemble'):
            response = MatchResponse(
                status=status, results=ranked[:3], total_eligible=len(pool), availability=availability, model_info=model,
                diagnostics=Diagnostics(steps=steps, counts=counts, primary_blocker=blocker, summary=summary,
                                        budget_alternative=alternative),
            )
        return MatchExecution(query, response, calculations)
