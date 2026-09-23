"""Real loopback HTTP test of both processes and the supplied CSV, no matcher stubs."""
import json
import os
import socket
import subprocess
import sys
import time
from contextlib import ExitStack
from pathlib import Path

import httpx

from backend.app.catalog import DEFAULT_DATASET, load_catalog
from backend.app.schemas import MatchResponse, SearchParams
from backend.app.matching import MatchingService
from backend.tests.test_matching import BASE

ROOT = Path(__file__).resolve().parents[2]


def port() -> int:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def start(stack: ExitStack, directory: Path, app: str, number: int, env: dict[str, str]) -> subprocess.Popen:
    process = subprocess.Popen([sys.executable, '-m', 'uvicorn', app, '--host', '127.0.0.1', '--port', str(number)],
                               cwd=directory, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    def stop() -> None:
        if process.poll() is None:
            process.terminate()
        process.communicate(timeout=5)
    stack.callback(stop)
    with httpx.Client(timeout=1) as client:
        for _ in range(100):
            if process.poll() is not None:
                raise RuntimeError(process.communicate()[1].decode())
            try:
                if client.get(f'http://127.0.0.1:{number}/openapi.json').status_code == 200:
                    return process
            except httpx.TransportError:
                time.sleep(.05)
    raise RuntimeError('Server startup timeout')


def main() -> None:
    with ExitStack() as stack:
        ai_port, api_port = port(), port()
        env = {**os.environ, 'AI_SERVICE_URL': f'http://127.0.0.1:{ai_port}', 'SEMANTIC_MODE': 'tfidf', 'AI_TIMEOUT_SECONDS': '.3',
               'ENABLE_MATCH_TRACE': 'true', 'PYTHONDONTWRITEBYTECODE': '1'}
        ai = start(stack, ROOT / 'services/ai', 'app.main:app', ai_port, env)
        start(stack, ROOT, 'backend.app.main:app', api_port, env)
        with httpx.Client(base_url=f'http://127.0.0.1:{api_port}', timeout=5) as client:
            begin = time.perf_counter()
            response = client.post('/api/match', json=BASE)
            response.raise_for_status()
            result = MatchResponse.model_validate(response.json())
            assert result.status == 'matched' and len(result.results) == 3 and result.total_eligible == 4
            assert result.model_info.semantic_model == 'tfidf-v1'
            assert all(p.semantic_score is not None for p in result.results)
            assert result == MatchResponse.model_validate(client.post('/api/match', json=BASE).json())
            for day in result.availability:
                repeated = client.post('/api/match', json={**BASE, 'date': day.date.isoformat()}).json()
                assert repeated['total_eligible'] == day.available
            for query, expected in [({**BASE, 'budget': 100}, 'no_match'), ({**BASE, 'city': 'Зарубежье'}, 'category_not_found')]:
                answer = client.post('/api/match', json=query)
                assert answer.status_code == 200 and answer.json()['status'] == expected
            details = client.post('/api/match/details', json=BASE)
            details.raise_for_status()
            assert details.json()['match'] == response.json()
            for ranking in details.json()['ranking']:
                total = sum(component['contribution'] for component in ranking['components']
                            if component['contribution'] is not None)
                assert round(total, 6) == ranking['score']
            window = client.post('/api/availability', json={'query': BASE, 'days_before': 3, 'days_after': 3})
            window.raise_for_status()
            assert len(window.json()['days']) == 7
            for day in window.json()['days']:
                assert client.post('/api/match', json={**BASE, 'date': day['date']}).json()['total_eligible'] == day['available']
            presets = client.get('/api/demo-presets')
            presets.raise_for_status()
            assert len(presets.json()['presets']) == 4  # Verified supplied snapshot.
            for preset in presets.json()['presets']:
                actual = client.post('/api/match', json=preset['query'])
                actual.raise_for_status()
                assert actual.json()['total_eligible'] == preset['eligible_count']
                assert actual.json()['status'] == preset['expected_status']
            trace = client.post('/api/debug/match', json=BASE)
            trace.raise_for_status()
            assert trace.json()['details'] == details.json()
            assert trace.json()['trace']['total_eligible'] == result.total_eligible
            assert trace.json()['trace']['total_ms'] >= 0
            ai.terminate()
            ai.wait(timeout=5)
            degraded = MatchResponse.model_validate(client.post('/api/match', json=BASE).json())
            assert degraded.model_info.semantic_model == 'unavailable'
            assert degraded.model_info.fallback_used
            assert all(p.semantic_score is None for p in degraded.results)
            assert degraded.total_eligible == result.total_eligible
            fallback_trace = client.post('/api/debug/match', json=BASE).json()
            assert fallback_trace['details']['match'] == degraded.model_dump(mode='json')
            assert 'semantic_unreachable' in [notice['code'] for notice in fallback_trace['trace']['notices']]
            baseline = MatchingService(load_catalog(DEFAULT_DATASET)).match(SearchParams(**BASE))
            assert degraded.results == baseline.results
            print(json.dumps({'http_smoke': 'passed', 'feature_routes': 'passed', 'trace_fallback': 'passed', 'eligible': result.total_eligible,
                              'ranked_ids': [p.id for p in result.results], 'including_startup_excluded_seconds': round(time.perf_counter()-begin, 3)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
