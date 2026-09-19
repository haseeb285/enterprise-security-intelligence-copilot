# Continuous integration

Phase 13 adds one GitHub Actions workflow at `.github/workflows/ci.yml`. It validates the public repository on pushes to `main` and on pull requests. Superseded runs for the same branch or pull request are cancelled. The workflow has only `contents: read` permission and does not use `pull_request_target`, repository secrets, deployment credentials, or registry credentials.

This is continuous integration for a local demonstration project. It does not deploy the application, publish images, run release automation, or validate a production environment.

## Jobs

### Python quality

The `quality` job uses Python 3.11.13, installs the official CPU-only PyTorch wheel before applying `requirements-dev.lock`, runs `pip check`, Ruff lint, and Ruff format in check mode. Preinstalling the CPU wheel prevents Linux pip from resolving unused CUDA packages. Ruff never modifies repository files in CI.

### Tests and migrations

The `tests` job creates a fresh PostgreSQL 17.11 service with explicitly disposable CI-only credentials. It installs the locked environment, upgrades the empty database with Alembic, creates deterministic synthetic data with ground truth written under `RUNNER_TEMP`, and runs `alembic check` before the test suite.

The test command is:

```bash
python -m pytest -m "not live_ollama and not qdrant_integration"
```

The PostgreSQL integration marker remains included and runs against the migrated, seeded service. The Qdrant integration is excluded because the ordinary RAG behavior is covered by deterministic fake-store tests and a live Qdrant service would duplicate Phase 12 runtime validation. Native Ollama is explicitly excluded; all ordinary LLM, agent, API, and failure tests use deterministic or mocked providers.

### Compose and container builds

The `containers` job validates the bootstrap profile with `docker compose config --quiet`, then builds:

- `esic-api:phase12`
- `esic-streamlit:phase12`
- `esic-trainer:phase12`

It does not start the stack or push images. The trainer is included because it creates the reproducible anomaly artifact during a clean bootstrap. After building, the job verifies that hosted-runner images are `amd64` and that `.env`, Git history, runtime ground truth, the anomaly artifact, an MLflow database, and evaluation files are absent.

Docker Compose uses BuildKit on the hosted runner. The repository `.dockerignore` excludes work files, caches, local model artifacts, runtime data, tests, documentation, evaluation output, and workflow files from the application build contexts.

## Dependency and action pinning

Python packages are installed from the fully pinned `requirements-dev.lock`. `actions/setup-python` uses its pip cache keyed from that lock file. Only pip downloads/wheels are cached; `.env`, credentials, model artifacts, MLflow state, ground truth, and developer runtime directories are not cache paths.

The workflow uses only GitHub-maintained `actions/checkout` and `actions/setup-python`. Both references are immutable full commit SHAs with release comments. Updates should be deliberate: review the official action release notes, replace the SHA and version comment together, and validate the workflow locally. No floating major tag is used.

## Runner architecture

GitHub's `ubuntu-latest` hosted runner builds native `amd64` images. This proves that the Dockerfiles and pinned dependencies build on the hosted architecture. It does not prove ARM64 runtime behavior. Phase 12 separately built and ran all images on an Apple M3 Docker server reporting `arm64`. CI does not add emulation or a platform matrix because that would repeat expensive builds without adding a real ARM64 runtime check.

## Offline evaluation decision

The Phase 10 `--offline` command does not call Ollama, but it still requires an ingested Qdrant collection, a migrated and seeded PostgreSQL database, and the ignored trained anomaly artifact. Reconstructing those layers would add embedding downloads and model training to every CI run. It is therefore excluded. Its deterministic scoring and safety contracts remain covered by `tests/test_evaluation.py`; full offline evaluation remains a documented local validation command.

## Reproduce locally

Quality checks:

```bash
.venv/bin/python -m pip install --requirement requirements-dev.lock
.venv/bin/python -m pip check
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
```

For the same database path as CI, start a disposable PostgreSQL container on an unused loopback port, then migrate, seed, and test:

```bash
docker run --rm --detach --name esic-phase13-postgres \
  -e POSTGRES_USER=esic_ci \
  -e POSTGRES_PASSWORD=ci-only-not-a-secret \
  -e POSTGRES_DB=esic_ci \
  -p 127.0.0.1:55434:5432 \
  postgres:17.11-bookworm

DATABASE_URL=postgresql+psycopg://esic_ci:ci-only-not-a-secret@127.0.0.1:55434/esic_ci \
  .venv/bin/alembic upgrade head
DATABASE_URL=postgresql+psycopg://esic_ci:ci-only-not-a-secret@127.0.0.1:55434/esic_ci \
  .venv/bin/python -m app.db.seed --ground-truth-path /tmp/esic-ci-ground-truth.json
DATABASE_URL=postgresql+psycopg://esic_ci:ci-only-not-a-secret@127.0.0.1:55434/esic_ci \
  .venv/bin/alembic check
DATABASE_URL=postgresql+psycopg://esic_ci:ci-only-not-a-secret@127.0.0.1:55434/esic_ci \
  .venv/bin/python -m pytest -m "not live_ollama and not qdrant_integration"

docker stop esic-phase13-postgres
```

Compose and image checks:

```bash
POSTGRES_USER=esic_ci \
POSTGRES_PASSWORD=ci-only-not-a-secret \
POSTGRES_DB=esic_ci \
DEMO_API_TOKEN=ci-admin-token-placeholder-000001 \
DEMO_READ_TOKEN=ci-reader-token-placeholder-00001 \
  docker compose --profile bootstrap config --quiet

POSTGRES_USER=esic_ci \
POSTGRES_PASSWORD=ci-only-not-a-secret \
POSTGRES_DB=esic_ci \
DEMO_API_TOKEN=ci-admin-token-placeholder-000001 \
DEMO_READ_TOKEN=ci-reader-token-placeholder-00001 \
  docker compose --profile bootstrap build api streamlit train
```

These values are disposable local examples and are not suitable for a running shared environment.

## Hosted status

This repository currently has no configured Git remote, so no badge is added and no hosted Actions run can be inspected. The workflow is validated locally. Its first GitHub-hosted result remains pending until the repository is pushed by its owner.
