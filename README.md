# HackAlemAI

Full-stack project with React, Vite, Chakra UI, TanStack Query, FastAPI, and Docker.

## Architecture

- `src/` - frontend application.
- `backend/` - FastAPI backend.
- `Dockerfile` - production frontend image.
- `backend/Dockerfile` - backend image.
- `docker-compose.yml` - starts frontend and backend together.

## Development

```bash
npm install
npm run dev
```

Run backend locally:

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Docker

```bash
docker compose up --build
```

Frontend: `http://localhost:3000`

Backend health: `http://localhost:8000/api/health`
