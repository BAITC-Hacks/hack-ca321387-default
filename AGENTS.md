# AGENTS.md — HackAlemAI / EventLens

## 0. Purpose of this file

This file defines the default working rules for any AI coding agent operating in this repository.

Treat these instructions as repository-wide constraints.

Before modifying code:

1. Read this file completely.
2. Inspect the existing implementation before creating new abstractions.
3. Preserve the current architecture unless there is a clear technical reason to change it.
4. Prefer small, reviewable changes over large rewrites.
5. Keep the hackathon requirements as the primary source of truth.

If a nested directory contains its own `AGENTS.md`, that file may add more specific rules for that directory, but it must not contradict the core product constraints in this root file.

---

# 1. Project

Project name: **HackAlemAI / EventLens**

EventLens is an explainable contractor recommendation system for event services in Kazakhstan.

The user has already selected an event context and needs help choosing from the available contractor catalog.

The system must not expand the catalog arbitrarily. It must select from the provided contractor data.

Core product idea:

> Recommend up to 3 contractors and explain exactly why each contractor appears in the result.

The product is not only a ranking system. Its key value is explainability.

The system should also explain why no suitable contractor was found.

---

# 2. Repository architecture

The current project architecture is:

```text
HackAlemAI/
├── frontend/              # React + Vite + Chakra UI + TanStack Query
├── backend/               # FastAPI application API
├── services/
│   └── ai/                # AI / ML inference, ranking and semantic matching
├── docs/                  # Project documentation
├── docker-compose.yml
└── AGENTS.md
```

Expected request flow:

```text
Browser
  ↓
Frontend
  ↓
/api/*
  ↓
FastAPI Backend
  ↓
AI Service when model inference is required
```

The AI service stays isolated from the backend so ML/model dependencies do not unnecessarily increase or slow down the main backend image.

Do not merge the AI service into the frontend.

Do not move application API ownership into the AI service.

---

# 3. Existing stack

## Frontend

Use the existing frontend stack:

- React
- TypeScript where already configured
- Vite
- Chakra UI
- TanStack Query

Do not migrate the project to Next.js.

Do not replace Chakra UI with another UI framework.

Do not replace TanStack Query unless the current implementation is fundamentally broken.

Do not introduce Redux, Zustand or another global state library unless there is a concrete need that cannot reasonably be solved with local state + TanStack Query.

## Backend

Use:

- Python
- FastAPI
- Pydantic
- existing project conventions

The backend owns application API endpoints and hard business constraints.

## AI / ML

The AI service is responsible for:

- semantic similarity;
- embeddings;
- deterministic ranking contributions;
- score calculation where appropriate;
- evidence generation;
- optional reranking;
- optional natural-language explanation generation;
- Constraint Doctor analysis if implemented there.

LLMs must never become the source of truth for eligibility or final deterministic ordering.

---

# 4. Source data

The hackathon dataset contains 66 contractor profiles.

Important contractor fields include:

```text
id
anon_name
categories
city
price_from_kzt
event_formats
languages
max_hours
busy_dates
description
synthetic
city_imputed
price_imputed
```

Important meanings:

- `categories`: contractor categories.
- `city`: Алматы / Астана / Зарубежье.
- `price_from_kzt`: starting event price in KZT.
- `event_formats`: supported formats such as wedding, toi, corporate, conference, anniversary, birthday.
- `languages`: supported working languages.
- `max_hours`: maximum hours on site; may be null when the service is not tied to on-site duration.
- `busy_dates`: unavailable dates.
- `description`: free-form Russian description.
- `synthetic`: indicates a fully synthetic profile.
- `city_imputed`, `price_imputed`: values filled during dataset preparation.

Synthetic profiles are allowed by the hackathon rules, but they must remain visibly identifiable in demos and UI.

Do not silently remove the `synthetic` flag.

Do not present synthetic profiles as if they were original real profiles.

---

# 5. Product input

The mandatory user input is:

- city;
- event date;
- event type / format;
- contractor category;
- budget in KZT.

Optional input:

- duration in hours;
- language.

A typical request shape may look like:

```json
{
  "city": "Алматы",
  "date": "2026-11-15",
  "event_type": "корпоратив",
  "category": "Ведущий",
  "budget": 800000,
  "duration": 6,
  "language": "русский"
}
```

Do not invent additional required fields unless the current API explicitly requires them.

---

# 6. Required output

The system returns **up to 3 contractor cards**.

Each result should expose at least:

- contractor identity/name;
- category;
- city;
- price;
- explanation of why the contractor is in the result.

The explanation must refer to concrete facts such as:

- budget fit;
- event format fit;
- language fit;
- duration fit;
- semantic match with the contractor description;
- availability on the requested date.

Avoid generic explanation text such as:

> "This contractor is a great choice for your event."

Explanations must be contractor-specific.

If names were removed from cards, the explanations should still contain enough distinct evidence that cards are not interchangeable.

---

# 7. Non-negotiable business rules

These are hard requirements.

## 7.1 Busy date

A contractor who is busy on the requested date must never appear in the recommendation result.

Example:

```python
if request.date in contractor.busy_dates:
    exclude_contractor()
```

This is a hard exclusion.

Do not allow semantic score, LLM output or any other soft signal to override this rule.

## 7.2 Maximum result count

Return at most:

```text
3 contractors
```

Never pad the result with weaker or invalid contractors just to reach 3.

If only 2 valid contractors exist, return 2.

If only 1 exists, return 1.

If none exist, return 0 and explain why.

## 7.3 Determinism

The same request must produce the same ordering when the underlying data/model configuration has not changed.

Do not introduce random ordering.

Do not shuffle candidates.

If scores tie, use a deterministic tie-breaker such as:

1. final score descending;
2. semantic score descending;
3. price ascending, if appropriate;
4. stable contractor ID ascending.

Define tie-breaking explicitly in code.

## 7.4 Three user-visible outcomes

The application must clearly distinguish:

### MATCHED

Valid contractors were found.

### CATEGORY_NOT_FOUND

The requested contractor category is not available in the selected city/catalog context.

### NO_MATCH

Contractors exist, but all were eliminated by constraints such as:

- busy date;
- budget;
- unsupported format;
- language;
- duration.

Do not render all three cases as the same generic empty state.

---

# 8. Recommended matching pipeline

Use a hybrid architecture.

```text
Request
  ↓
Input validation
  ↓
Hard filters
  ↓
Candidate set
  ↓
Semantic similarity
  ↓
Deterministic scoring
  ↓
Stable sort
  ↓
Top 3
  ↓
Evidence Ledger
  ↓
Optional explanation rewriting
  ↓
Response
```

The eligibility decision must not depend on an LLM.

---

# 9. Hard filters

Hard filters belong primarily to the backend/business layer.

A recommended filtering order is:

```text
all contractors
  ↓
category
  ↓
city
  ↓
availability / busy date
  ↓
event format
  ↓
budget
  ↓
language, if requested
  ↓
duration, if requested
```

The exact implementation may combine filters, but the system should preserve diagnostic information about how many candidates remained after important constraints.

Never send clearly invalid candidates to the final ranking stage.

---

# 10. Filter trace

Where practical, record a deterministic filter trace.

Example:

```json
{
  "initial": 15,
  "after_city": 10,
  "after_date": 6,
  "after_format": 4,
  "after_budget": 2,
  "after_language": 2,
  "after_duration": 2
}
```

This trace is important for:

- debugging;
- Constraint Doctor;
- explainability;
- demo.

Do not fabricate counts on the frontend.

Counts must come from real filtering.

---

# 11. Semantic matching

Semantic matching is a soft ranking signal.

It may use:

- TF-IDF + cosine similarity as a deterministic fallback;
- multilingual embedding models;
- optional rerankers.

Semantic matching should operate primarily on the contractor `description` and a normalized representation of the user request.

Example semantic query:

```text
Современный ведущий для корпоратива,
с импровизацией и интерактивом,
на русском языке.
```

Do not use semantic similarity to override failed hard constraints.

---

# 12. ML strategy

The dataset is small.

Do not fine-tune a model on the 66 profiles for the hackathon unless there is a very strong justified reason.

Preferred strategy:

```text
hard filtering
+
pretrained embeddings or TF-IDF
+
deterministic scoring
+
optional reranker
+
optional LLM wording
```

A safe implementation should continue to work even when external model APIs are unavailable.

At minimum, the system should have a local deterministic fallback.

---

# 13. Deterministic scoring

Scoring must be explicit and inspectable.

An example structure:

```python
final_score = (
    semantic_score * SEMANTIC_WEIGHT
    + budget_score * BUDGET_WEIGHT
    + language_score * LANGUAGE_WEIGHT
    + format_score * FORMAT_WEIGHT
    + duration_score * DURATION_WEIGHT
)
```

Weights must live in configuration/constants, not be duplicated throughout the codebase.

Do not silently change score weights inside UI code.

Do not let an LLM generate the score.

Do not introduce random noise into ranking.

The exact formula may evolve, but it must remain deterministic and explainable.

---

# 14. Evidence Ledger

Every recommendation should be backed by machine-readable evidence.

Preferred conceptual structure:

```json
{
  "date": {
    "matched": true,
    "reason": "Свободен 15 ноября"
  },
  "budget": {
    "matched": true,
    "reason": "700 000 ₸ входит в бюджет 800 000 ₸"
  },
  "format": {
    "matched": true,
    "reason": "Проводит корпоративные мероприятия"
  },
  "language": {
    "matched": true,
    "reason": "Работает на русском языке"
  },
  "duration": {
    "matched": true,
    "reason": "Работает до 6 часов"
  },
  "semantic": {
    "matched": true,
    "score": 0.82,
    "reason": "Описание связано с импровизацией и корпоративами"
  }
}
```

The exact schema may differ, but evidence must remain:

- factual;
- deterministic where possible;
- contractor-specific;
- derived from real data.

Never allow the explanation layer to invent unsupported facts.

---

# 15. LLM usage

LLMs are optional.

A language model may be used only after facts and ranking have already been determined.

Allowed use:

```text
verified evidence
  ↓
LLM
  ↓
natural-language rewrite
```

Example:

Input facts:

```text
price = 700000
budget = 800000
available = true
language = Russian
format = corporate
semantic evidence = improvisation
```

LLM may rewrite those facts into:

> Стоимость входит в ваш бюджет, подрядчик свободен на выбранную дату и работает с корпоративами. В описании также упоминается импровизация.

The LLM must not:

- add unsupported experience;
- invent availability;
- invent languages;
- invent price;
- change ranking;
- add a contractor that failed filters;
- remove a valid contractor because of subjective preference.

If LLM generation fails, use deterministic template explanations.

---

# 16. Constraint Doctor

When there are no valid results, do not return only:

```text
[]
```

The system should explain the blocking constraint.

Example:

```text
Всего ведущих: 15
В выбранном городе: 10
Свободны на дату: 4
Подходят по формату: 2
Входят в бюджет: 0
```

User-facing explanation:

> Подрядчики есть, но после проверки бюджета подходящих вариантов не осталось.

Constraint Doctor may also identify safe alternatives if they are derived from actual data, for example:

- another date;
- higher budget threshold;
- relaxed optional language constraint.

Do not fabricate recommendations.

Do not silently modify the user's request.

Any alternative must be presented as an optional suggestion, not as an automatic replacement of the original criteria.

---

# 17. What-if date analysis

If implemented, alternative-date analysis should compare nearby dates using the real availability calendar.

Example:

```text
14 ноября — 2 кандидата
15 ноября — 5 кандидатов
16 ноября — 3 кандидата
17 ноября — 6 кандидатов
```

Changing date should produce a real new match result.

Do not hardcode alternative-date counts.

Do not display date availability if it cannot be computed from real data.

---

# 18. Backend responsibilities

The backend owns:

- request validation;
- application API;
- dataset access;
- contractor normalization;
- hard filters;
- availability checks;
- city/category/format/budget/language/duration constraints;
- filter trace;
- communication with the AI service;
- stable result assembly;
- API error handling.

The backend must not delegate hard business constraints to the frontend.

The backend must not trust frontend validation as the only validation.

---

# 19. AI service responsibilities

The AI service may own:

- embedding model loading;
- embedding caching;
- semantic similarity;
- ranking signals;
- deterministic score calculation if the architecture places scoring here;
- reranking;
- evidence generation;
- semantic explanation signals;
- optional LLM wording;
- optional Constraint Doctor analysis.

Keep ML dependencies inside the AI service where possible.

Do not add heavy model libraries to the main backend image unless absolutely necessary.

---

# 20. Frontend responsibilities

The frontend owns:

- search form;
- form validation UX;
- API calls via the frontend API layer;
- loading state;
- error state;
- result cards;
- Evidence Ledger visualization;
- Constraint Doctor visualization;
- alternative date interaction;
- responsive layout;
- accessibility.

The frontend must not decide whether a contractor is eligible.

The frontend must not calculate availability.

The frontend must not recalculate ranking.

The frontend must preserve the order returned by the API.

---

# 21. Frontend product scope

The main page should focus on contractor matching.

Primary controls:

- city;
- date;
- event type;
- category;
- budget;
- language;
- duration;
- submit.

Primary result UI:

- up to 3 contractor cards;
- price;
- match score if exposed;
- evidence;
- explanation;
- synthetic profile indicator when applicable.

Important states:

- initial;
- loading;
- matched;
- partial matched result (<3);
- category not found;
- no match;
- API/network error.

Do not create extra product areas that are outside hackathon scope.

---

# 22. UI scope exclusions

Do not add unless explicitly requested:

- authentication;
- registration;
- user profiles;
- favorites;
- booking;
- checkout;
- payments;
- messaging;
- contractor notifications;
- admin panel;
- marketplace ordering flow.

The hackathon task is recommendation, not transaction processing.

---

# 23. Frontend design direction

The frontend may use a premium restrained Liquid Glass direction.

Desired qualities:

- precise;
- calm;
- premium;
- production-like;
- high-contrast;
- readable;
- demo-friendly.

Avoid stereotypical AI-generated design patterns:

- excessive purple gradients;
- glowing blobs;
- floating decorative cards;
- random sparkles;
- robot/brain imagery;
- fake AI metrics;
- meaningless charts;
- excessive glassmorphism;
- excessive hover motion;
- decorative animation without product value.

Use animation only to explain state transitions.

Every visible interactive control must work.

If a control has no implemented action, do not render it.

---

# 24. Frontend implementation rules

Use:

- reusable Chakra components;
- centralized theme/semantic tokens;
- TanStack Query for server state;
- a dedicated API layer;
- strict TypeScript where configured;
- consistent utilities for KZT and dates.

Avoid:

- direct `fetch()` scattered across components;
- duplicated colors;
- `any`;
- random inline API calls;
- random client-side sorting of recommendation results.

The frontend must not reorder backend results.

---

# 25. API guidance

A main endpoint may follow this contract:

```http
POST /api/match
```

Request example:

```json
{
  "city": "Алматы",
  "date": "2026-11-15",
  "event_type": "корпоратив",
  "category": "Ведущий",
  "budget": 800000,
  "duration": 6,
  "language": "русский"
}
```

Possible response:

```json
{
  "status": "matched",
  "results": []
}
```

Other statuses:

```text
category_not_found
no_match
```

A richer response may include:

```json
{
  "status": "no_match",
  "results": [],
  "diagnostics": {
    "initial": 15,
    "after_city": 10,
    "after_date": 4,
    "after_format": 2,
    "after_budget": 0
  }
}
```

Do not treat this example schema as permission to silently break existing APIs.

If the repository already has concrete schemas, preserve them or perform an explicit coordinated migration.

---

# 26. Error handling

Differentiate:

- validation errors;
- category not found;
- no matching contractors;
- AI service failure;
- backend error;
- network failure.

A model/API outage should not automatically make the whole application unusable if deterministic fallback logic can still return valid recommendations.

Never expose raw stack traces to end users.

Log enough information for developers to diagnose failures.

---

# 27. Performance

Hackathon target: responses should arrive in a reasonable time, with approximately 10 seconds as an upper reference point for the live demo.

Avoid loading large models per request.

Load models once during service startup where practical.

Cache contractor embeddings when possible.

Do not recompute static contractor embeddings for every user request.

Do not call an LLM multiple times per contractor unless there is a strong reason.

Prefer one explanation request for the final top results, or deterministic templates.

---

# 28. Data preprocessing

Do not destructively modify the original dataset during runtime.

Normalize parsed fields in memory or through a preprocessing layer.

Typical normalization may include:

- trimming strings;
- normalizing case;
- parsing list-like CSV fields;
- converting date strings to date objects;
- converting numeric fields to integers;
- preserving null `max_hours`;
- preserving synthetic/imputation flags.

Do not lose original IDs.

---

# 29. Synthetic data

The hackathon permits additional synthetic profiles if they use the same structure and have:

```json
{
  "synthetic": true
}
```

If agents add synthetic data:

1. keep original data intact;
2. clearly mark new records;
3. document why they were added;
4. ensure demo/UI shows the synthetic marker.

Do not create hidden synthetic records.

---

# 30. Testing requirements

Changes affecting matching logic should include tests when feasible.

Important cases:

## Busy date

A busy contractor is excluded.

## Same request

Same request returns the same order.

## Different dates

A request on two dates may produce different results due to availability.

## Budget

Over-budget contractors fail the required budget constraint if the product definition treats budget as a hard constraint.

## Language

Requested language is respected.

## Duration

If `max_hours` is applicable and requested duration exceeds it, contractor fails.

If `max_hours` is null for a category where duration is not applicable, do not incorrectly exclude the contractor.

## Maximum output

Never return more than 3 contractors.

## Rare category

Fewer than 3 valid profiles is a valid result.

## No result

Return an explanatory diagnostic state, not an unexplained empty list.

## Category absent

Return the dedicated category-not-found state.

---

# 31. Definition of Done

A feature is not done only because it renders.

The complete project should satisfy:

- request returns within a reasonable time;
- explanations are contractor-specific;
- repeat request gives the same order;
- different dates can change the output due to calendar availability;
- dense-category case works;
- rare-category case works;
- no-result case works;
- empty results are explained;
- team can explain the full pipeline;
- frontend clearly distinguishes main outcome states;
- production/demo build starts reproducibly from repository instructions.

---

# 32. Required demo scenarios

The hackathon expects at least three meaningful scenarios.

Maintain support for:

## Dense category

Examples:

- Ведущий
- Фотограф
- Банкетный зал

The result should demonstrate real ranking among multiple valid candidates.

## Rare category

Examples include categories with around three profiles, such as:

- Флорист
- Декоратор
- Подарки и сувениры
- Ведущий церемонии
- Фото и видеобудки
- Отель
- Инструменталист

The application must handle fewer than 3 results gracefully.

## No result

The app must show why no one passed.

The no-result screen must not be a blank area or a generic error.

---

# 33. README and reproducibility

The hackathon explicitly values reproducibility.

When setup or architecture changes, update repository documentation.

README/setup instructions should clearly explain:

- prerequisites;
- environment variables;
- how to run frontend;
- how to run backend;
- how to run AI service;
- how to run Docker setup;
- how to run tests;
- main API endpoint;
- high-level matching pipeline.

Do not leave undocumented setup steps that only work on one developer's machine.

---

# 34. Docker rules

Preserve the existing Docker-based architecture.

Do not couple model dependencies into the backend container without reason.

If a new dependency is required:

- add it to the appropriate service;
- update the relevant Dockerfile/requirements/package file;
- verify compose build/start still works.

Do not hardcode local Windows absolute paths in application code.

Never commit machine-specific paths such as:

```text
C:\Users\...
```

---

# 35. Environment variables

Secrets and environment-specific URLs must not be hardcoded.

Use environment variables for:

- API base URLs;
- model API keys;
- model selection;
- optional feature flags;
- mock mode where appropriate.

Provide `.env.example` entries when introducing a new variable.

Never commit real API keys.

---

# 36. Git / agent workflow

When an AI coding agent makes changes:

1. inspect `git status`;
2. understand existing code before editing;
3. do not rewrite unrelated files;
4. keep changes scoped to the task;
5. do not delete user work unless necessary;
6. do not run destructive Git commands without explicit user request;
7. do not reset or force-push;
8. do not overwrite uncommitted user changes.

Preferred branch model:

```text
main
├── feature/frontend
├── feature/backend
└── feature/ml
```

Agents may use other branch names, but work should remain isolated and reviewable.

---

# 37. File ownership guidance

When a task is explicitly scoped to frontend:

- prefer modifying `frontend/`;
- do not change backend or AI code unless an API contract change is required;
- if a backend change is necessary, clearly state it.

When scoped to backend:

- prefer `backend/`;
- avoid changing frontend except for coordinated API contract changes.

When scoped to AI/ML:

- prefer `services/ai/`;
- do not place model inference code in frontend;
- do not introduce heavy ML dependencies into backend without reason.

Cross-cutting changes are allowed only when necessary and must be explained.

---

# 38. Code quality

Do not leave:

- dead code;
- unused imports;
- broken buttons;
- placeholder handlers;
- debug `console.log`;
- commented-out experiments;
- unexplained TODOs;
- type errors;
- lint errors caused by the change.

Do not create abstractions that are more complex than the project needs.

Prefer readable, explicit code over clever code.

---

# 39. Agent behavior

Before implementing a substantial change, the agent should:

1. inspect the relevant directories;
2. read existing schemas/types;
3. inspect current API contracts;
4. identify the smallest viable change;
5. preserve existing working behavior.

When the task is broad, implement in this order:

```text
working core
→ integration
→ error states
→ tests
→ polish
```

Do not begin with animation, design polish or LLM integration before the core flow works.

---

# 40. Priority order

For hackathon decisions, use this priority:

```text
1. Correctness / task compliance
2. Explanation quality
3. Honest handling of rare/busy/empty cases
4. Determinism
5. Reliability
6. Speed
7. UI polish
8. Extra features
```

If time is limited, cut optional features before weakening correctness.

---

# 41. Suggested implementation phases

## P0 — required

- dataset loading;
- request validation;
- hard filtering;
- busy-date exclusion;
- deterministic fallback ranking;
- top 3;
- contractor-specific evidence;
- matched/category-not-found/no-match states;
- working frontend form and result cards;
- reproducible run.

## P1 — strong hackathon version

- multilingual embeddings;
- improved semantic score;
- Evidence Ledger UI;
- Constraint Doctor;
- filter trace;
- synthetic profile badge;
- polished frontend;
- caching.

## P2 — optional

- reranker;
- optional LLM rewriting;
- What-if alternative dates;
- additional observability;
- refined animations.

Never block P0 completion on P2.

---

# 42. Final verification checklist for agents

Before declaring a task complete, check what applies.

## General

- [ ] Existing architecture preserved.
- [ ] No unrelated files rewritten.
- [ ] No secrets added.
- [ ] No machine-specific absolute paths added.
- [ ] Relevant documentation updated.

## Backend

- [ ] Request validation works.
- [ ] Busy dates are enforced.
- [ ] No more than 3 results.
- [ ] Output order is deterministic.
- [ ] Error/outcome states are explicit.

## AI

- [ ] Ranking is deterministic.
- [ ] LLM does not control eligibility or order.
- [ ] Semantic score is a soft signal only.
- [ ] Evidence comes from real contractor/request data.
- [ ] Fallback exists where practical.

## Frontend

- [ ] No empty interactive buttons.
- [ ] Loading works.
- [ ] Matched works.
- [ ] Fewer-than-3 results work.
- [ ] Category-not-found works.
- [ ] No-match diagnostics work.
- [ ] API error state is distinct.
- [ ] Backend order is preserved.
- [ ] Synthetic profiles are labeled.
- [ ] Mobile layout does not break.

## Build / tests

Run the relevant project checks available in the repository, for example:

```bash
npm run build
npm run lint
pytest
docker compose build
```

Do not claim a check passed unless it was actually run successfully.

---

# 43. Core principle

The core principle of EventLens is:

> The system should not merely say which contractor is best. It should show the concrete evidence that made each contractor eligible, relevant and highly ranked.

Every architecture, ML, backend and frontend decision should preserve that principle.
