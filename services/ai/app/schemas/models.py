from datetime import date
from typing import Literal

from pydantic import AliasChoices, BaseModel, Field


class RankQuery(BaseModel):
    city: str = Field(min_length=1)
    date: date
    event_type: str = Field(min_length=1)
    category: str = Field(min_length=1)
    budget: int = Field(gt=0)
    language: str | None = None
    duration: float | None = Field(default=None, gt=0)
    preferences: str = ""


class Candidate(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(default="", validation_alias=AliasChoices("name", "anon_name"))
    category: str = ""
    city: str = ""
    description: str = ""
    price: int = Field(ge=0, validation_alias=AliasChoices("price", "price_from_kzt"))
    languages: list[str] = Field(default_factory=list)
    formats: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("formats", "event_formats"),
    )
    max_hours: float | None = Field(default=None, gt=0)
    synthetic: bool = False


class RankRequest(BaseModel):
    query: RankQuery
    candidates: list[Candidate]
    limit: int = Field(default=3, ge=1, le=3)


class EvidenceItem(BaseModel):
    matched: bool | None = None
    score: float | None = Field(default=None, ge=0, le=1)
    reason: str
    source_field: str = ""


class CandidateEvidence(BaseModel):
    budget: EvidenceItem
    language: EvidenceItem
    format: EvidenceItem
    duration: EvidenceItem
    semantic: EvidenceItem


class ScoreBreakdown(BaseModel):
    semantic: float = Field(ge=0, le=1)
    lexical: float = Field(ge=0, le=1)
    budget: float = Field(ge=0, le=1)
    duration: float = Field(ge=0, le=1)


class RankedCandidate(BaseModel):
    id: str
    name: str
    category: str
    city: str
    price: int
    score: float = Field(ge=0, le=1)
    semantic_score: float = Field(ge=0, le=1)
    score_breakdown: ScoreBreakdown
    evidence: CandidateEvidence
    explanation: str = ""
    synthetic: bool = False


class RankResponse(BaseModel):
    outcome: Literal["matched", "no_candidates"]
    candidates: list[RankedCandidate]
    total_eligible: int
    model_info: dict[str, str | bool]


class ConstraintDoctorRequest(BaseModel):
    city: str
    category: str
    counts: dict[str, int] = Field(default_factory=dict)
    requested_budget: int | None = Field(default=None, gt=0)
    minimum_price: int | None = Field(default=None, ge=0)
    selected_date: date | None = None


class ConstraintDoctorResponse(BaseModel):
    outcome: Literal["category_absent_in_city", "constraints_failed", "matched"]
    summary: str
    funnel: list[dict[str, int | str]]
    primary_blocker: str | None = None


class WhatIfRequest(BaseModel):
    selected_date: date
    date_counts: dict[date, int]


class WhatIfDate(BaseModel):
    date: date
    available: int = Field(ge=0)


class WhatIfResponse(BaseModel):
    selected_date: date
    selected_available: int = Field(ge=0)
    alternatives: list[WhatIfDate]
    explanation: str
