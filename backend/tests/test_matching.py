import json
import os
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.error import URLError

from fastapi.testclient import TestClient

from backend.app.catalog import Catalog, CatalogError, DEFAULT_DATASET, Profile, load_catalog
from backend.app.main import create_app
from backend.app.matching import MatchingService
from backend.app.rules import STAGES, evaluate
from backend.app.schemas import MAX_BUDGET, ErrorResponse, MatchResponse, SearchParams
from backend.app.semantic import HttpSemanticProvider, SemanticUnavailable
from backend.scripts.export_contract import ROOT, contract

BASE = dict(city='Алматы', date='2026-11-18', event_type='корпоратив', category='Ведущий',
            budget=1_000_000, language='русский', duration=6)


def profile(identifier: str, **overrides: object) -> Profile:
    return Profile.model_validate(dict(id=identifier, name=f'Подрядчик {identifier}', city='Алматы',
        categories=['Ведущий'], price=500000, formats=['корпоратив'], languages=['русский'],
        max_hours=8, duration_policy='limited', busy_dates=[], description='Ведущий корпоратив с импровизацией') | overrides)


def catalog(*profiles: Profile) -> Catalog:
    return Catalog(tuple(profiles), 'test-snapshot')


class MatchingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.env = patch.dict(os.environ, {'SEMANTIC_MODE': 'disabled'})
        self.env.start()
        self.addCleanup(self.env.stop)

    def response(self, profiles: tuple[Profile, ...], query: dict | None = None) -> dict:
        with TestClient(create_app(catalog(*profiles))) as client:
            response = client.post('/api/match', json=query or BASE)
            self.assertEqual(response.status_code, 200, response.text)
            MatchResponse.model_validate(response.json())
            return response.json()

    def test_one_two_three_and_top_k(self) -> None:
        for size in (1, 2, 3, 5):
            with self.subTest(size=size):
                result = self.response(tuple(profile(str(i)) for i in range(size)))
                self.assertEqual(result['status'], 'matched')
                self.assertEqual(len(result['results']), min(size, 3))
                self.assertEqual(result['total_eligible'], size)
                self.assertEqual(result['availability'][2]['available'], size)

    def test_all_constraints_exclude_and_funnel_is_sequential(self) -> None:
        records = (profile('category', categories=['Фотограф']), profile('city', city='Астана'),
                   profile('busy', busy_dates=['2026-11-18']), profile('format', formats=['свадьба']),
                   profile('budget', price=2_000_000), profile('language', languages=['казахский']),
                   profile('duration', max_hours=4))
        result = self.response(records)
        self.assertEqual(result['status'], 'no_match')
        self.assertEqual(result['diagnostics']['primary_blocker'], 'duration')
        self.assertEqual([s['count'] for s in result['diagnostics']['steps']], [6, 5, 4, 3, 2, 1, 0])
        for i, step in enumerate(result['diagnostics']['steps']):
            self.assertEqual(step['before'], 7-i)
            self.assertEqual(step['after'], 6-i)
            self.assertEqual(step['excluded'], 1)
        self.assertEqual(result['results'], [])

    def test_each_mandatory_failure_is_never_returned(self) -> None:
        changes = [{'busy_dates': ['2026-11-18']}, {'formats': []}, {'price': 1_000_001},
                   {'languages': []}, {'max_hours': 5}, {'busy_dates': None}, {'price': None},
                   {'max_hours': None, 'duration_policy': 'unknown'}]
        for change in changes:
            with self.subTest(change=change):
                # Known vocabulary remains present in another city.
                result = self.response((profile('bad', **change), profile('vocabulary', city='Астана')))
                self.assertEqual(result['results'], [])
                self.assertEqual(result['status'], 'no_match')

    def test_category_absent_differs_from_unknown(self) -> None:
        result = self.response((profile('host', city='Астана'), profile('photo', categories=['Фотограф'])))
        self.assertEqual(result['status'], 'category_not_found')
        with TestClient(create_app(catalog(profile('1')))) as client:
            for field in ('city', 'category', 'event_type', 'language'):
                response = client.post('/api/match', json={**BASE, field: 'unknown'})
                self.assertEqual(response.status_code, 422)
                self.assertEqual(response.json()['code'], 'unknown_option')
                self.assertEqual(response.json()['detail'][0]['field'], field)

    def test_first_zero_not_largest_independent_failure(self) -> None:
        result = self.response((profile('busy', busy_dates=['2026-11-18'], price=2_000_000),))
        self.assertEqual(result['diagnostics']['primary_blocker'], 'date')
        self.assertEqual(result['diagnostics']['counts']['budget'], 0)
        self.assertIn('не гарантирует', result['diagnostics']['summary'])
        self.assertIsNone(result['diagnostics']['budget_alternative'])

    def test_budget_alternative_rechecks_all_other_constraints(self) -> None:
        records = (profile('cheap-but-short', price=1_200_000, max_hours=3), profile('eligible', price=1_500_000),
                   profile('busy', price=1_100_000, busy_dates=['2026-11-18']))
        result = self.response(records)
        suggestion = result['diagnostics']['budget_alternative']
        self.assertEqual(suggestion, {'budget': 1_500_000, 'available': 1})
        retried = self.response(records, {**BASE, 'budget': suggestion['budget']})
        self.assertEqual(retried['total_eligible'], suggestion['available'])

    def test_evidence_and_optional_nulls(self) -> None:
        record = profile('1', synthetic=True, max_hours=6, price=1_000_000)
        result = self.response((record,))['results'][0]
        self.assertEqual(result['evidence']['budget']['actual'], BASE['budget'])
        self.assertEqual(result['evidence']['date']['requested'], BASE['date'])
        self.assertEqual(result['evidence']['duration']['actual'], 6)
        self.assertEqual(result['price'], record.price)
        self.assertTrue(result['synthetic'])
        for stage, _ in STAGES:
            expected = evaluate(record, SearchParams(**BASE)).checks[stage].model_dump(mode='json')
            self.assertEqual(result['evidence'][stage], expected)
        optional = self.response((record,), {**BASE, 'language': None, 'duration': None})['results'][0]
        self.assertIsNone(optional['evidence']['language']['matched'])
        self.assertIsNone(optional['evidence']['duration']['matched'])
        self.assertIsNone(optional['score_breakdown']['duration'])
        self.assertIsNone(optional['semantic_score'])
        self.assertIsNone(optional['evidence']['semantic']['matched'])

    def test_not_applicable_duration_is_not_confirmed_match(self) -> None:
        result = self.response((profile('florist', max_hours=None, duration_policy='not_applicable'),))
        self.assertEqual(result['status'], 'matched')
        duration = result['results'][0]['evidence']['duration']
        self.assertIsNone(duration['matched'])
        self.assertEqual(duration['code'], 'not_applicable')

    def test_stable_ties_normalization_and_optional_input(self) -> None:
        records = catalog(profile('Z'), profile('A'), profile('B'))
        service = MatchingService(records)
        expected = service.match(SearchParams(**BASE))
        self.assertEqual([p.id for p in expected.results], ['A', 'B', 'Z'])
        for _ in range(20):
            self.assertEqual(service.match(SearchParams(**BASE)), expected)
        changed = {**BASE, 'city': '  аЛМАТЫ  ', 'category': 'ВЕДУЩИЙ', 'event_type': 'КОРПОРАТИВ', 'language': ' РУССКИЙ '}
        self.assertEqual(service.match(SearchParams(**changed)), expected)
        for value in (None, '', 'Не важно'):
            result = service.match(SearchParams(**{**BASE, 'language': value}))
            self.assertIsNone(result.results[0].evidence.language.matched)

    def test_date_alternatives_match_repeat_requests(self) -> None:
        service = MatchingService(catalog(profile('busy', busy_dates=['2026-11-18']), profile('free')))
        result = service.match(SearchParams(**BASE))
        for day in result.availability:
            other = service.match(SearchParams(**{**BASE, 'date': day.date}))
            self.assertEqual(day.available, other.total_eligible)
        self.assertEqual([p.id for p in result.results], ['free'])
        self.assertEqual(service.match(SearchParams(**{**BASE, 'date': '2026-11-19'})).total_eligible, 2)

    def test_validation_boundaries_and_error_contract(self) -> None:
        with TestClient(create_app(catalog(profile('1')))) as client:
            for field, values in {
                'date': ['2026-09-22', '2027-01-01', '2026-11-31', '2026-11-18T00:00:00Z', 1794952800],
                'budget': [0, -1, MAX_BUDGET+1, '500000', True, None],
                'duration': [0, 13, 1.5, '6', True],
                'city': ['', None],
            }.items():
                for value in values:
                    with self.subTest(field=field, value=value):
                        response = client.post('/api/match', json={**BASE, field: value})
                        self.assertEqual(response.status_code, 422)
                        ErrorResponse.model_validate(response.json())
            for special in ('NaN', 'Infinity', '-Infinity'):
                body = json.dumps(BASE).replace('1000000', special)
                response = client.post('/api/match', content=body, headers={'Content-Type': 'application/json'})
                self.assertEqual(response.status_code, 422)
            for day in ('2026-09-23', '2026-12-31'):
                response = client.post('/api/match', json={**BASE, 'date': day, 'budget': MAX_BUDGET, 'duration': 1})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(all('2026-09-23' <= d['date'] <= '2026-12-31' for d in response.json()['availability']))
            minimal = {k: v for k, v in BASE.items() if k not in ('language', 'duration')}
            self.assertEqual(client.post('/api/match', json=minimal).status_code, 200)
            self.assertEqual(client.post('/api/match', json={**minimal, 'budget': 0.01, 'duration': 12}).status_code, 200)
            for field in ('city', 'date', 'category', 'budget', 'event_type'):
                self.assertEqual(client.post('/api/match', json={k: v for k, v in BASE.items() if k != field}).status_code, 422)
            self.assertEqual(client.get('/api/does-not-exist').json()['code'], 'route_not_found')
            self.assertEqual(client.post('/api/match', content='{').status_code, 422)

    def test_dependency_timeout_and_invalid_data_degrade(self) -> None:
        provider = HttpSemanticProvider('http://localhost:8100', .1)
        service = MatchingService(catalog(profile('free'), profile('busy', busy_dates=['2026-11-18'])), provider)
        for error in (TimeoutError(), URLError('offline'), ValueError('malformed')):
            with patch('backend.app.semantic.urlopen', side_effect=error):
                result = service.match(SearchParams(**BASE))
                self.assertEqual([p.id for p in result.results], ['free'])
                self.assertEqual(result.model_info.semantic_model, 'unavailable')
                self.assertTrue(result.model_info.fallback_used)
                self.assertIsNone(result.results[0].semantic_score)
        with patch('backend.app.semantic.urlopen') as opener:
            opener.return_value.__enter__.return_value.read.return_value = b'{"model":"tfidf-v1","scores":[]}'
            with self.assertRaises(SemanticUnavailable):
                provider.score(SearchParams(**BASE), service.catalog)

    def test_semantic_cannot_override_hard_checks_and_score_is_explainable(self) -> None:
        records = catalog(profile('free'), profile('busy', busy_dates=['2026-11-18']),
                          profile('expensive', price=2000000))
        provider = HttpSemanticProvider('http://localhost:8100')
        scores = {'model': 'tfidf-v1', 'scores': [
            {'id': p.id, 'semantic': 1.0, 'lexical': 1.0} for p in records.profiles]}
        with patch('backend.app.semantic.urlopen') as opener:
            opener.return_value.__enter__.return_value.read.return_value = json.dumps(scores).encode()
            result = MatchingService(records, provider).match(SearchParams(**BASE))
        self.assertEqual([p.id for p in result.results], ['free'])
        card = result.results[0]
        self.assertEqual(card.semantic_score, card.evidence.semantic.score)
        self.assertEqual(card.semantic_score, card.score_breakdown.semantic)
        self.assertAlmostEqual(sum(v for v in card.score_weights.model_dump().values() if v is not None), 1)
        calculated = sum((value or 0) * (getattr(card.score_weights, key) or 0)
                         for key, value in card.score_breakdown.model_dump().items())
        self.assertAlmostEqual(calculated, card.score, places=6)
        self.assertEqual(result.model_info.semantic_model, 'tfidf-v1')

    def test_metadata_catalog_outage_and_internal_error(self) -> None:
        with TestClient(create_app(catalog(profile('1')))) as client:
            metadata = client.get('/api/meta/options').json()
            self.assertEqual(metadata['categories'], ['Ведущий'])
            self.assertEqual(metadata['max_budget'], MAX_BUDGET)
            cors = client.options('/api/match', headers={'Origin': 'http://localhost:5173', 'Access-Control-Request-Method': 'POST'})
            self.assertEqual(cors.headers['access-control-allow-origin'], 'http://localhost:5173')
        with patch.dict(os.environ, {'DATASET_PATH': '/does-not-exist'}):
            with TestClient(create_app()) as client:
                for path in ('/api/meta/options', '/api/health'):
                    response = client.get(path)
                    self.assertEqual(response.status_code, 503)
                    self.assertEqual(response.json()['code'], 'catalog_unavailable')
                self.assertEqual(client.post('/api/match', json=BASE).status_code, 503)
        with TestClient(create_app(catalog(profile('1'))), raise_server_exceptions=False) as client:
            with patch('backend.app.main.MatchingService.match', side_effect=RuntimeError('secret-test-value')):
                response = client.post('/api/match', json=BASE)
                self.assertEqual(response.status_code, 500)
                self.assertNotIn('secret-test-value', response.text)

    def test_real_dataset_and_frontend_fixtures_same_contract(self) -> None:
        snapshot = load_catalog(DEFAULT_DATASET)
        self.assertEqual(len(snapshot.profiles), 66)
        self.assertEqual(sum(p.synthetic for p in snapshot.profiles), 13)
        service = MatchingService(snapshot)
        bundle = json.loads((ROOT / 'frontend/src/mocks/fixtures.json').read_text())
        self.assertEqual(bundle['metadata'], snapshot.metadata().model_dump(mode='json'))
        statuses = set()
        for fixture in bundle['fixtures']:
            expected = MatchResponse.model_validate(fixture['response'])
            actual = service.match(SearchParams.model_validate(fixture['request']))
            self.assertEqual(actual, expected)
            statuses.add(actual.status)
        self.assertEqual(statuses, {'matched', 'no_match', 'category_not_found'})
        self.assertEqual((ROOT / 'frontend/src/shared/types/match.ts').read_text(), contract())
        with TestClient(create_app(snapshot)) as client:
            schema = client.get('/openapi.json').json()
            self.assertIn('/api/match', schema['paths'])
            self.assertEqual(schema['components']['schemas']['MatchResponse']['properties']['status']['enum'],
                             ['matched', 'category_not_found', 'no_match'])

    def test_corrupt_catalog_is_not_replaced_by_mock(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'bad.csv'
            path.write_text('id,name\nx,test\n')
            with self.assertRaises(CatalogError):
                load_catalog(path)


if __name__ == '__main__':
    unittest.main()
