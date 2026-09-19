# Phase 13 checkpoint — GitHub Actions CI

**Scope:** Phase 13 only. Added GitHub Actions validation for Python quality, ordinary tests, PostgreSQL migrations, Compose configuration, and build-only application images. The workflow uses no native Ollama, live Qdrant, ignored model artifact, developer volume, runtime ground truth, MLflow state, paid API, repository secret, image registry, deployment step, or Phase 14 hardening work.

## Workflow

`.github/workflows/ci.yml` runs for pull requests and pushes to `main`. Concurrency cancellation stops superseded runs for the same branch or pull request. Top-level permissions are limited to `contents: read`; the workflow does not use `pull_request_target`, `continue-on-error`, write permissions, a registry login, or a deployment environment.

The workflow has three jobs:

- **Python quality:** Python 3.11.13, CPU-only PyTorch plus locked dependency install, `pip check`, Ruff lint, and Ruff format check.
- **Tests and migrations:** ephemeral PostgreSQL 17.11, migration upgrade, deterministic synthetic seed under `RUNNER_TEMP`, Alembic consistency check, and 147 selected tests.
- **Compose and container builds:** Compose bootstrap-profile validation, then build-only FastAPI, Streamlit, and trainer images plus architecture and image-content checks.

The test selection is `python -m pytest -m "not live_ollama and not qdrant_integration"`. It includes the PostgreSQL integration against the fresh migrated and seeded database. Native Ollama and live Qdrant are explicitly deselected. Their deterministic mocked behavior remains covered by the ordinary suite, and Phase 12 separately validated the real services.

## Supply chain and cache behavior

`actions/checkout` v4.2.2 and `actions/setup-python` v5.6.0 are pinned by full immutable commit SHA with readable release comments. Python dependencies come from `requirements-dev.lock`; the official CPU-only PyTorch wheel is installed first so Linux does not resolve unused CUDA packages. Setup Python's pip cache key is tied to the lock file. No workflow cache path includes `.env`, credentials, model artifacts, MLflow databases/artifacts, runtime ground truth, or local work directories.

Action updates are manual and reviewable: check the official release notes, update the full SHA and release comment together, and repeat local workflow validation. No floating action tags are used.

## Local reproduction result

The workflow YAML parsed successfully with Ruby's YAML parser and was inspected for required triggers, immutable action references, permissions, cache key input, commands, and prohibited `pull_request_target`/`continue-on-error` behavior.

A fresh disposable PostgreSQL 17.11 container was migrated from an empty database to `20260918_01`, seeded with 120 users, 140 devices, 12,065 events, 6 incidents, and 6 scenarios, then checked by Alembic. `alembic check` reported no new upgrade operations.

The exact CI marker selection collected 149 tests, deselected 2, and passed all **147 selected tests** in 4.12 seconds. The included PostgreSQL integration passed. The two deliberate exclusions were native Ollama and live Qdrant. Local reproduction exposed and fixed one genuine isolation defect: the safe-default settings test now removes credential/database environment overrides before asserting defaults.

The final broader local regression also passed **148 tests with 1 skipped** in 4.38 seconds. It included the available PostgreSQL and Qdrant integrations; the only skip was the opt-in native Ollama test.

Additional results:

- `pip check`: no broken requirements.
- Ruff lint: passed.
- Ruff format: all 113 discovered Python files passed check mode.
- Compose bootstrap profile: valid with disposable values and no output of expanded configuration.
- Image builds: `esic-api:phase12`, `esic-streamlit:phase12`, and `esic-trainer:phase12` succeeded.
- Local image architecture: all three were ARM64 on the Apple M3 Docker server.
- Image inspection: no `.env`, Git history, runtime ground truth, anomaly artifact, local MLflow database, or evaluation directory.
- Build contexts remained approximately 701 KB for API, 698 KB for trainer, and 85 KB for Streamlit.

## Architecture boundary

The GitHub `ubuntu-latest` job is designed to build native `amd64` images and asserts that result. This is build validation on the hosted architecture, not ARM64 runtime evidence. Phase 12 separately built and exercised all three images on the target Apple M3 ARM64 host. CI deliberately avoids emulated multi-platform runtime tests and does not push a manifest or image.

## Offline evaluation decision

Phase 10 offline evaluation does not require Ollama, but it requires an ingested Qdrant collection, PostgreSQL data, and the ignored trained anomaly artifact. Running it would force policy embedding downloads and model training into CI. It is excluded for cost and reproducibility. Deterministic evaluation metrics and all 13 safety contracts remain covered by ordinary unit tests.

## GitHub-hosted status

No Git remote is configured in this checkout. No workflow was pushed, no repository setting was changed, and no GitHub-hosted Actions result exists. No badge was added. The workflow is validated locally; the first hosted run remains pending after the owner pushes the repository.

## Remaining limits and technical debt

The hosted runner may differ from the local Docker and filesystem environment, so the first actual Actions run may expose runner-specific behavior. The suite retains the known upstream Starlette/AnyIO deprecation warning. CI does not run native Ollama, live Qdrant, Phase 10 offline/live evaluation, ARM64 emulation, container runtime integration, vulnerability scanning, dependency update automation, image signing, publishing, deployment, or production security checks.

## Proposed Phase 14 scope

Phase 14 should harden the existing boundaries with targeted tests and fixes for authentication/authorization edge cases, request and pagination limits, malformed dependency responses, startup and recovery behavior, PostgreSQL/Qdrant/Ollama/model failure transitions, concurrent request isolation, prompt-injection and provenance enforcement, API/OpenAPI contracts, and container/runtime security assumptions. It should run unit, integration, API, RAG, agent, and recovery checks; fix demonstrated defects; avoid new product capabilities or production IAM; and preserve the synthetic read-only architecture. Phase 14 has not started.
