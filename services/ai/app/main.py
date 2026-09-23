from fastapi import FastAPI
from app.ranking.semantic import cached_similarity
from app.schemas.models import SimilarityRequest, SimilarityResponse, TextSimilarity

from app.constraint_doctor.doctor import diagnose_constraints
from app.explanations.generator import build_explanation
from app.ranking.scorer import rank_candidates
from app.schemas.models import (
    ConstraintDoctorRequest,
    ConstraintDoctorResponse,
    RankRequest,
    RankResponse,
    WhatIfRequest,
    WhatIfResponse,
)

app = FastAPI(title="EventLens AI Service", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "eventlens-ai", "ranking_version": "tfidf-v1"}


@app.post("/rank", response_model=RankResponse)
def rank(request: RankRequest) -> RankResponse:
    response = rank_candidates(request)
    for candidate in response.candidates:
        candidate.explanation = build_explanation(candidate.evidence)
    return response


@app.post("/constraints/diagnose", response_model=ConstraintDoctorResponse)
def diagnose(request: ConstraintDoctorRequest) -> ConstraintDoctorResponse:
    return diagnose_constraints(request)


@app.post("/what-if", response_model=WhatIfResponse)
def what_if(request: WhatIfRequest) -> WhatIfResponse:
    selected_count = request.date_counts.get(request.selected_date, 0)
    alternatives = [
        {"date": date, "available": count}
        for date, count in sorted(request.date_counts.items())
        if date != request.selected_date
    ]
    alternatives.sort(key=lambda item: (-item["available"], item["date"]))
    best = alternatives[0] if alternatives else None
    message = (
        f"На выбранную дату доступно {selected_count} кандидатов. "
        if best is None
        else f"На выбранную дату доступно {selected_count} кандидатов; "
        f"{best['date']} — {best['available']} кандидатов."
    )
    return WhatIfResponse(
        selected_date=request.selected_date,
        selected_available=selected_count,
        alternatives=alternatives,
        explanation=message,
    )



@app.post('/similarity', response_model=SimilarityResponse)
def similarity(request: SimilarityRequest) -> SimilarityResponse:
    """Text signals only. Backend owns hard constraints, score, order and evidence."""
    scores = cached_similarity(request.query, tuple(doc.text for doc in request.documents))
    return SimilarityResponse(scores=[
        TextSimilarity(id=doc.id, semantic=semantic, lexical=lexical)
        for doc, (semantic, lexical) in zip(request.documents, scores)
    ])
