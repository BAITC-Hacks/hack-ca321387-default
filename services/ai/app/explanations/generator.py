from app.explanations.evidence import evidence_reasons
from app.schemas.models import CandidateEvidence


def build_explanation(evidence: CandidateEvidence) -> str:
    facts = evidence_reasons(evidence)
    semantic = evidence.semantic.reason
    if not facts:
        return semantic
    return f"{'; '.join(facts[:3])}. {semantic}."
