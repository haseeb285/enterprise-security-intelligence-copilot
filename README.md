# Enterprise Security Intelligence Copilot

Portfolio project for a **local, synthetic** security intelligence workflow. The planned system combines policy retrieval, a simulated SIEM, anomaly detection, and evidence-grounded local LLM explanations. No production security capability or real organization data is claimed.

## Current status

Phase 13 adds GitHub Actions checks for the pinned Python environment, Ruff, ordinary tests, Alembic consistency, Compose configuration, and build-only API, Streamlit, and trainer images. CI requires no native Ollama, private data, ignored model artifact, persistent developer volume, paid API, or repository secret. This is continuous integration for a local demonstration, not deployment automation. See [the CI guide](docs/ci.md), [local deployment guide](docs/deployment-local.md), and [phased checklist](docs/implementation-checklist.md).

## Local setup

Use Python 3.11 on arm64. On the inspected Mac, that is `/opt/anaconda3/bin/python3.11`.

```bash
/opt/anaconda3/bin/python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.lock
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

Copy `.env.example` to `.env` only when overriding defaults. Keep local secrets and private inputs out of Git. `OLLAMA_BASE_URL` defaults to the macOS loopback address for host-native development; Compose configures FastAPI to use `host.docker.internal`.

## Run locally with Docker Compose

Keep Ollama native on macOS, start it, and install the configured model:

```bash
ollama pull qwen3.5:4b
curl --fail http://127.0.0.1:11434/api/tags
```

Create an ignored `.env` from `.env.example` and set PostgreSQL credentials plus distinct random admin and reader demo tokens. Then run the explicit bootstrap:

```bash
make docker-build
make docker-infra
make docker-migrate
make docker-seed
make docker-ingest
make docker-train
make docker-up
```

Open <http://127.0.0.1:8501>. PostgreSQL and Qdrant use named volumes; normal startup does not reset, re-seed, re-embed, or retrain them. The API mounts the ignored model directory read-only, while the one-off trainer creates the trusted local artifact. See [local Docker deployment](docs/deployment-local.md) for configuration, health, cleanup, measured memory, failure behavior, and limitations.

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

For the Phase 8 integrated development evaluation, keep PostgreSQL, Qdrant, native Ollama, the policy collection, and the ignored model artifact available, then run:

```bash
.venv/bin/python -m app.agent.evaluate_integrated
```

The 20-case measured run is documented in [the Phase 8 checkpoint](docs/phase-8-checkpoint.md). Results are written under ignored `work/`.

For Phase 9, keep FastAPI running and start the loopback Streamlit client:

```bash
ESIC_API_BASE_URL=http://127.0.0.1:8000/api/v1 \
  .venv/bin/streamlit run frontend/app.py --server.address 127.0.0.1
```

Open `http://127.0.0.1:8501` and enter the reader or admin demo token in the password field. Streamlit communicates only with FastAPI; it does not connect directly to PostgreSQL, Qdrant, Ollama, LangGraph, or the ML service. See [the frontend guide](docs/frontend.md) and [Phase 9 checkpoint](docs/phase-9-checkpoint.md).

## Development evaluation

Run the layers that do not require Ollama, then the live local-model layers:

```bash
.venv/bin/python -m app.evaluation.run --offline
.venv/bin/python -m app.evaluation.run --live
```

The suite uses synthetic events, fictional policies, the local `qwen3.5:4b` model, and a small development case set. It does not measure production SOC performance and does not calculate one overall accuracy score. Exact measured strengths and failures are generated in [the Phase 10 summary](evaluation/results/phase10-summary.md); methodology and reproduction details are in [the evaluation guide](docs/evaluation.md).

`requirements-dev.lock` records the exact local Python environment, including transitive packages. Refresh it deliberately after dependency changes. `pyproject.toml` lists direct dependencies.

## Continuous integration

The workflow in `.github/workflows/ci.yml` runs on pull requests and pushes to `main`. It uses Python 3.11.13, an ephemeral PostgreSQL service, deterministic synthetic fixtures, mocked local-model behavior, Compose validation, and build-only application images. Native Ollama and live Qdrant tests are intentionally excluded. The hosted runner builds `amd64`; Phase 12 separately validated the runtime on an Apple M3 `arm64` host.

No CI badge is included because this checkout has no configured GitHub remote. See [continuous integration](docs/ci.md) for the exact jobs, marker selection, supply-chain pinning, architecture boundary, and local reproduction commands.

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
- [Phase 8 checkpoint](docs/phase-8-checkpoint.md)
- [Streamlit frontend](docs/frontend.md)
- [Phase 9 checkpoint](docs/phase-9-checkpoint.md)
- [Layered development evaluation](docs/evaluation.md)
- [Phase 10 checkpoint](docs/phase-10-checkpoint.md)
- [Generated Phase 10 results](evaluation/results/phase10-summary.md)
- [Phase 11 observability](docs/observability.md)
- [Phase 11 checkpoint](docs/phase-11-checkpoint.md)
- [Local Docker Compose deployment](docs/deployment-local.md)
- [Phase 12 checkpoint](docs/phase-12-checkpoint.md)
- [Continuous integration](docs/ci.md)
- [Phase 13 checkpoint](docs/phase-13-checkpoint.md)

The full architecture, workflows, measured evaluation results, and demo instructions will be documented as the corresponding components are implemented and verified.
