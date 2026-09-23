from fastapi import FastAPI

app = FastAPI(title="HackAlemAI AI Service", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "HackAlemAI AI Service"}


@app.post("/predict")
def predict() -> dict[str, str]:
    return {
        "status": "not_configured",
        "message": "Connect the neural-network model here.",
    }
