# EventLens AI service

The service ranks candidates that the backend has already selected for a
request. The backend remains the source of truth for category, city and date
constraints. The AI service defensively rechecks format, budget, language and
duration before scoring, so invalid candidates are never returned.

## Ranking pipeline

```text
backend eligible candidates
        -> deterministic TF-IDF cosine fallback
        -> budget / duration fit
        -> weighted score
        -> stable sort: score DESC, price ASC, id ASC
        -> Evidence Ledger and grounded explanation
```

The current scoring weights follow `app/ranking/weights.py`:

- duration applies: semantic 0.50, lexical 0.20, budget 0.20, duration 0.10;
- duration absent or not applicable: semantic 0.60, lexical 0.20, budget 0.20.

TF-IDF is deliberately dependency-free. Here `semantic_score` means the
baseline text similarity; it is not represented as an embedding model result.
An embedding encoder can later replace that one scoring signal behind the same
`[0, 1]` interface without changing hard filters, evidence or tie-breaking.

## HTTP API

### `POST /rank`

```json
{
  "query": {
    "city": "Алматы",
    "date": "2026-11-15",
    "event_type": "corporate",
    "category": "Ведущий",
    "budget": 800000,
    "language": "русский",
    "duration": 6,
    "preferences": "современный ведущий, юмор и импровизация"
  },
  "candidates": [
    {
      "id": "HK-123",
      "description": "Ведущий корпоративов, импровизация и юмор",
      "price": 700000,
      "languages": ["русский"],
      "formats": ["корпоратив"],
      "max_hours": 6
    }
  ]
}
```

The API also accepts the dataset names `anon_name`, `price_from_kzt`, and
`event_formats`. The response includes `outcome`, at most three ranked
candidates, score components, evidence reasons, deterministic explanations,
and `model_info`. Input candidates are expected to be date-available and to
match the requested city/category; those fields are absent from the compact
AI candidate contract.

### `POST /constraints/diagnose`

Accepts backend filter-funnel `counts`, and optional `minimum_price` and
`requested_budget`. Returns an explicit outcome, the funnel and the first
blocking constraint with a user-facing explanation.

### `POST /what-if`

Accepts `selected_date` and backend-computed `date_counts`; returns sorted
alternatives (higher availability first, date as stable tie-break) and a short
comparison sentence.

## Running locally

From `services/ai`:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8100
```

OpenAPI is available at `http://localhost:8100/docs`.
