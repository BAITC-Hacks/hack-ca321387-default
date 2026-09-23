"""HTTP boundaries for discovery: real rules, no semantic calls, unchanged legacy schema."""
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.catalog import Catalog
from backend.app.discovery import AvailabilityResponse
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


if __name__ == '__main__':
    unittest.main()
