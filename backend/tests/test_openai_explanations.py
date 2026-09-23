"""OpenAI explanations are optional and cannot affect matching decisions."""
import io
import json
import unittest
from unittest.mock import patch
from urllib.error import URLError

from fastapi.testclient import TestClient

from backend.app.catalog import Catalog, Profile
from backend.app.explanations import FallbackExplanationProvider, LocalExplanationProvider, OpenAIExplanationProvider
from backend.app.main import create_app
from backend.app.matching import MatchingService
from backend.app.schemas import SearchParams

QUERY = SearchParams(city='Алматы', date='2026-11-18', event_type='корпоратив',
                     category='Ведущий', budget=1_000_000, language='русский', duration=6)


def profile(identifier: str, price: int = 500_000) -> Profile:
    return Profile.model_validate({
        'id': identifier, 'name': f'Ведущий {identifier}', 'city': 'Алматы',
        'categories': ['Ведущий'], 'price': price, 'formats': ['корпоратив'],
        'languages': ['русский'], 'max_hours': 8, 'duration_policy': 'limited',
        'busy_dates': [], 'description': 'Ведущий корпоративов',
    })


def catalog(*records: Profile) -> Catalog:
    return Catalog(tuple(records), 'test-openai')


class FakeProvider:
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.seen: list[str] = []

    def explain(self, cards):
        self.seen = [card.id for card in cards]
        if self.fail:
            raise RuntimeError('network failed')
        return {card.id: f'ИИ объяснение для {card.id}' for card in cards}


class OpenAIExplanationTests(unittest.TestCase):
    def test_local_provider_and_openai_fallback(self) -> None:
        cards = MatchingService(catalog(profile('one'), profile('two'))).match(QUERY).results
        local = LocalExplanationProvider('http://localhost:8200')

        def respond(request, timeout):
            self.assertEqual(request.full_url, 'http://localhost:8200/explain')
            self.assertEqual(timeout, 30)
            payload = json.loads(request.data)
            self.assertEqual({item['id'] for item in payload['candidates']}, {'one', 'two'})
            return io.BytesIO(json.dumps({'items': [
                {'id': 'one', 'explanation': 'Локальный текст'},
                {'id': 'two', 'explanation': ''},
            ]}).encode())

        with patch('backend.app.explanations.urlopen', side_effect=respond):
            writer = FallbackExplanationProvider(local, FakeProvider())
            result = writer.explain(cards)
        self.assertEqual(result, {'one': 'Локальный текст', 'two': 'ИИ объяснение для two'})

        with patch('backend.app.explanations.urlopen', side_effect=URLError('offline')):
            result = FallbackExplanationProvider(local, FakeProvider()).explain(cards)
        self.assertEqual(set(result), {'one', 'two'})

    def test_local_mode_is_configured_through_http(self) -> None:
        with patch.dict('os.environ', {'EXPLANATION_MODE': 'local', 'OPENAI_API_KEY': '',
                                        'SEMANTIC_MODE': 'disabled'}), \
                patch.object(LocalExplanationProvider, 'explain', return_value={'one': 'Локальная модель: проверенные факты.'}) as explain:
            with TestClient(create_app(catalog(profile('one')))) as client:
                response = client.post('/api/match', json=QUERY.model_dump(mode='json'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['results'][0]['explanation'], 'Локальная модель: проверенные факты.')
        explain.assert_called_once()

    def test_http_match_uses_configured_writer_without_changing_result(self) -> None:
        records = catalog(profile('one'))
        baseline = MatchingService(records).match(QUERY)
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key', 'SEMANTIC_MODE': 'disabled'}), \
                patch.object(OpenAIExplanationProvider, 'explain', return_value={'one': 'Подходит по подтверждённым условиям.'}) as explain:
            with TestClient(create_app(records)) as client:
                response = client.post('/api/match', json=QUERY.model_dump(mode='json'))
        self.assertEqual(response.status_code, 200)
        card = response.json()['results'][0]
        self.assertEqual(card['explanation'], 'Подходит по подтверждённым условиям.')
        self.assertEqual(card['score'], baseline.results[0].score)
        self.assertEqual(card['evidence'], baseline.results[0].evidence.model_dump())
        explain.assert_called_once()

    def test_only_top_three_are_reworded_after_ranking(self) -> None:
        records = catalog(*(profile(str(i), 400_000 + i * 10_000) for i in range(5)))
        baseline = MatchingService(records).match(QUERY)
        writer = FakeProvider()
        result = MatchingService(records, explanations=writer).match(QUERY)
        self.assertEqual(writer.seen, [card.id for card in baseline.results])
        self.assertEqual([card.id for card in result.results], [card.id for card in baseline.results])
        self.assertEqual([card.score for card in result.results], [card.score for card in baseline.results])
        self.assertEqual(result.total_eligible, baseline.total_eligible)
        self.assertEqual(result.results[0].explanation, f'ИИ объяснение для {result.results[0].id}')

    def test_provider_failure_and_empty_results_keep_fallback(self) -> None:
        records = catalog(profile('one'))
        baseline = MatchingService(records).match(QUERY)
        writer = FakeProvider(fail=True)
        result = MatchingService(records, explanations=writer).match(QUERY)
        self.assertEqual(result.results[0].explanation, baseline.results[0].explanation)
        empty_writer = FakeProvider()
        empty = MatchingService(catalog(profile('busy', 2_000_000)), explanations=empty_writer).match(QUERY)
        self.assertEqual(empty.results, [])
        self.assertEqual(empty_writer.seen, [])

    def test_response_request_uses_only_evidence_and_validates_ids(self) -> None:
        cards = MatchingService(catalog(profile('one'))).match(QUERY).results
        provider = OpenAIExplanationProvider('test-key')
        captured = {}

        def respond(request, timeout):
            captured['url'] = request.full_url
            captured['timeout'] = timeout
            captured['payload'] = json.loads(request.data)
            return io.BytesIO(json.dumps({
                'status': 'completed', 'output': [{'type': 'message', 'content': [
                    {'type': 'output_text', 'text': json.dumps({'items': [
                        {'id': 'one', 'explanation': 'Подходит по формату и бюджету.'},
                    ]})},
                ]}],
            }).encode())

        with patch('backend.app.explanations.urlopen', side_effect=respond):
            result = provider.explain(cards)
        self.assertEqual(result, {'one': 'Подходит по формату и бюджету.'})
        self.assertEqual(captured['url'], 'https://api.openai.com/v1/responses')
        self.assertEqual(captured['timeout'], 8)
        self.assertFalse(captured['payload']['store'])
        self.assertEqual(captured['payload']['model'], 'gpt-4.1-mini')
        prompt = json.loads(captured['payload']['input'])
        self.assertEqual(prompt['candidates'][0]['id'], 'one')
        self.assertTrue(any('бюджет' in reason for reason in prompt['candidates'][0]['facts']))
        self.assertNotIn('description', captured['payload']['input'])

        with patch('backend.app.explanations.urlopen', side_effect=URLError('offline')):
            self.assertEqual(provider.explain(cards), {})
        with patch('backend.app.explanations.urlopen', return_value=io.BytesIO(json.dumps({
            'status': 'completed', 'output': [{'type': 'message', 'content': [
                {'type': 'output_text', 'text': json.dumps({'items': [
                    {'id': 'unknown', 'explanation': 'Непроверенный кандидат'},
                ]})},
            ]}],
        }).encode())):
            self.assertEqual(provider.explain(cards), {})


if __name__ == '__main__':
    unittest.main()
