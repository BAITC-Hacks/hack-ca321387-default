"""Present facts captured by the matcher; never rerun selection or model inference."""
from dataclasses import dataclass

from .feature_schemas import ComponentName, DetailedMatchResponse, RankingDetail, ScoreComponentDetail
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
    return DetailedMatchResponse(query=query, match=response, ranking=ranking)
