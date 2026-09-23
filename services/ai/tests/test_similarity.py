import unittest
from fastapi.testclient import TestClient
from app.main import app
from app.ranking.semantic import cached_similarity


class SimilarityTests(unittest.TestCase):
    def test_batch_nulls_repeatability_cache_and_invalidation(self) -> None:
        cached_similarity.cache_clear()
        query = {'query': 'Ведущий корпоратив', 'documents': [
            {'id': 'a', 'text': 'Ведущий корпоратив'}, {'id': 'b', 'text': ''},
            {'id': 'c', 'text': 'флорист свадьба'}]}
        with TestClient(app) as client:
            first = client.post('/similarity', json=query)
            self.assertEqual(first.status_code, 200)
            body = first.json()
            self.assertAlmostEqual(body['scores'][0]['semantic'], 1)
            self.assertEqual(body['scores'][1], {'id': 'b', 'semantic': None, 'lexical': None})
            self.assertEqual(body['scores'][2]['semantic'], 0)
            self.assertEqual(body, client.post('/similarity', json=query).json())
            self.assertEqual(cached_similarity.cache_info().hits, 1)
            query['documents'][2]['text'] = 'Ведущий'
            self.assertNotEqual(body, client.post('/similarity', json=query).json())
            self.assertEqual(cached_similarity.cache_info().misses, 2)

    def test_legacy_rank_endpoint_remains_compatible(self) -> None:
        with TestClient(app) as client:
            response = client.post('/rank', json={
                'query': {'city': 'Алматы', 'date': '2026-11-18', 'event_type': 'корпоратив', 'category': 'Ведущий', 'budget': 1000000},
                'candidates': [{'id': 'a', 'price_from_kzt': 500000, 'event_formats': ['корпоратив'], 'anon_name': 'Имя'}]})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['candidates'][0]['name'], 'Имя')


if __name__ == '__main__':
    unittest.main()
