# Enterprise Security Intelligence Copilot

Portfolio project for a **local, synthetic** security intelligence workflow. The planned system combines policy retrieval, a simulated SIEM, anomaly detection, and evidence-grounded local LLM explanations. No production security capability or real organization data is claimed.

## Current status

Phase 7 adds a leakage-safe synthetic behavioral anomaly subsystem: UTC daily features, a chronological Isolation Forest experiment, persisted preprocessing/model artifact, reusable inference service, separate scenario evaluation, and local MLflow tracking. It is not integrated into LangGraph yet. No UI or autonomous remediation is implemented. See [the phased checklist](docs/implementation-checklist.md), [ML guide](docs/ml.md), [agent guide](docs/agent.md), and [security notes](docs/security.md).

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

For Phase 5, set distinct random `DEMO_API_TOKEN` (admin) and `DEMO_READ_TOKEN` (reader) values in the ignored `.env`, then start the loopback API:

```bash
.venv/bin/uvicorn app.api.main:create_app --factory --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/api/v1/docs` for OpenAPI. See [API guide](docs/api.md) for routes, validation, auth, and a local smoke check. The demo tokens are not enterprise SSO.

For the Phase 6 synthetic development evaluation, run `.venv/bin/python -m app.agent.evaluate` while PostgreSQL, Qdrant, and native Ollama are healthy. Detailed per-request results are written to ignored `work/` files. See [agent design and limits](docs/agent.md).

For Phase 7, run `MLFLOW_DISABLE_AGENT_HINT=1 .venv/bin/python -m app.ml.train --clean`. It trains from the synthetic PostgreSQL events, evaluates against the separate ignored scenario file, writes the selected artifact under ignored `models/`, and records two local MLflow runs under ignored `work/`. See [ML design and measured results](docs/ml.md).

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
- [Versioned API](docs/api.md)
- [Demo security boundary](docs/security.md)
- [Phase 5 checkpoint](docs/phase-5-checkpoint.md)
- [Read-only LangGraph agent](docs/agent.md)
- [Phase 6 checkpoint](docs/phase-6-checkpoint.md)
- [Synthetic anomaly model](docs/ml.md)
- [Phase 7 checkpoint](docs/phase-7-checkpoint.md)

The full architecture, workflows, measured evaluation results, and demo instructions will be documented as the corresponding components are implemented and verified.
