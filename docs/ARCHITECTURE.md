# Architecture

EventLens follows a facts-first matching flow: the backend owns the catalog
and hard eligibility constraints; the AI service scores only eligible
candidates, returns evidence for every score, and explains empty results from
the backend's filter counts. Language-model output never changes eligibility
or ranking.

```text
HackAlemAI
├── frontend/      React, Vite, Chakra UI, TanStack Query
├── backend/       FastAPI application API
├── services/
│   └── ai/        deterministic ranking, evidence and diagnostics API
├── docs/          Project documentation
└── docker-compose.yml
```

## Request Flow

1. The browser opens the frontend on port `3000`.
2. Nginx proxies `/api/*` requests from the frontend container to the backend.
3. The backend filters by category, city, date, event format, budget, language
   and duration, then sends only eligible profiles to `POST /rank`.
4. The AI service calculates TF-IDF similarity and deterministic fit scores,
   orders ties by price and profile ID, and returns up to three candidates with
   an Evidence Ledger and grounded explanation.
5. When no candidates remain, the backend sends its filter funnel to
   `POST /constraints/diagnose`. `POST /what-if` compares date counts already
   computed by the backend.
6. The AI service stays isolated so a future embedding model does not slow down
   or destabilize backend hard constraints. The current dependency-free
   TF-IDF implementation remains the fallback.

## AI service modules

```text
services/ai/app/
├── constraint_doctor/  no-result diagnostics from funnel counts
├── explanations/       evidence-only deterministic text templates
├── ranking/            TF-IDF similarity, weights and stable scoring
├── schemas/            validated request/response contracts
└── main.py              FastAPI endpoints: /rank, /constraints/diagnose, /what-if
```

The AI contract accepts both the compact candidate shape (`price`, `formats`,
`name`) and dataset field names (`price_from_kzt`, `event_formats`,
`anon_name`). See `services/ai/README.md` for request examples and scoring
details.
