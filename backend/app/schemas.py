"""Public API contract. OpenAPI is the schema source for frontend fixtures."""
from datetime import date as Date
from typing import Annotated, Literal
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

MIN_DATE = Date(2026, 9, 23)
MAX_DATE = Date(2026, 12, 31)
MAX_BUDGET = 100_000_000
UnitScore = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
Stage = Literal['category', 'city', 'date', 'format', 'budget', 'language', 'duration']


def normalize(value: str) -> str:
    return ' '.join(value.casefold().replace('ё', 'е').split())


class Schema(BaseModel):
    model_config = ConfigDict(extra='forbid')


class SearchParams(Schema):
    city: str = Field(min_length=1, max_length=100)
    date: Date = Field(ge=MIN_DATE, le=MAX_DATE)
    event_type: str = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1, max_length=100)
    budget: float = Field(gt=0, le=MAX_BUDGET, allow_inf_nan=False, strict=True)
    language: str | None = Field(default=None, max_length=100)
    duration: int | None = Field(default=None, ge=1, le=12, strict=True)

    @field_validator('date', mode='before')
    @classmethod
    def calendar_date(cls, value: object) -> object:
        if isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            return value
        if type(value) is Date:
            return value
        raise ValueError('Дата должна иметь формат YYYY-MM-DD')

    @field_validator('city', 'event_type', 'category', 'language', mode='before')
    @classmethod
    def trim(cls, value: object) -> object:
        return ' '.join(value.split()) if isinstance(value, str) else value

    @field_validator('language', mode='before')
    @classmethod
    def no_preference(cls, value: object) -> object:
        if isinstance(value, str) and normalize(value) in ('', 'не важно'):
            return None
        return value


class EvidenceItem(Schema):
    matched: bool | None
    reason: str
    score: UnitScore | None = None
    source_field: str
    code: str
    # Structured facts, never reconstructed from reason/explanation.
    requested: str | float | None = None
    actual: str | float | list[str] | None = None


class EvidenceLedger(Schema):
    category: EvidenceItem
    city: EvidenceItem
    date: EvidenceItem
    format: EvidenceItem
    budget: EvidenceItem
    language: EvidenceItem
    duration: EvidenceItem
    semantic: EvidenceItem


class ScoreBreakdown(Schema):
    semantic: UnitScore | None
    lexical: UnitScore | None
    budget: UnitScore
    duration: UnitScore | None


class Contractor(Schema):
    id: str
    name: str
    categories: list[str]
    city: str
    price: float = Field(ge=0, allow_inf_nan=False)
    price_basis: Literal['event_from'] = 'event_from'
    score: UnitScore
    semantic_score: UnitScore | None
    synthetic: bool
    city_imputed: bool
    price_imputed: bool
    evidence: EvidenceLedger
    explanation: str
    score_breakdown: ScoreBreakdown
    score_weights: ScoreBreakdown
    max_hours: float | None
    duration_policy: Literal['limited', 'not_applicable', 'unknown']
    languages: list[str]
    description: str


class DiagnosticStep(Schema):
    stage: Stage
    label: str
    before: int = Field(ge=0)
    after: int = Field(ge=0)
    excluded: int = Field(ge=0)
    count: int = Field(ge=0)  # Existing UI alias for after.


class BudgetAlternative(Schema):
    budget: float = Field(gt=0, le=MAX_BUDGET)
    available: int = Field(gt=0)


class Diagnostics(Schema):
    counts: dict[Stage, int]
    steps: list[DiagnosticStep]
    primary_blocker: Stage | None
    summary: str
    budget_alternative: BudgetAlternative | None = None


class AvailabilityDay(Schema):
    date: Date
    available: int = Field(ge=0)


class ModelInfo(Schema):
    ranking_version: str
    data_version: str
    semantic_model: Literal['tfidf-v1', 'unavailable', 'disabled', 'not_used']
    fallback_used: bool


class MatchResponse(Schema):
    status: Literal['matched', 'category_not_found', 'no_match']
    results: list[Contractor] = Field(max_length=3)
    diagnostics: Diagnostics
    availability: list[AvailabilityDay]
    total_eligible: int = Field(ge=0)
    model_info: ModelInfo


class Metadata(Schema):
    cities: list[str]
    categories: list[str]
    event_types: list[str]
    languages: list[str]
    min_date: Date = MIN_DATE
    max_date: Date = MAX_DATE
    min_budget_exclusive: float = 0
    max_budget: float = MAX_BUDGET
    min_duration: int = 1
    max_duration: int = 12


class FieldError(Schema):
    field: str | None
    code: str
    message: str


class ErrorResponse(Schema):
    code: str
    message: str
    detail: list[FieldError] = Field(default_factory=list)
