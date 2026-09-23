"""Present facts captured by the matcher; never rerun selection or model inference."""
from dataclasses import dataclass
from itertools import combinations

from .feature_schemas import (
    ComparisonContext, ComparisonDecision, ComponentName, DetailedMatchResponse,
    FunnelStepDetail, RankingDetail, ScoreComponentDetail,
)
from .schemas import Contractor, MatchResponse, ScoreBreakdown, SearchParams

COMPONENTS: tuple[ComponentName, ...] = ('semantic', 'lexical', 'budget', 'duration')


@dataclass(frozen=True)
class ScoreCalculation:
    values: ScoreBreakdown
    weights: ScoreBreakdown
    unrounded_score: float


def ranking_detail(card: Contractor, calculation: ScoreCalculation, position: int) -> RankingDetail:
    components = []
    source_fields = {'semantic': ['description'], 'lexical': ['description'],
                     'budget': ['price_from_kzt', 'budget'], 'duration': ['max_hours', 'duration']}
    for key in COMPONENTS:
        value: float | None = getattr(calculation.values, key)
        weight: float | None = getattr(calculation.weights, key)
        state = 'active'
        if value is None:
            if key == 'duration':
                state = 'not_requested' if card.evidence.duration.code == 'not_requested' else 'not_applicable'
            else:
                state = 'unavailable'
        if key == 'budget':
            reason = 'clamp(1 - price / budget, 0, 1); стартовая цена за мероприятие'
        elif key == 'duration':
            reason = 'clamp((max_hours - duration) / duration, 0, 1)' if value is not None else card.evidence.duration.reason
        else:
            reason = ('TF-IDF cosine' if key == 'semantic' else 'Lexical Jaccard') if value is not None else 'Сервис не предоставил оценку; компонент исключён, остальные веса перенормированы'
        components.append(ScoreComponentDetail.model_validate({
            'component': key, 'state': state, 'value': value, 'weight': weight,
            'contribution': value * weight if value is not None and weight is not None else None,
            'source_fields': source_fields[key], 'reason': reason,
        }))
    return RankingDetail(candidate_id=card.id, position=position, score=card.score, components=components,
                         unrounded_score=calculation.unrounded_score,
                         rounding_adjustment=card.score - calculation.unrounded_score)


def build_details(query: SearchParams, response: MatchResponse,
                  calculations: dict[str, ScoreCalculation]) -> DetailedMatchResponse:
    ranking = [ranking_detail(card, calculations[card.id], index + 1) for index, card in enumerate(response.results)]
    by_id = {detail.candidate_id: detail for detail in ranking}
    decisions = []
    for higher, lower in combinations(response.results, 2):
        if higher.score != lower.score:
            decided_by = 'score'
            reason = 'Выше итоговый score после округления до 6 знаков.'
        elif higher.price != lower.price:
            decided_by = 'price'
            reason = 'Округлённый score равен; раньше стоит меньшая стартовая цена за мероприятие.'
        else:
            decided_by = 'id'
            reason = 'Округлённый score и цена равны; порядок определён ID по возрастанию, а не качеством профиля.'
        deltas: dict[ComponentName, float | None] = {}
        for left, right in zip(by_id[higher.id].components, by_id[lower.id].components):
            deltas[left.component] = (left.contribution - right.contribution
                                      if left.contribution is not None and right.contribution is not None else None)
        decisions.append(ComparisonDecision.model_validate({
            'higher_id': higher.id, 'lower_id': lower.id, 'decided_by': decided_by,
            'score_gap': round(higher.score - lower.score, 6), 'contribution_deltas': deltas, 'reason': reason,
        }))
    funnel = []
    for step in response.diagnostics.steps:
        skipped = (step.stage == 'language' and query.language is None) or (step.stage == 'duration' and query.duration is None)
        funnel.append(FunnelStepDetail(**step.model_dump(), application='not_requested' if skipped else 'applied',
                                       reason='Условие отсутствует в запросе; кандидаты не исключались.' if skipped else
                                       'Применён общий предикат отбора; неприменимые для услуги значения не подтверждают совпадение.'))
    formats = {}
    for card in response.results:
        actual = card.evidence.format.actual
        # evaluate() stores the source list, not extracted words from an explanation.
        assert isinstance(actual, list)  # A returned candidate passed the format check.
        formats[card.id] = actual
    return DetailedMatchResponse(
        query=query, match=response, ranking=ranking, funnel=funnel,
        comparison=ComparisonContext(candidate_ids=[card.id for card in response.results], formats=formats,
                                     ordering=['score_desc', 'price_asc', 'id_asc'], decisions=decisions),
    )
