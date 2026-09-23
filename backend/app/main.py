from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(title="HackAlemAI API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "HackAlemAI API"}


@app.get("/api/architecture")
def architecture() -> dict[str, str]:
    return {
        "frontend": "React + Vite",
        "backend": "FastAPI",
        "ai_service": os.getenv("AI_SERVICE_URL", "http://localhost:8100"),
    }
