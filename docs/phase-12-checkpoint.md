# Phase 12 checkpoint — local Docker Compose deployment

**Scope:** Phase 12 only. Added ARM64 application images, an explicit local Compose bootstrap, persistent PostgreSQL and Qdrant state, container-to-native Ollama access, a mounted and reproducibly trained anomaly artifact, clean-state validation, failure recovery checks, and deployment documentation. Ollama remains native on macOS. No cloud deployment, CI, Kubernetes, production identity, reverse proxy, TLS, autonomous action, or Phase 13 work was added.

## Environment and images

- Docker client/server: 28.3.3; Docker Desktop 4.45.0.
- Docker Compose: v2.39.2-desktop.1.
- Docker server architecture: arm64.
- Base: `python:3.11.13-slim-bookworm`, resolved as `sha256:86adf8dbadc3d6e82ee5dd2c74bec2e1c2467cdad47886280501df722372d2e1`.
- `esic-api:phase12`: arm64, 433.7 MB, CPU-only PyTorch 2.14.0, non-root runtime.
- `esic-streamlit:phase12`: arm64, 181.1 MB, frontend-only runtime, non-root.
- `esic-trainer:phase12`: arm64, 571.7 MB, one-off API base plus MLflow 3.16.1.
- Infrastructure: `postgres:17.11-bookworm` and `qdrant/qdrant:v1.19.1`, both resolved for arm64.

The first API build exposed that the default PyPI PyTorch wheel attempted to add CUDA packages. The Dockerfile was corrected to install the official ARM64 CPU wheel from PyTorch's CPU index. Build contexts measured about 698 KB for the API/trainer and 85 KB for Streamlit. The application images contain no `.env`, Git history, model artifact, runtime ground truth, local MLflow database, evaluation output, or repository work files.

## Compose architecture and bootstrap

Runtime services are PostgreSQL, Qdrant, FastAPI, and Streamlit. PostgreSQL and Qdrant use named volumes `postgres_data` and `qdrant_data`; API and Streamlit expose loopback ports. `migrate`, `seed`, `ingest`, and `train` are one-off services under the `bootstrap` profile. MLflow is installed only in the trainer image and is not an always-on service.

FastAPI waits for PostgreSQL with a bounded application-level retry in addition to Compose dependency health. PostgreSQL, Qdrant, API, and Streamlit all have lightweight health checks. FastAPI reported `ready` with application, PostgreSQL, Qdrant, and Ollama all `ok`. The API container reached native Ollama through `http://host.docker.internal:11434`, received its tags endpoint, and used `qwen3.5:4b` for structured generation.

The clean validation used project `esic-phase12-validation`, fresh isolated volumes, and ignored bind directories. It did not alter the existing development volumes. Migration upgraded an empty database to `20260918_01`. Seed created 120 users, 140 devices, 12,065 events, 6 incidents, and 6 scenarios. Ingestion discovered and indexed 7 fictional policy files into 28 chunks. Training selected the baseline Isolation Forest after evaluating two tracked configurations; scenario recall was 0.833333 and false-positive rate was 0.068611 on the synthetic holdout. These are demonstration results, not production performance claims.

The second seed returned `already_seeded` with zero insertion time. The second ingestion skipped all 7 files, created zero chunks, and reported 28 duplicates avoided. Normal application startup does not invoke any bootstrap service.

The anomaly artifact is produced by the explicit trainer into an ignored bind-mounted model directory. It is never silently baked into an image. FastAPI mounts that directory read-only and treats it as a trusted local joblib artifact. The model is intentionally separate from general readiness because event and policy workflows can operate when ML is unavailable.

## Live end-to-end results

An API investigation for U104 returned HTTP 200 in 62.05 seconds. It selected policy search, event search, and anomaly analysis; returned five observed events, one typed ML result with score `0.13168683144477877` and flagged status, three cited policy records, and a grounded synthesis. All tools reported success.

The first browser validation found a real frontend image defect: Streamlit's health endpoint was green while the application could not import the `frontend` package. Setting `PYTHONPATH=/app`, rebuilding only Streamlit, and repeating the browser check fixed it.

A real browser-driven U105 request then followed Browser → Streamlit → FastAPI → LangGraph → PostgreSQL/ML → native Ollama. It returned in 34.56 seconds with `EV012026` from Germany at 10:00 UTC, `EV012027` from Japan at 10:15 UTC, and typed ML score `-0.21107408822812324`. The model reported `Not flagged` while listing elevated country diversity and one country transition. The UI preserved this known impossible-travel limitation and did not overstate detection. That request did not require policy context.

Streamlit generated request ID `68ec5180fd504a4e9a723d17320d7fa3`. API and agent completion events carried the same ID, with two selected tools, three results, five graph steps, and two tool calls. Structured log scans found no submitted request phrase or demo token.

## Failure validation

- Invalid bearer token: HTTP 401 with `Invalid credentials`.
- PostgreSQL stopped: health returned 503 and `postgresql: unavailable`; the same volume restarted healthy.
- Qdrant stopped: health returned 503 and `qdrant: unavailable`; the same volume restarted healthy.
- Ollama pointed at an unavailable host port: health returned 503 and `ollama: unavailable`; an investigation returned HTTP 200 in 0.047 seconds with `routing_failed`, zero tools, and no leaked connection detail.
- Model artifact temporarily absent: the API remained generally ready; the requested ML investigation returned HTTP 200 in 9.03 seconds with typed `dependency_failure`, `insufficient_evidence`, and no fabricated score. The artifact was restored and API returned ready.

No persistent volume was corrupted or deleted during failure checks.

## Resource measurement

One warm `docker stats --no-stream` sample measured approximately:

| Container | Memory |
| --- | ---: |
| FastAPI | 919.5 MiB |
| Streamlit | 133.9 MiB |
| PostgreSQL | 42.0 MiB |
| Qdrant | 166.7 MiB |

Native Ollama and its model are outside these figures. Memory changes with caches and workload; no aggressive limits were imposed.

## Validation

- Full suite: **148 passed, 1 skipped** in 5.97 seconds. The skip is the deliberately opt-in native Ollama test; the live Compose investigations covered native Ollama separately.
- Docker/config focused tests are included in the full suite: container URL/path overrides, bounded database retry success/failure, and fresh frontend request IDs.
- Ruff lint passed; all **109 Python files** passed format checks.
- `pip check`: no broken requirements.
- Alembic check in the isolated PostgreSQL container: no new upgrade operations.
- Compose configuration: valid with required settings and bootstrap profile.
- Images: all application and infrastructure images inspected as Linux arm64; application users are UID/GID 10001.
- Health: all four runtime containers healthy after recovery; API dependencies all `ok`; Streamlit `_stcore/health` returned `ok`.
- Security/config: no privileged containers, Docker socket, added capabilities, embedded credentials, or frontend direct-backend imports. Application root filesystems are read-only and capabilities are dropped.
- Ignore/build-context: `.env`, model artifact, runtime ground truth, and all detailed validation results are ignored. Git whitespace checks passed. Image inspection found none of those private/runtime artifacts.

## Remaining limits and technical debt

The local stack uses demo bearer tokens and loopback HTTP. It has no production identity, TLS, rate limiting, managed secrets, centralized logs, durable metrics, backup/restore workflow, high availability, image signing, vulnerability gate, or deployment threat model. MLflow emits harmless missing-Git metadata warnings in the intentionally minimal trainer image. Embedding model download is cached in an ignored bind directory and the first clean ingestion requires network access. The U105 travel pair remains a demonstrated model miss. Phase 12 measurements are local synthetic development evidence.

## Proposed Phase 13 scope

Phase 13 should add GitHub Actions for pull requests and pushes that installs the pinned Python 3.11 environment, runs Ruff lint and format checks, executes the test suite with mocked Ollama and no private data, validates the Compose configuration, and builds the API and Streamlit images. It should cache dependencies safely, avoid requiring native Ollama or developer volumes, use only synthetic public fixtures, and document branch checks and any architecture limits of the hosted runner. Phase 13 has not started.
