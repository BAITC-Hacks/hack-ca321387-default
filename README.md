# EventLens

Explainable selection of event contractors in Kazakhstan. The React frontend
uses the real FastAPI API by default. The backend loads the 66 supplied profiles,
checks all hard constraints, ranks eligible profiles and returns at most three
cards with evidence, diagnostic counts and nearby-date alternatives.

See [architecture and API contract](docs/ARCHITECTURE.md) for rules, score weights,
unknown-data policy, schema fields and degradation modes.

## Development

From the repository root (Python 3.12+ and a Node version supported by Vite 8):

```bash
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements-dev.txt
npm --prefix frontend ci
```

Start these in three terminals, from the repository root:

```bash
# Backend, real CSV, API and OpenAPI
backend/.venv/bin/python -m uvicorn backend.app.main:app --reload --port 8000

# Existing AI service: deterministic text similarity, no API keys
backend/.venv/bin/python -m uvicorn app.main:app --app-dir services/ai --port 8100

# Frontend; /api is proxied to localhost:8000
npm --prefix frontend run dev
```

Frontend: http://localhost:5173. API reference: http://localhost:8000/docs.
The backend also works while AI is unavailable, with explicit null text scores
and a disclosed budget/duration ranking mode.

Server env (see `.env.example`): optional `DATASET_PATH`, `AI_SERVICE_URL`
(default `http://localhost:8100`), `AI_TIMEOUT_SECONDS` (default 2),
`SEMANTIC_MODE=tfidf|disabled`, `CORS_ORIGINS` (comma-separated).
Uvicorn can read the root file explicitly with `--env-file .env`.
No server environment file or secrets are imported into the frontend.

To have OpenAI write the card's "Почему этот подрядчик подходит" text, copy
`.env.example` to an ignored root `.env` and set `OPENAI_API_KEY` there. Docker
Compose passes it only to the backend. For local Uvicorn, add `--env-file .env`.
`OPENAI_MODEL` defaults to `gpt-4.1-mini`; `OPENAI_TIMEOUT_SECONDS` defaults to 8.
The backend sends only verified evidence for the already-ranked TOP-3 in one
Responses API request. If the key is absent or the request fails, it keeps the
existing evidence-based text. Ranking, scores and candidate eligibility never
depend on OpenAI. API access requires a separate OpenAI Platform key; a ChatGPT
subscription alone does not configure the backend.

For a local, keyless explanation model, set `EXPLANATION_MODE=local` in the root
`.env` and start `docker compose --profile local-llm up --build`. This starts a
separate Hugging Face Qwen2.5-0.5B-Instruct service on port 8200. The optional
image installs CPU-only PyTorch and downloads model weights on first startup;
the named volume keeps the download for later runs. Wait until
`http://localhost:8200/health` responds before searching. Local generation on
CPU may be slower and less reliable than OpenAI. If it fails, the backend tries
OpenAI when a key is configured, then the deterministic text. To use only
OpenAI, set `EXPLANATION_MODE=openai`; `template` disables model wording.
Ordinary `docker compose up --build` does not build or start the local model.

The assistant chat uses `POST /api/chat`: OpenAI is tried first when
`OPENAI_API_KEY` is configured, then the optional local Qwen service. Chat does
not change deterministic matching and does not receive contractor results; it
only knows the selected search fields and the current conversation. Without a
working provider it reports a service error instead of a canned response.
Run `docker compose --profile local-llm up --build` to enable the local fallback.

Frontend env (`frontend/.env.example`): `VITE_API_URL=/api`,
`VITE_USE_MOCK_API=false`. Production refuses mock mode. Optional dev mock mode
uses a finite set of recorded backend responses, documented in the architecture;
it never silently replaces an API failure.

## Docker

```bash
docker compose up --build
```

Frontend: http://localhost:3000; backend health: http://localhost:8000/api/health;
AI health: http://localhost:8100/health. Backend image includes the CSV from the
root build context. It starts independently of AI health and supports degradation.
The Compose frontend calls the real backend; it does not enable fixtures.

## Tests and contract regeneration

```bash
backend/.venv/bin/python -m unittest discover -s backend/tests -v
backend/.venv/bin/python -m mypy --strict backend/app
# Run AI tests with its own app import root
(cd services/ai && ../../backend/.venv/bin/python -m unittest discover -s tests -v)
backend/.venv/bin/python -m backend.scripts.http_smoke
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run build

# After deliberately changing backend schemas/data/algorithm:
backend/.venv/bin/python -m backend.scripts.export_contract
backend/.venv/bin/python -m backend.scripts.export_fixtures
```

Tested runtime: Python 3.13.0, FastAPI 0.124.4, Pydantic 2.13.5,
Uvicorn 0.38.0; Node 25.4.0, React 19.3.0, Vite 8.3.0,
TypeScript 6.0.3, Chakra UI 3.37.0, TanStack Query 5.103.2.
Existing runtime dependency ranges/lockfile were preserved; test dependencies
are in `backend/requirements-dev.txt`.

## Demo requests

```bash
curl http://localhost:8000/api/meta/options
curl -X POST http://localhost:8000/api/match \
  -H 'Content-Type: application/json' \
  -d '{"city":"Алматы","date":"2026-11-18","event_type":"корпоратив","category":"Ведущий","budget":1000000,"language":"русский","duration":6}'
```

For the supplied CSV and TF-IDF mode, this request has four eligible profiles;
the displayed IDs are `HK-44923`, `HK-27222`, `HK-77838`. Set budget to 100 for
`no_match` and a verified budget suggestion; set city to `Зарубежье` for
`category_not_found`. Unknown dictionary values instead return HTTP 422.

Verification in this workspace: backend/API tests, AI tests, strict backend
types, frontend contract/component tests, lint, build and real HTTP smoke passed.
Docker execution could not be checked because the CLI is absent. Browser control
is unavailable due to system permissions, so live form clicks, expanded details,
layout and browser Retry still require a manual pass. Static component rendering
and API retry tests cover those states without claiming browser E2E.

## Branch synchronization

After each push to `main`, `.github/workflows/sync-main.yml` merges the latest
`main` into both `arys` and `damir`, then pushes each branch separately.
The workflow preserves branch-specific commits and never force-pushes. If a
merge conflicts or a branch rule rejects the bot push, that branch's job fails
without replacing its content; resolve the conflict or branch permission in
GitHub and rerun the workflow manually.
