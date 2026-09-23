"""Small boundary to the existing AI service. A failure never changes eligibility."""
import json
import logging
from typing import Literal, Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, ValidationError

from .catalog import Catalog
from .schemas import SearchParams, UnitScore

logger = logging.getLogger(__name__)


class TextScore(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str
    semantic: UnitScore | None
    lexical: UnitScore | None


class SimilarityResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')
    model: Literal['tfidf-v1']
    scores: list[TextScore]


class SemanticUnavailable(RuntimeError):
    def __init__(self, message: str, code: str = 'semantic_unavailable'):
        super().__init__(message)
        self.code = code


class SemanticProvider(Protocol):
    def score(self, query: SearchParams, catalog: Catalog) -> dict[str, TextScore]: ...


class HttpSemanticProvider:
    def __init__(self, base_url: str, timeout: float = 2.0):
        if not 0 < timeout <= 10:
            raise ValueError('AI_TIMEOUT_SECONDS must be in (0, 10]')
        self.url = base_url.rstrip('/') + '/similarity'
        self.timeout = timeout

    def score(self, query: SearchParams, catalog: Catalog) -> dict[str, TextScore]:
        # Full snapshot fixes the TF-IDF corpus across dates and eligibility changes.
        payload = {'query': f'{query.category} {query.event_type}',
                   'documents': [{'id': p.id, 'text': p.description} for p in catalog.profiles]}
        request = Request(self.url, json.dumps(payload).encode(), {'Content-Type': 'application/json'})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read(1_000_001)
            if len(raw) > 1_000_000:
                raise ValueError('AI response too large')
            result = SimilarityResponse.model_validate_json(raw)
            scores = {item.id: item for item in result.scores}
            if len(scores) != len(result.scores) or scores.keys() != {p.id for p in catalog.profiles}:
                raise ValueError('AI returned inconsistent profile IDs')
            return scores
        except (URLError, OSError, ValueError, ValidationError) as exc:
            logger.warning('Text similarity unavailable: %s', type(exc).__name__)
            reason = exc.reason if isinstance(exc, URLError) else exc
            code = ('semantic_timeout' if isinstance(reason, TimeoutError) else
                    'semantic_invalid_response' if isinstance(exc, ValueError) else 'semantic_unreachable')
            raise SemanticUnavailable('Text similarity unavailable', code) from exc
