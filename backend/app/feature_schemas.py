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


class DetailedMatchResponse(Schema):
    query: SearchParams
    match: MatchResponse
    ranking: list[RankingDetail] = Field(max_length=3)
