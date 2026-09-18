# Enterprise Security Intelligence Copilot

Portfolio project for a **local, synthetic** security intelligence workflow. The planned system combines policy retrieval, a simulated SIEM, anomaly detection, and evidence-grounded local LLM explanations. No production security capability or real organization data is claimed.

## Current status

Phase 4 local LLM foundation is complete: PostgreSQL and synthetic telemetry, local policy retrieval, and a native macOS Ollama provider with text and schema-constrained generation. No RAG answer generation, API, ML model, agent, or UI is implemented yet. See [the phased checklist](docs/implementation-checklist.md), [RAG design](docs/rag.md), and [LLM foundation](docs/llm.md).

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

For Phase 3, set `QDRANT_PORT=6333` in `.env`, then:

```bash
docker compose up -d postgres qdrant
.venv/bin/python -m app.rag.ingest data/policies/synthetic --prune
.venv/bin/python -m app.rag.evaluate --threshold 0.805
```

Both services bind their host ports to loopback by default. See [data model](docs/data-model.md), [synthetic data](docs/synthetic-data.md), and [local RAG](docs/rag.md) for behavior and validation.

For Phase 4, install the official native Ollama macOS app and pull `qwen3.5:4b` (approximately 3.4 GB). Keep the model on the host. With Ollama available at `OLLAMA_BASE_URL`, run:

```bash
.venv/bin/python -m app.llm.smoke
RUN_LIVE_OLLAMA=1 .venv/bin/python -m pytest -m live_ollama
```

See [LLM setup and limitations](docs/llm.md). The ordinary test suite mocks Ollama and does not need a downloaded model.

`requirements-dev.lock` records the exact local Python environment, including transitive packages. Refresh it deliberately after dependency changes. `pyproject.toml` lists direct dependencies.

## Documentation

- [Complete requirements](docs/project-specification.md)
- [Architecture and environment findings](docs/phase-0-architecture.md)
- [Implementation checklist](docs/implementation-checklist.md)
- [Phase 2 data model](docs/data-model.md)
- [Synthetic data methodology](docs/synthetic-data.md)
- [Local policy retrieval](docs/rag.md)
- [Phase 3 checkpoint](docs/phase-3-checkpoint.md)
- [Local LLM foundation](docs/llm.md)
- [Phase 4 checkpoint](docs/phase-4-checkpoint.md)

The full architecture, workflows, measured evaluation results, and demo instructions will be documented as the corresponding components are implemented and verified.
