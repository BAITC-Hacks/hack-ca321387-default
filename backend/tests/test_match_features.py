"""Contract, explanation and trace tests through the real matching pipeline."""
import math
import os
import unittest
from uuid import UUID
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.catalog import Catalog, Profile
from backend.app.feature_schemas import DetailedMatchResponse
from backend.app.main import create_app
from backend.app.matching import MatchingService
from backend.app.rules import STAGES
from backend.app.schemas import ErrorResponse, SearchParams
from backend.app.semantic import SemanticUnavailable, TextScore

BASE: dict[str, object] = {
    'city': 'Алматы', 'date': '2026-11-18', 'event_type': 'корпоратив',
    'category': 'Ведущий', 'budget': 1_000_000, 'language': 'русский', 'duration': 6,
}


def request(**changes: object) -> SearchParams:
    return SearchParams.model_validate(BASE | changes)


def profile(identifier: str, **changes: object) -> Profile:
    return Profile.model_validate({
        'id': identifier, 'name': f'Подрядчик {identifier}', 'city': 'Алматы',
        'categories': ['Ведущий'], 'price': 500_000, 'formats': ['корпоратив'],
        'languages': ['русский'], 'max_hours': 8, 'duration_policy': 'limited',
        'busy_dates': [], 'description': 'Ведущий корпоратив с импровизацией',
    } | changes)


def catalog(*records: Profile) -> Catalog:
    return Catalog(tuple(records), 'features-test-snapshot')


class CountingSemantic:
    """Replace only the remote score source, never filtering or matching."""

    def __init__(self, scores: dict[str, tuple[float | None, float | None]] | None = None,
                 failure: SemanticUnavailable | None = None) -> None:
        self.scores = scores or {}
        self.failure = failure
        self.calls = 0

    def score(self, query: SearchParams, snapshot: Catalog) -> dict[str, TextScore]:
        self.calls += 1
        if self.failure is not None:
            raise self.failure
        return {
            record.id: TextScore(id=record.id, semantic=self.scores.get(record.id, (.4, .2))[0],
                                 lexical=self.scores.get(record.id, (.4, .2))[1])
            for record in snapshot.profiles
        }


class MatchFeatureTests(unittest.TestCase):
    def setUp(self) -> None:
        environment = patch.dict(os.environ, {'SEMANTIC_MODE': 'disabled', 'ENABLE_MATCH_TRACE': 'false'})
        environment.start()
        self.addCleanup(environment.stop)


    def test_score_contributions_preserve_raw_inputs_at_rounding_boundaries(self) -> None:
        # The rounded public component can produce a different final rounding.
        # Details must retain actual inputs without altering the legacy score.
        for semantic, expected in ((.50000082, .3), (.50000085, .300001)):
            with self.subTest(semantic=semantic):
                provider = CountingSemantic({'one': (semantic, 0)})
                service = MatchingService(catalog(profile('one', price=1_000_000)), provider)
                result = service.details(request(duration=None))
                detail = result.ranking[0]
                card = result.match.results[0]
                components = {item.component: item for item in detail.components}
                self.assertEqual(detail.score, expected)
                self.assertEqual(components['semantic'].value, semantic)
                self.assertEqual(components['budget'].source_fields, ['price_from_kzt', 'budget'])
                self.assertEqual(detail.decomposition, 'weighted_sum')
                self.assertEqual(detail.interpretation, 'fit_not_probability')
                self.assertEqual((detail.scale_min, detail.scale_max), (0, 1))
                total = sum(item.contribution for item in detail.components if item.contribution is not None)
                self.assertEqual(total, detail.unrounded_score)
                self.assertEqual(total + detail.rounding_adjustment, card.score)
                self.assertEqual(round(total, 6), card.score)
                self.assertLessEqual(abs(detail.rounding_adjustment), .0000005)
                if semantic == .50000082:
                    self.assertIsNotNone(card.score_breakdown.semantic)
                    self.assertIsNotNone(card.score_weights.semantic)
                    naive = (card.score_breakdown.semantic or 0) * (card.score_weights.semantic or 0)
                    self.assertNotEqual(round(naive, 6), card.score)


    def test_details_http_contract_and_validation_keep_ordinary_search_compatible(self) -> None:
        with TestClient(create_app(catalog(profile('one'), profile('two')))) as client:
            ordinary = client.post('/api/match', json=BASE)
            detailed = client.post('/api/match/details', json=BASE)
            self.assertEqual(ordinary.status_code, 200)
            self.assertEqual(detailed.status_code, 200, detailed.text)
            DetailedMatchResponse.model_validate(detailed.json())
            self.assertEqual(detailed.json()['match'], ordinary.json())
            self.assertNotIn('ranking', ordinary.json())
            for changes in ({'category': 'unknown'}, {'duration': 13}, {'date': '2026-11-18T00:00:00Z'}):
                invalid = client.post('/api/match/details', json=BASE | changes)
                self.assertEqual(invalid.status_code, 422)
                ErrorResponse.model_validate(invalid.json())


if __name__ == '__main__':
    unittest.main()
