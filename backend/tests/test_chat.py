import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.chat import ChatRequest, ChatService
from backend.app.main import create_app


class ChatTests(unittest.TestCase):
    def setUp(self) -> None:
        self.query = {'message': 'Помоги с корпоративом', 'context': {'city': 'Алматы'}}

    def test_openai_has_priority(self) -> None:
        service = ChatService('test-key', 'gpt-4.1-mini', 2, 'http://localhost:8200', 2)
        with patch.object(service, '_post', return_value={
            'status': 'completed', 'output': [{'type': 'message', 'content': [
                {'type': 'output_text', 'text': 'Ответ OpenAI'}]}]}) as post:
            result = service.reply(ChatRequest(**self.query))
        self.assertEqual(result.provider, 'openai')
        self.assertEqual(post.call_count, 1)
        self.assertIn('api.openai.com', post.call_args.args[0])

    def test_local_fallback(self) -> None:
        service = ChatService('test-key', 'gpt-4.1-mini', 2, 'http://localhost:8200', 2)
        with patch.object(service, '_post', side_effect=[ValueError('fail'), {'answer': 'Локальный ответ'}]) as post:
            result = service.reply(ChatRequest(**self.query))
        self.assertEqual(result.provider, 'local')
        self.assertEqual(post.call_count, 2)

    def test_route_and_validation(self) -> None:
        with TestClient(create_app()) as client, patch.object(ChatService, '_post', return_value={'answer': 'Ответ'}):
            response = client.post('/api/chat', json=self.query)
            invalid = client.post('/api/chat', json={'message': ''})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['provider'], 'local')
        self.assertEqual(invalid.status_code, 422)

    def test_unavailable_is_not_mocked(self) -> None:
        with TestClient(create_app()) as client, patch.object(ChatService, '_post', side_effect=ValueError('offline')):
            response = client.post('/api/chat', json=self.query)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['code'], 'chat_unavailable')


if __name__ == '__main__':
    unittest.main()
