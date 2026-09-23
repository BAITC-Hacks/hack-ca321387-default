"""The optional HTTP server is testable without downloading model weights."""
import unittest

from fastapi.testclient import TestClient

from app.local_explainer import create_app


class FakeGenerator:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def generate(self, facts: list[str]) -> str:
        self.calls.append(facts)
        return 'Подходит: ' + '; '.join(facts)


class LocalExplainerTests(unittest.TestCase):
    def test_chat_uses_supplied_turns(self) -> None:
        class ChatGenerator(FakeGenerator):
            def generate_chat(self, messages: list[dict[str, str]], context: dict[str, str]) -> str:
                return f"Ответ для {context.get('city', '')}: {messages[-1]['content']}"

        with TestClient(create_app(ChatGenerator())) as client:
            response = client.post('/chat', json={
                'messages': [{'role': 'user', 'content': 'Помоги'}],
                'context': {'city': 'Алматы'},
            })
            invalid = client.post('/chat', json={'messages': [{'role': 'assistant', 'content': 'Привет'}]})
        self.assertEqual(response.status_code, 200)
        self.assertIn('Алматы', response.json()['answer'])
        self.assertEqual(invalid.status_code, 422)

    def test_explain_preserves_ids_and_only_uses_supplied_facts(self) -> None:
        generator = FakeGenerator()
        with TestClient(create_app(generator)) as client:
            self.assertEqual(client.get('/health').status_code, 200)
            response = client.post('/explain', json={'candidates': [
                {'id': 'one', 'facts': ['Работает в Алматы', 'Цена в бюджете']},
                {'id': 'two', 'facts': ['Свободен на дату']},
            ]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(generator.calls, [['Работает в Алматы', 'Цена в бюджете'], ['Свободен на дату']])
        self.assertEqual([item['id'] for item in response.json()['items']], ['one', 'two'])

    def test_rejects_duplicate_ids_and_too_many_candidates(self) -> None:
        item = {'id': 'one', 'facts': ['Проверенный факт']}
        with TestClient(create_app(FakeGenerator())) as client:
            self.assertEqual(client.post('/explain', json={'candidates': [item, item]}).status_code, 422)
            self.assertEqual(client.post('/explain', json={'candidates': [item] * 4}).status_code, 422)


if __name__ == '__main__':
    unittest.main()
