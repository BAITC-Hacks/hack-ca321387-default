import json
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.catalog import DEFAULT_DATASET, load_catalog
from backend.app.chat import ChatService
from backend.app.main import create_app
from backend.app.request_extraction import ExtractionService, validate_extraction


TEXT = 'Нужен ведущий на корпоратив в Алматы 15 ноября 2026, бюджет до 800 000 ₸, на 6 часов, на русском языке'
FIELDS = {
    'city': {'value': 'Алматы', 'quote': 'Алматы'},
    'date': {'value': '2026-11-15', 'quote': '15 ноября 2026'},
    'event_type': {'value': 'корпоратив', 'quote': 'корпоратив'},
    'category': {'value': 'Ведущий', 'quote': 'ведущий'},
    'budget': {'value': '800000', 'quote': 'бюджет до 800 000 ₸'},
    'language': {'value': 'русский', 'quote': 'русском языке'},
    'duration': {'value': '6', 'quote': '6 часов'},
}


class ExtractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_catalog(DEFAULT_DATASET)

    def test_all_fields_are_grounded(self) -> None:
        result = validate_extraction(TEXT, FIELDS, self.catalog, 'openai')
        self.assertEqual(result.missing, [])
        self.assertEqual(result.fields.date, '2026-11-15')
        self.assertEqual(result.fields.budget, 800000)
        self.assertEqual(result.fields.duration, 6)

    def test_invented_or_mismatched_values_are_dropped(self) -> None:
        fields = {**FIELDS,
                  'city': {'value': 'Астана', 'quote': 'Алматы'},
                  'date': {'value': '2026-11-16', 'quote': '15 ноября 2026'},
                  'budget': {'value': '900000', 'quote': 'бюджет до 800 000 ₸'},
                  'category': {'value': 'Ведущий церемонии', 'quote': 'ведущий'}}
        result = validate_extraction(TEXT, fields, self.catalog, 'openai')
        self.assertIsNone(result.fields.city)
        self.assertIsNone(result.fields.date)
        self.assertIsNone(result.fields.budget)
        self.assertIsNone(result.fields.category)
        self.assertEqual(set(result.missing), {'city', 'date', 'category', 'budget'})

    def test_missing_fields_stay_missing(self) -> None:
        result = validate_extraction('Нужен ведущий', {'category': {'value': 'Ведущий', 'quote': 'ведущий'}},
                                     self.catalog, 'local')
        self.assertEqual(result.fields.category, 'Ведущий')
        self.assertEqual(set(result.missing), {'city', 'date', 'event_type', 'budget'})

    def test_openai_priority_and_local_fallback(self) -> None:
        service = ExtractionService('test-key', 'gpt-4.1-mini', 2, 'http://localhost:8200', 2)
        openai = {'status': 'completed', 'output': [{'type': 'message', 'content': [
            {'type': 'output_text', 'text': json.dumps(FIELDS, ensure_ascii=False)}]}]}
        with patch.object(ChatService, '_post', return_value=openai) as post:
            result = service.extract(TEXT, self.catalog)
        self.assertEqual(result.provider, 'openai')
        self.assertEqual(post.call_count, 1)
        with patch.object(ChatService, '_post', side_effect=[ValueError('offline'),
                                                             {'answer': json.dumps(FIELDS, ensure_ascii=False)}]) as post:
            fallback = service.extract(TEXT, self.catalog)
        self.assertEqual(fallback.provider, 'local')
        self.assertEqual(post.call_count, 2)

    def test_route_validation_and_unavailable(self) -> None:
        with TestClient(create_app(self.catalog)) as client, patch.object(
            ChatService, '_post', return_value={'answer': json.dumps(FIELDS, ensure_ascii=False)}):
            response = client.post('/api/search/extract', json={'text': TEXT})
            invalid = client.post('/api/search/extract', json={'text': ''})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['fields']['budget'], 800000)
        self.assertEqual(invalid.status_code, 422)
        with TestClient(create_app(self.catalog)) as client, patch.object(ChatService, '_post', side_effect=ValueError):
            unavailable = client.post('/api/search/extract', json={'text': TEXT})
        self.assertEqual(unavailable.status_code, 503)


if __name__ == '__main__':
    unittest.main()
