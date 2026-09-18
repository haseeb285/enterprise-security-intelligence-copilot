# Phase 5 checkpoint — FastAPI boundary

**Scope:** Phase 5 only. Added versioned FastAPI routes for existing synthetic event/incident reads and evidence-only policy retrieval, plus health, demo token roles, validation, safe errors, CORS, lifespan, audit hooks, tests, and documentation. No chat, agent, ML, MLflow, Streamlit, or RAG answer generation was added.

## Implemented

- `app/api/main.py` owns the app factory, lifespan, CORS, request-size guard, safe exception handlers, and dependency readiness.
- `app/api/routes/` holds small route modules. `schemas.py` defines request/response contracts; `dependencies.py` supplies demo principals and database sessions; `services.py` calls the existing repositories and `RagService` and writes audit records.
- `app/db/seed.py` now accepts extra API audit rows while still checking seeded core-table counts and the marker. `VectorStore` can reuse the lifespan-owned Qdrant client.
- Seven documented paths under `/api/v1`: health, event list/detail, user events, incident list/detail, and retrieval.

## Measured validation on the local Mac

Environment: Python 3.11 in `.venv`, native Ollama with configured `qwen3.5:4b`, Docker Compose PostgreSQL 17.11 and Qdrant 1.19.1 on loopback, synthetic seed with 12,065 events, 120 users, 140 devices, and six incidents. Validation used local services and a one-off FastAPI TestClient smoke script with random in-process tokens; no public endpoint was exposed.

- API tests: **16 passed**, covering startup, health states, authentication, authorization, filters, pagination and ID validation, safe failures, CORS, retrieval, OpenAPI, and audit behavior.
- Full ordinary suite: **63 passed, 1 skipped** (`tests/test_ollama_live.py` is deliberately opt-in), with two upstream TestClient/AnyIO deprecation warnings.
- Live API smoke: health **200**, application/PostgreSQL/Qdrant/Ollama all `ok`; events **200** (43 high-severity matches), event detail **200**, user events **200**, incidents **200** (six total), reader incident access **403**, missing token **401**, bad limit **422**, retrieval **200** with three cited evidence items and `insufficient_evidence=false`, OpenAPI **200** with seven paths, five audit rows added. The first retrieval took **12,187 ms** including local embedding-model load. Subsequent latency was not benchmarked.
- A separate actual Uvicorn process started on `127.0.0.1:18080` using the documented factory command and returned HTTP **200** for health with all four components `ok`; it was then stopped.
- `docker compose ps`: PostgreSQL and Qdrant containers healthy. `alembic current`: `20260918_01 (head)`; `alembic check`: no new operations. Repeat `python -m app.db.seed`: `already_seeded` after the API audit writes, confirming the guard change.
- `ruff check .`, `ruff format --check .`, `pip check`, and `docker compose config --quiet` passed. The ignored `.env` and smoke script stayed out of Git. Repository scan for common secret formats found no committed credential values.

## Limits and next gate

Demo tokens are not production identity or IAM. Audit writes add a database commit to each authenticated read; this is appropriate for the local demo but needs a durable operational design later. First retrieval can take seconds as the embedding model loads. OpenAPI uses a documented factory command (`uvicorn app.api.main:create_app --factory`) because token validation occurs when the app is created. FastAPI TestClient emits two upstream deprecation warnings, with no observed functional failure.

Phase 6, if approved, is the bounded LangGraph agent with typed state, selective read-only evidence routing, tool contracts, workflow and failure tests. Phase 6 was not started here.
