# Architecture

```text
HackAlemAI
├── frontend/      React, Vite, Chakra UI, TanStack Query
├── backend/       FastAPI application API
├── services/
│   └── ai/        AI and neural-network inference service
├── docs/          Project documentation
└── docker-compose.yml
```

## Request Flow

1. The browser opens the frontend on port `3000`.
2. Nginx proxies `/api/*` requests from the frontend container to the backend.
3. The backend owns application API endpoints and calls the AI service when model inference is needed.
4. The AI service stays isolated so model dependencies do not slow down the backend image.
