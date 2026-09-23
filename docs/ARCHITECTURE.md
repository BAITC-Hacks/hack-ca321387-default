# EventLens architecture and API

## Responsibility and request flow

```text
React form / TanStack Query
  -> frontend/src/api (HTTP + errors; preserves order, nulls and dates)
  -> POST /api/match
  -> backend/app/schemas.py       validation / OpenAPI
  -> backend/app/catalog.py       one validated, immutable CSV snapshot
  -> backend/app/rules.py         hard checks -> structured facts / filter funnel
  -> backend/app/matching.py      alternatives, score, top 3, grounded explanation
  -> backend/app/semantic.py      one bounded batch HTTP call
  -> services/ai POST /similarity cached deterministic TF-IDF + lexical signals
```

`backend/app/main.py` is the HTTP/configuration boundary. Normal `def` route
handlers run blocking work in FastAPI's thread pool; the event loop is not used
for the synchronous AI call. This follows [FastAPI's execution model](https://fastapi.tiangolo.com/async/).
No database, queue, external LLM or provider secret is required.

`rules.evaluate` implements each criterion once. The resulting structured checks
are used by the sequential funnel and copied directly into result evidence.
Alternative budgets/dates call the same filter function. The AI service does not
choose eligibility, modify evidence, determine final scores or order API results.
Its existing `/rank`, `/constraints/diagnose`, `/what-if` endpoints remain for
legacy consumers; the product pipeline does **not** use those older endpoints.

## Dataset rules (and their sources)

Source: `docs/hackathon dataset anonymized .csv` (66 profiles, 13 synthetic).
The original `HackAlem AI_ Хакатон-задача_ умный подбор подрядчиков.docx` explicitly
specifies price per event, the calendar window and the meaning of null hours.
The CSV contains 9 null-hour profiles: florists, decorators, gifts/souvenirs.

- `price_from_kzt` is the starting price **per event**, not an hourly rate. Budget
  comparison uses that starting price without multiplying hours. This is a
  recommendation against catalog prices, not a final commercial quote.
- `busy_dates` is the closed demo calendar for **2026-09-23 through 2026-12-31**.
  A date not in a known calendar is available within that window. A missing CSV
  calendar is unknown and fails the date check; it is never treated as empty.
  An explicitly known empty calendar in the typed data model means no busy days.
- Null `max_hours` is N/A only for the documented non-presence service categories
  (florist, decorator, gifts/souvenirs). Otherwise it is unknown, and a requested
  duration cannot be confirmed. N/A and unrequested conditions have
  `matched: null`; unknown requested conditions fail (`matched: false`).
- Missing price fails the budget check. Missing formats/languages cannot confirm
  a requested value. Missing required catalog columns, corrupt data, duplicate IDs
  or an unreadable/empty catalog make the API unavailable, with HTTP 503.
- City/category/format/language comparison folds case, ё/е and repeated whitespace.
  Query values are canonicalized against the actual catalog. There is no automatic
  city expansion or inference from description text.
- `synthetic`, `city_imputed`, `price_imputed` describe provenance, not quality.
  They do not affect score; reconstructed price/city are disclosed in evidence.

The snapshot loads once at startup; `data_version` is the first 16 hex characters
of SHA-256 of the CSV bytes. Restart the backend after changing data. There is no
silent fallback to browser fixtures or another catalog.

## API

OpenAPI: `/openapi.json`, interactive reference: `/docs`.

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | Readiness of the loaded catalog; 503 if unavailable |
| `GET /api/meta/options` | Actual cities, categories, event types, languages and form limits |
| `POST /api/match` | Matching, diagnostic funnel, validated alternatives |
| `GET /api/architecture` | Non-secret summary of service responsibilities |

Request (the five first fields are required):

```json
{"city":"Алматы","date":"2026-11-18","event_type":"корпоратив","category":"Ведущий","budget":1000000,"language":"русский","duration":6}
```

`date` must be an ISO calendar string `YYYY-MM-DD`, with no timestamps/timezone
conversion. Budget must be a finite JSON number in `(0, 100000000]`. The upper
bound preserves the existing form limit and exceeds the CSV maximum (6000000).
Duration is an integer from 1 to 12. Optional fields are canonically `null`;
omission is accepted, and empty/«Не важно» language input normalizes to null.
The browser sends null for both «Не важно» controls. String durations are invalid.
Unknown vocabulary values are **422**, not empty search results.

HTTP 200 business outcomes:

- `matched`: 1–3 `results`, with `total_eligible` before the top-3 limit.
- `category_not_found`: the category is known globally, but absent in this city.
- `no_match`: the category exists in the city, but later checks exclude everyone.

Response fields: `status`, `results`, `total_eligible`, `diagnostics`, `availability`,
`model_info`. Each card contains `id`, `name`, `categories`, `city`, `price`,
`price_basis: "event_from"`, `score`, `semantic_score`, provenance flags,
`evidence`, `explanation`, `score_breakdown`, `score_weights`, `languages`,
`max_hours`, `duration_policy` and `description`. The exact typed schema is in
`backend/app/schemas.py`; frontend types are generated from these models by
`python -m backend.scripts.export_contract` (no extra generator dependency).

Evidence has individual `category`, `city`, `date`, `budget`, `format`, `language`,
`duration`, `semantic` objects. Each has `matched: boolean | null`, `reason`,
`source_field`, stable `code`, `requested`, `actual`, and `score: number | null`.
Semantic similarity is a signal, so its `matched` is always null. It is never a
hard pass/fail. Explanations use those facts and an explicitly attributed excerpt
from `description` already contained in semantic evidence. No fact is extracted
back from explanation text.

Breakdown and weights both contain `semantic`, `lexical`, `budget`, `duration`.
Inactive values/weights are null. All non-null scores and weights are in `[0,1]`.
Scores represent fit, not the probability of a successful event. UI percentages
are presentation only; order comes directly from the backend.

Errors use `{code, message, detail: [{field, code, message}]}`: validation 422,
unknown route 404, catalog unavailable 503, unexpected internal error 500.
Errors never become business statuses; responses contain no stack traces.

## Hard-filter order and diagnostics

Fixed order: **category → city → date → format → budget → language → duration**.
Optional checks stay in the funnel even when not requested; their counts do not
change. A step contains `stage`, `label`, `before`, `after`, `excluded`, plus
`count` (the existing frontend alias for `after`). Each next `before` equals the
previous `after`; counts are not independent selections.

`diagnostics.primary_blocker` is the first step where a nonempty pool becomes
empty. The summary explicitly explains that this is order-dependent and relaxing
that one condition alone need not produce a result.

`diagnostics.budget_alternative` is null unless a recomputation with every other
condition unchanged finds a feasible higher budget within form bounds. It has
`{budget, available}`; the proposed threshold is the minimum price among those
candidates, followed by a second full verification at exactly that budget.

`availability` contains `{date, available}` for selected date ±2 days, clipped to
the documented range. Each count is the **full eligible count**, not the displayed
maximum of three. Selecting another date resubmits the last searched parameters,
even if the user has since edited the draft form.

## Deterministic ranking and degradation

Baseline version: `eventlens-v2`. The existing TF-IDF/lexical scoring formula is
preserved, with the full catalog as the stable text corpus (not a changing subset
of eligible candidates):

- TF-IDF cosine of `category + event_type` against descriptions; smoothed IDF
  `log((1 + corpus_size) / (1 + document_frequency)) + 1` and term frequency.
  Query is included in the corpus as in the original implementation.
- Lexical Jaccard overlap of case-folded whitespace tokens.
- Budget fit: `clamp(1 - price / budget, 0, 1)`.
- Duration fit when applicable: `clamp((max_hours - duration) / duration, 0, 1)`.
- With applicable duration: weights **0.50 / 0.20 / 0.20 / 0.10**.
- Without applicable duration: **0.60 / 0.20 / 0.20 / 0**.

Unavailable components are null; weights of the remaining components are
renormalized to sum to one. No text means no fabricated zero score. The final
weighted sum is rounded to 6 places, with order **score DESC, price ASC, ID ASC**.
Only eligible candidates enter ranking, and fewer than three are never padded.
`score_weights` makes per-candidate N/A renormalization explicit.

AI requests are batched once per matching request, with a configurable default
2-second socket timeout (maximum 10). The AI service memoizes at most 128
`(query, full corpus)` combinations; changed text changes the key. There is no
per-candidate network request, model load, DB query or result cache.

`model_info.semantic_model` is `tfidf-v1`, `unavailable`, `disabled`, or `not_used`
(no candidates). On timeout, invalid response, invalid scores/IDs or service
outage, text signals become null and only budget/applicable duration are used.
`fallback_used` is true for outages; intentional `SEMANTIC_MODE=disabled` is
reported separately. The mode is appended to `ranking_version`, so identical
request + data snapshot + algorithm/mode gives identical cards/scores/evidence.
Changes in dependency availability are explicitly changes in algorithm mode.
No embedding-model or LLM result is claimed by this baseline.

## Frontend integration and fixtures

The default is the real API. `VITE_API_URL` accepts `/api`, an origin such as
`http://localhost:8000`, or an origin ending in `/api`; normalization prevents
accidental `/api/api/match`. Vite proxies `/api` to port 8000; Nginx forwards that
same prefix. CORS permits localhost 3000/5173 unless overridden on the server.
The frontend contains no provider keys and uses a 12-second request timeout.
Missing metadata surfaces an error with Retry and disables submit; it does not
silently substitute a guessed dictionary.

`VITE_USE_MOCK_API=true` is dev-only and selects recorded backend fixtures.
There are no browser matching rules. Fixtures cover the default query, budget
100, the florist wedding scenario (Алматы, 2026-10-15, 300000, Russian, no duration),
the Astana florist scenario (2026-12-20, same conditions), and the default query in
Зарубежье, each with ±4 recorded dates. Other inputs give a clear fixture error.
Regenerate with `python -m backend.scripts.export_fixtures`. All fixtures validate
against Pydantic and generated TypeScript and are compared with the real matcher.
Production rejects mock=true and removes the dynamic fixture import entirely.

## Verification

See root README for commands. Unit/API tests use the actual MatchingService.
The HTTP smoke script launches two Uvicorn processes against the real CSV,
checks semantic results, statuses, stable ranking, alternatives, then terminates
AI and checks degraded responses. Frontend tests type-check recorded responses,
exercise the API adapter/errors, render result/evidence/diagnostic/error states
and verify production mock rejection.

The current environment has no Docker CLI. Native browser control was denied by
system permissions; interactive clicks, expanded details, layout and browser
Retry remain manual checks. Static component rendering is not browser E2E.
