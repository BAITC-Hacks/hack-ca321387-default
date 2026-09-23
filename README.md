# HackAlemAI

Full-stack project with React, Vite, Chakra UI, TanStack Query, FastAPI, and Docker.

## Architecture

- `frontend/` - React frontend with Chakra UI and TanStack Query.
- `backend/` - FastAPI backend API.
- `services/ai/` - separate AI service for model inference and neural-network code.
- `docs/` - architecture and project documentation.
- `frontend/Dockerfile` - production frontend image.
- `backend/Dockerfile` - backend image.
- `services/ai/Dockerfile` - AI service image.
- `docker-compose.yml` - starts frontend, backend, and AI service together.

## Development

```bash
cd frontend
npm install
npm run dev
```

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
