# Local demonstration deployment with Docker Compose

This is a **local demonstration deployment** for an Apple silicon Mac with 16 GB unified memory. It is not a production deployment. Docker Compose runs PostgreSQL, Qdrant, FastAPI, and Streamlit. Ollama stays native on macOS so `qwen3.5:4b` can use Apple acceleration.

```text
Browser -> Streamlit container -> FastAPI container
                                  |-> PostgreSQL container
                                  |-> Qdrant container
                                  `-> host.docker.internal:11434 -> native Ollama
```

Streamlit is attached only to the application network and calls FastAPI over HTTP. PostgreSQL and Qdrant use the backend network. FastAPI joins both networks. No container is privileged, no Docker socket is mounted, and the application containers run as UID/GID 10001 with all capabilities dropped and read-only root filesystems.

## Prerequisites

- Apple silicon macOS; Phase 12 was validated on arm64.
- Docker Desktop with Compose v2.
- Native Ollama listening on port 11434 with `qwen3.5:4b` installed.
- At least two distinct random demo tokens of 24 characters or more.

Install and start the official Ollama macOS application, then pull the configured model:

```bash
ollama pull qwen3.5:4b
curl --fail http://127.0.0.1:11434/api/tags
```

## Configure

Copy the example and edit the ignored local file:

```bash
cp .env.example .env
```

Set `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DEMO_API_TOKEN`, and `DEMO_READ_TOKEN`. The two demo tokens must be distinct. Compose supplies container-specific service URLs: PostgreSQL uses `postgres`, Qdrant uses `qdrant`, FastAPI uses `host.docker.internal` for Ollama, and Streamlit uses `api`. Host-native development continues to use the loopback defaults in application settings.

`COMPOSE_OLLAMA_BASE_URL` changes the host Ollama address without source edits. `MODEL_BIND_PATH`, `HF_CACHE_BIND_PATH`, `RUNTIME_BIND_PATH`, and `TRAINING_WORK_BIND_PATH` change local bind paths. These paths should remain under ignored local directories.

## Build and bootstrap from empty volumes

The bootstrap is explicit. Normal startup never resets PostgreSQL, Qdrant, or the model artifact.

```bash
make docker-build
make docker-infra
make docker-migrate
make docker-seed
make docker-ingest
make docker-train
make docker-up
```

The equivalent build command is:

```bash
docker compose --profile bootstrap build api streamlit train
```

The one-off `migrate`, `seed`, `ingest`, and `train` services are behind the `bootstrap` profile. `seed` is deterministic and idempotent. `ingest` embeds only the public fictional corpus under `data/policies/synthetic`, uses content hashes to skip unchanged inputs, and prunes stale chunks. The normal API and Streamlit startup does not re-seed, re-embed, or retrain.

The trainer writes `models/anomaly/isolation_forest_daily_v1.joblib` through a bind mount. The runtime image never contains the untracked joblib artifact and mounts the model directory read-only. Loading joblib assumes a trusted local artifact. A missing artifact yields a typed dependency failure and insufficient evidence; it does not fabricate or download a model.

Open Streamlit at <http://127.0.0.1:8501>. FastAPI health is at <http://127.0.0.1:8000/api/v1/health>. Enter a configured demo token in Streamlit.

## Operations

```bash
make docker-logs
make docker-down
```

`make docker-down` keeps named volumes. `make docker-clean-demo` is deliberately destructive and removes this Compose project's PostgreSQL and Qdrant volumes. Review the active Compose project before running it.

PostgreSQL and Qdrant persist in `postgres_data` and `qdrant_data`. Their health checks run locally inside each container. The FastAPI readiness check calls only the existing lightweight dependency health route; it does not generate LLM output. Streamlit uses `/_stcore/health`.

Phase 11 JSON logs write to container standard output and error. Each Streamlit client request supplies a fresh safe request ID, which FastAPI propagates through the agent and approved tools. Prompts, evidence, generated text, tokens, connection strings, and exception details remain excluded from structured operational events.

## Clean-state validation result

On 2026-09-19, an isolated Compose project with new PostgreSQL and Qdrant volumes completed migration, deterministic seed, policy ingestion, model training, API startup, Streamlit startup, and two live investigations. The seed created 120 users, 140 devices, 12,065 events, 6 incidents, and 6 scenarios. Policy bootstrap discovered and ingested 7 fictional files into 28 chunks. A repeat returned `already_seeded`, skipped all 7 unchanged policy files, and avoided 28 duplicate chunks.

The U104 API investigation returned HTTP 200 in 62.05 seconds with five observed events, one typed ML result, three policy citations, and a grounded LLM synthesis. A browser-driven U105 request through Streamlit returned in 34.56 seconds with two cross-country login events and typed ML output. It correctly showed the known limitation: the anomaly model did not flag the impossible-travel pair.

Measured warm running memory was approximately 920 MiB for API, 134 MiB for Streamlit, 42 MiB for PostgreSQL, and 167 MiB for Qdrant. Native Ollama memory is outside these container figures. Memory varies with model cache and workload.

## Failure behavior and limits

- Invalid demo authentication returns 401.
- PostgreSQL or Qdrant loss makes health return 503 with the unavailable dependency named coarsely.
- Unreachable Ollama makes health return 503 and an investigation returns `routing_failed` without leaking connection details.
- A missing anomaly artifact returns a typed ML `dependency_failure` and `insufficient_evidence`.

The model artifact is not part of general health readiness because policy and event workflows can still operate without ML. Investigation results report the ML failure explicitly when that tool is requested.

This setup has demo bearer tokens, loopback HTTP, local volumes, process-local metrics, and native host Ollama. It has no TLS, enterprise identity, managed secret store, rate limiting, centralized logs, durable metrics, backups, high availability, supply-chain signing, or deployment threat model. Those are required before any production use.
