# Enterprise Security Intelligence Copilot

Portfolio project for a **local, synthetic** security intelligence workflow. The planned system combines policy retrieval, a simulated SIEM, anomaly detection, and evidence-grounded local LLM explanations. No production security capability or real organization data is claimed.

## Current status

Phase 1 foundation is complete: package, validated environment settings, quality configuration, and smoke tests. No API, database, RAG, ML, agent, or UI is implemented yet. See [the phased checklist](docs/implementation-checklist.md) and [architecture decision](docs/phase-0-architecture.md).

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

`requirements-dev.lock` records the exact Phase 1 environment, including transitive packages. Refresh it deliberately after dependency changes. `pyproject.toml` lists the direct runtime and development dependencies.

## Documentation

- [Complete requirements](docs/project-specification.md)
- [Architecture and environment findings](docs/phase-0-architecture.md)
- [Implementation checklist](docs/implementation-checklist.md)

The full architecture, workflows, measured evaluation results, and demo instructions will be documented as the corresponding components are implemented and verified.
