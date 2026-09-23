# EventLens

Explainable selection of event contractors in Kazakhstan. The React frontend
shows up to three eligible profiles, evidence for each recommendation,
filter-funnel diagnostics, and nearby-date availability.

## Architecture

- `frontend/` - React, Vite, Chakra UI and TanStack Query UI and API adapters.
- `backend/` - FastAPI application API; `/api/match` is not implemented yet.
- `services/ai/` - deterministic ranking and evidence API, prepared for backend integration.
- `docs/` - architecture and project documentation.
- `docker-compose.yml` - runs all three services and explicitly enables the
  frontend's demo adapter, backed by the 66 profiles from the supplied CSV.

## Development

```bash
cd frontend
npm install
npm run dev
```

The development server uses the demo adapter by default. It reads the same
anonymized profiles supplied under `docs/`, including real busy dates and
synthetic-profile flags. Filters, results and adjacent-date counts are computed
from these local records. This is demonstration data, not a live backend.

To use the real API, set `VITE_USE_MOCK_API=false` in `frontend/.env` and restart
Vite. The frontend then calls `POST /api/match` and `GET /api/meta/options` via
`VITE_API_URL` (default `/api`). The metadata request falls back to the known
catalog options if that endpoint returns 404. Until `/api/match` is added to
the backend, real mode shows the error and retry state.

`frontend/.env.example` documents both variables. In production builds, mock
mode is off unless `VITE_USE_MOCK_API=true` is set explicitly; the Docker Compose
demo sets it as a build argument.

Run backend locally:

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Run AI service locally:

```bash
cd services/ai
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8100
```

## Docker

```bash
docker compose up --build
```

Frontend: `http://localhost:3000`

Backend health: `http://localhost:8000/api/health`

AI health: `http://localhost:8100/health`

## Branch synchronization

After each push to `main`, `.github/workflows/sync-main.yml` merges the latest
`main` into both `arys` and `damir`, then pushes each branch separately.
The workflow preserves branch-specific commits and never force-pushes. If a
merge conflicts or a branch rule rejects the bot push, that branch's job fails
without replacing its content; resolve the conflict or branch permission in
GitHub and rerun the workflow manually.
