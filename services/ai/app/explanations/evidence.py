from app.schemas.models import CandidateEvidence


def evidence_reasons(evidence: CandidateEvidence) -> list[str]:
    return [
        item.reason
        for item in (evidence.budget, evidence.language, evidence.format, evidence.duration)
        if item.matched is not False
    ]
