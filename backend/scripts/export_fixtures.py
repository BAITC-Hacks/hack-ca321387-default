"""Recorded responses from the real matcher; the browser contains no matching rules."""
import json
from datetime import date, timedelta
from pathlib import Path

from backend.app.catalog import DEFAULT_DATASET, load_catalog
from backend.app.matching import MatchingService
from backend.app.schemas import SearchParams

ROOT = Path(__file__).resolve().parents[2]


def fixture_bundle() -> dict:
    service = MatchingService(load_catalog(DEFAULT_DATASET))
    base = dict(city='Алматы', date='2026-11-18', event_type='корпоратив', category='Ведущий',
                budget=1_000_000, language='русский', duration=6)
    scenarios = [base, {**base, 'budget': 100},
                 {**base, 'date': '2026-10-15', 'category': 'Флорист', 'event_type': 'свадьба', 'budget': 300_000, 'duration': None},
                 {**base, 'city': 'Астана', 'date': '2026-12-20', 'category': 'Флорист', 'event_type': 'свадьба', 'budget': 300_000, 'duration': None},
                 {**base, 'city': 'Зарубежье'}]
    fixtures = []
    for scenario in scenarios:
        for offset in range(-4, 5):
            query = SearchParams.model_validate({**scenario, 'date': (date.fromisoformat(scenario['date']) + timedelta(days=offset)).isoformat()})
            response = service.match(query)
            fixtures.append({'request': query.model_dump(mode='json'), 'response': response.model_dump(mode='json')})
    return {'metadata': service.catalog.metadata().model_dump(mode='json'), 'fixtures': fixtures}


if __name__ == '__main__':
    (ROOT / 'frontend/src/mocks/fixtures.json').write_text(json.dumps(fixture_bundle(), ensure_ascii=False, separators=(',', ':')) + '\n')
