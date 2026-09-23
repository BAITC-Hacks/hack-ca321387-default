"""HTTP boundaries for discovery: real rules, no semantic calls, unchanged legacy schema."""
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.catalog import Catalog
from backend.app.discovery import AvailabilityResponse, DemoPresetsResponse, build_demo_presets
from backend.app.main import create_app
from backend.app.matching import MatchingService
from backend.app.schemas import ErrorResponse, SearchParams
from backend.app.semantic import TextScore
from backend.tests.test_matching import BASE, catalog, profile


class ForbiddenSemantic:
    def score(self, query: SearchParams, snapshot: Catalog) -> dict[str, TextScore]:
        raise AssertionError('Discovery must not call semantic ranking')


class FeatureRoutesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.environment = patch.dict(os.environ, {'SEMANTIC_MODE': 'disabled', 'ENABLE_MATCH_TRACE': 'false'})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_discovery_http_uses_same_filters_without_ml(self) -> None:
        snapshot = catalog(profile('free'), profile('busy', busy_dates=['2026-11-18']),
                           profile('expensive', price=2_000_000), profile('short', max_hours=3),
                           profile('language', languages=['английский']), profile('calendar', busy_dates=None))
        with TestClient(create_app(snapshot, ForbiddenSemantic())) as client:
            response = client.post('/api/availability', json={'query': BASE, 'days_before': 1, 'days_after': 1})
            self.assertEqual(response.status_code, 200, response.text)
            result = AvailabilityResponse.model_validate(response.json())
            self.assertEqual([day.available for day in result.days], [2, 1, 2])
            self.assertEqual(result.recommended_date.isoformat(), '2026-11-17')
            for day in result.days:
                actual = MatchingService(snapshot).match(SearchParams(**{**BASE, 'date': day.date}))
                self.assertEqual(actual.total_eligible, day.available)
            presets = client.get('/api/demo-presets')
            self.assertEqual(presets.status_code, 200, presets.text)
            DemoPresetsResponse.model_validate(presets.json())
            schema = client.get('/openapi.json').json()
            legacy_schema = schema['paths']['/api/match']['post']['responses']['200']['content']['application/json']['schema']
            self.assertEqual(legacy_schema, {'$ref': '#/components/schemas/MatchResponse'})
            for route in ('/api/match/details', '/api/availability', '/api/demo-presets'):
                self.assertIn(route, schema['paths'])
            self.assertNotIn('/api/debug/match', schema['paths'])

    def test_discovery_validation_uses_existing_error_contract(self) -> None:
        with TestClient(create_app(catalog(profile('free')))) as client:
            invalid = [
                {'query': BASE, 'date_from': '2026-09-22', 'date_to': '2026-09-24'},
                {'query': BASE, 'date_from': '2026-11-20', 'date_to': '2026-11-18'},
                {'query': BASE, 'days_before': 20, 'days_after': 20},
                {'query': BASE, 'days_before': True},
                {'query': {**BASE, 'budget': 0}},
                {'query': {**BASE, 'category': 'Unknown'}},
            ]
            for query in invalid:
                with self.subTest(query=query):
                    response = client.post('/api/availability', json=query)
                    self.assertEqual(response.status_code, 422)
                    error = ErrorResponse.model_validate(response.json())
                    self.assertTrue(error.detail)
            unknown = client.post('/api/availability', json={'query': {**BASE, 'city': 'Unknown'}}).json()
            self.assertEqual(unknown['detail'][0]['field'], 'query.city')
            nested = client.post('/api/availability', json={'query': {**BASE, 'budget': 0}}).json()
            self.assertEqual(nested['detail'][0]['field'], 'query.budget')
            self.assertIn('Бюджет', nested['detail'][0]['message'])

    def test_presets_cache_belongs_to_snapshot_and_rebuilds_on_replacement(self) -> None:
        first = catalog(profile('first'))
        second = Catalog((profile('busy', busy_dates=None),), 'changed-snapshot')
        app = create_app(first)
        with TestClient(app) as client, patch('backend.app.main.build_demo_presets', wraps=build_demo_presets) as build:
            initial = client.get('/api/demo-presets').json()
            self.assertTrue(initial['presets'])
            self.assertEqual(initial, client.get('/api/demo-presets').json())
            self.assertEqual(build.call_count, 1)
            app.state.matching = MatchingService(second)
            changed = client.get('/api/demo-presets').json()
            self.assertEqual(changed['data_version'], 'changed-snapshot')
            self.assertEqual(changed['presets'], [])
            self.assertEqual(build.call_count, 2)

    def test_catalog_unavailable_never_becomes_empty_discovery(self) -> None:
        with patch.dict(os.environ, {'DATASET_PATH': '/does-not-exist'}):
            with self.assertLogs('backend.app.main', level='ERROR'), TestClient(create_app()) as client:
                responses = [client.get('/api/demo-presets'),
                             client.post('/api/availability', json={'query': BASE}),
                             client.post('/api/match/details', json=BASE)]
                for response in responses:
                    self.assertEqual(response.status_code, 503)
                    self.assertEqual(response.json()['code'], 'catalog_unavailable')


if __name__ == '__main__':
    unittest.main()
