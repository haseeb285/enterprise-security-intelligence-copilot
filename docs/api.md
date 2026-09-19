# Phase 5 API

This is a local, synthetic-data FastAPI boundary over PostgreSQL, Qdrant policy retrieval, the persisted anomaly model, and native Ollama. It exposes the bounded investigation agent and no general chat or write endpoint.

## Run locally

Use the Python 3.11 environment and configure PostgreSQL/Qdrant/Ollama as described in the README. Set two distinct, random bearer tokens of at least 24 characters in the ignored `.env` as `DEMO_READ_TOKEN` and `DEMO_API_TOKEN` (admin). For example, generate each token with `python -c 'import secrets; print(secrets.token_urlsafe(32))'` and paste it into `.env` without committing it. Set `CORS_ORIGINS` to a JSON array of exact origins if a browser client needs cross-origin requests, for example `["http://localhost:8501"]`. Default CORS allows no origins.

```bash
.venv/bin/uvicorn app.api.main:create_app --factory --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/api/v1/docs` for interactive OpenAPI or `/api/v1/openapi.json` for the schema. API startup fails if demo tokens are missing, short, or identical. The app opens the DB engine, Qdrant client, and Ollama provider during lifespan and closes them on shutdown. It does not load an embedding model until a retrieval request. All route functions are synchronous because these local database and provider interfaces are synchronous; FastAPI runs them in its threadpool.

## Routes

| Method | Route | Access | Behavior |
|---|---|---|---|
| GET | `/api/v1/health` | Public | Reports application, PostgreSQL, Qdrant collection, and Ollama model readiness; returns 200 ready or 503 degraded. |
| GET | `/api/v1/events` | Reader or admin | Bounded search of synthetic security events. |
| GET | `/api/v1/events/{event_id}` | Reader or admin | One synthetic event or 404. |
| GET | `/api/v1/users/{user_id}/events` | Reader or admin | Bounded events for a synthetic user. |
| GET | `/api/v1/incidents` | Admin | Bounded list of synthetic incidents. |
| GET | `/api/v1/incidents/{incident_id}` | Admin | One synthetic incident or 404. |
| GET | `/api/v1/audit` | Admin | Bounded newest-first safe audit metadata; internal detail payloads are omitted. |
| POST | `/api/v1/retrieval` | Reader or admin | Evidence-only retrieval with citation metadata and an insufficient-evidence flag. |
| POST | `/api/v1/investigate` | Reader or admin | Bounded read-only LangGraph investigation; incident evidence requires admin. |

Send `Authorization: Bearer <token>` for protected routes. The reader token accesses events and retrieval; the admin token additionally accesses incidents. No route accepts writes to source events or incidents. The role checks are dependency functions that can be replaced when a real identity provider is introduced.

Event filters: `user_id`, `start_time`, `end_time`, `severity`, `event_type`, `source_ip`, `device_id`, `incident_id`. IDs must match the existing synthetic ID formats. Timestamps must include a timezone, and `start_time` must be no later than `end_time`. Severity is `low`, `medium`, `high`, or `critical`. Pages use `limit` 1–100 (default 50) and `offset` 0–1,000,000 (default 0). The retrieval JSON body has `query` 1–4,000 nonblank characters and `top_k` 1–10 (default 5). POST bodies above 8 KiB are rejected.

Responses use JSON. Missing/invalid token returns 401; insufficient role 403; absent resource 404; invalid input 422; unavailable dependency 503. Safe errors do not echo submitted values, SQL errors, provider internals, filesystem paths, or prompts. Health reports only coarse state labels (`ok`, `unavailable`, `model_missing`, `collection_missing`). The OpenAPI schema documents bearer auth and response models.

Authenticated successful and not-found reads write an `audit_logs` record with action, resource type, optional synthetic ID, result, and demo role. Retrieval failures also log a failure when PostgreSQL remains available. Audit details do not include tokens, queries, policy text, or event payloads. Invalid input and unauthenticated requests do not write audit rows. The audit table's nullable user foreign key remains null for demo-token principals.

The Phase 9 Streamlit client uses only these HTTP routes. Its audit page requires the admin token and receives only `audit_id`, timestamp, action, resource type, optional synthetic resource ID, and result. The API never sends the internal audit `details` payload to the frontend.

## Quick checks

```bash
.venv/bin/python -m pytest tests/test_api.py
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m pip check
```

A one-off local smoke script used for Phase 5 is in ignored `work/phase5_smoke.py`. It generates temporary tokens in process, exercises live dependencies with FastAPI's test client, and prints only aggregate results. Ordinary automated tests use SQLite and fake Qdrant/Ollama/RAG services; they do not require network access or model downloads.

## Integrated investigation route

`POST /api/v1/investigate` accepts `{"request":"..."}` with 1–4,000 nonblank characters and a reader or admin bearer token. It runs the bounded read-only LangGraph agent described in [the agent guide](agent.md). Readers can receive policy, synthetic event, and typed anomaly evidence; the incident tool is admin-only.

The response schema exposes `summary`, `observed_evidence`, `ml_analysis`, `policy_context`, `interpretation`, `recommended_next_steps`, `evidence_sufficiency`, `sources`, selected tools, per-tool safe outcomes, safe errors, and graph/tool counts. Each ML object contains the exact floating point score and flag returned by the service, the observation window, feature values/signals, model version, demonstration statement, and provenance. A valid request may return HTTP 200 with `complete`, `partial_evidence`, `insufficient_evidence`, or another safe workflow outcome. Callers must inspect both `outcome` and `evidence_sufficiency`.

Invalid body and missing token retain the 422/401 behavior. Investigation audit rows store workflow metadata without request text, evidence, ML features, prompts, or generated prose. `ML_MODEL_PATH` configures the ignored local artifact and defaults to `models/anomaly/isolation_forest_daily_v1.joblib`.
