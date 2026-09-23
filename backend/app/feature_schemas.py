"""Opt-in product details and developer trace; legacy response models stay unchanged."""
from typing import Literal

from pydantic import Field

from .schemas import DiagnosticStep, MatchResponse, ModelInfo, Schema, SearchParams, UnitScore

ComponentName = Literal['semantic', 'lexical', 'budget', 'duration']


class ScoreComponentDetail(Schema):
    component: ComponentName
    state: Literal['active', 'not_requested', 'not_applicable', 'unavailable']
    value: UnitScore | None
    weight: UnitScore | None
    contribution: UnitScore | None
    source_fields: list[str]
    reason: str


class RankingDetail(Schema):
    candidate_id: str
    position: int = Field(ge=1, le=3)
    score: UnitScore
    scale_min: Literal[0] = 0
    scale_max: Literal[1] = 1
    interpretation: Literal['fit_not_probability'] = 'fit_not_probability'
    decomposition: Literal['weighted_sum'] = 'weighted_sum'
    components: list[ScoreComponentDetail]
    unrounded_score: float = Field(ge=0, allow_inf_nan=False)
    rounding_adjustment: float
    rounding: Literal['python_round_6_decimal_places'] = 'python_round_6_decimal_places'


class FunnelStepDetail(DiagnosticStep):
    application: Literal['applied', 'not_requested']
    reason: str


class ComparisonDecision(Schema):
    higher_id: str
    lower_id: str
    decided_by: Literal['score', 'price', 'id']
    score_gap: float = Field(ge=0)
    contribution_deltas: dict[ComponentName, float | None]
    reason: str


class ComparisonContext(Schema):
    # Characteristics and hard-check evidence are reused from match.results, by ID.
    candidate_ids: list[str] = Field(max_length=3)
    currency: Literal['KZT'] = 'KZT'
    price_unit: Literal['event'] = 'event'
    price_basis: Literal['starting_price'] = 'starting_price'
    price_note: str = 'Сравниваются стартовые цены за мероприятие; состав пакета и окончательная смета неизвестны.'
    duration_unit: Literal['hours'] = 'hours'
    duration_note: str = 'Сравнивать только известные лимиты присутствия; not_applicable не означает 0 или бесконечность.'
    formats: dict[str, list[str]]
    ordering: list[Literal['score_desc', 'price_asc', 'id_asc']]
    decisions: list[ComparisonDecision]


class DetailedMatchResponse(Schema):
    query: SearchParams
    match: MatchResponse
    ranking: list[RankingDetail] = Field(max_length=3)
    funnel: list[FunnelStepDetail]
    comparison: ComparisonContext
