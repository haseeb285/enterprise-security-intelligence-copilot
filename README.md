# Enterprise Security Intelligence Copilot

Portfolio project for a **local, synthetic** security intelligence workflow. The planned system combines policy retrieval, a simulated SIEM, anomaly detection, and evidence-grounded local LLM explanations. No production security capability or real organization data is claimed.

## Current status

Phase 2 data layer is complete: PostgreSQL schema/migration, deterministic fictional telemetry, bounded event/incident queries, and a seed command. No API, RAG, ML, agent, or UI is implemented yet. See [the phased checklist](docs/implementation-checklist.md) and [architecture decision](docs/phase-0-architecture.md).

## Local setup

Use Python 3.11 on arm64. On the inspected Mac, that is `/opt/anaconda3/bin/python3.11`.

```bash
/opt/anaconda3/bin/python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.lock
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

Copy `.env.example` to `.env` only when overriding defaults. Keep local secrets and private inputs out of Git. `OLLAMA_BASE_URL` defaults to the macOS loopback address; Dockerized API settings will override it with `host.docker.internal` in a later phase.

For Phase 2, set `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT`, and matching `DATABASE_URL` in the ignored `.env`. Generate a unique local password; do not use any organization credentials. Then:

```bash
docker compose up -d postgres
docker compose ps
.venv/bin/alembic upgrade head
.venv/bin/python -m app.db.seed
.venv/bin/alembic check
```

The Compose file runs only PostgreSQL and binds the configured host port to loopback. See [data model](docs/data-model.md) and [synthetic data](docs/synthetic-data.md) for schema, scenario, ground-truth, and reset details.

`requirements-dev.lock` records the exact Phase 1 environment, including transitive packages. Refresh it deliberately after dependency changes. `pyproject.toml` lists the direct runtime and development dependencies.

## Documentation

- [Complete requirements](docs/project-specification.md)
- [Architecture and environment findings](docs/phase-0-architecture.md)
- [Implementation checklist](docs/implementation-checklist.md)
- [Phase 2 data model](docs/data-model.md)
- [Synthetic data methodology](docs/synthetic-data.md)

The full architecture, workflows, measured evaluation results, and demo instructions will be documented as the corresponding components are implemented and verified.
