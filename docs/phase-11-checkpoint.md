# Phase 11 checkpoint — observability

**Scope:** Phase 11 only. Added request correlation, content-safe structured operational logging, bounded process-local metrics, an admin metrics API and System Health summary, failure categories, tests, and documentation. No Docker, CI, Phase 12 work, monitoring service, write-capable action, model change, or evaluation tuning was added.

## Implementation

- Added validated/generated `X-Request-ID` propagation across FastAPI, agent, tools, retrieval, ML, and Ollama.
- Added compact JSON events with explicit safe fields and stable error categories. Prompts, requests, evidence, outputs, credentials, exception details, and paths are excluded.
- Added thread safe fixed-cardinality counters plus count/mean/min/max latency summaries for API, investigation, retrieval, LLM, ML, and approved tools.
- Added safe dependency failure counters and structured health events for PostgreSQL, Qdrant, Ollama, and the model artifact.
- Added admin-only `GET /api/v1/metrics`, a typed frontend client method, and a compact System Health metrics section.
- Kept operational telemetry separate from the existing audit trail; only the explicit admin metrics read creates an audit action.

## Measured live result

PostgreSQL and Qdrant were healthy, native Ollama listed `qwen3.5:4b`, FastAPI reported all dependencies ready, and Streamlit returned HTTP 200 with a healthy internal health endpoint.

The live request `phase11-investigation-002` completed in 23.91 seconds with policy, synthetic event, and ML evidence. Correlated JSON events covered API, agent, all three tools, retrieval, ML, and two LLM calls. The process snapshot measured API 23,901.547 ms, agent 23,878.629 ms, retrieval 41.848 ms, ML 35.659 ms, and mean LLM 6,501.301 ms. The first policy tool took 10,813.324 ms because it included lazy embedding model load. A scan found no request phrase, policy phrase, or demo token in the logs.

The metrics route returned 401 unauthenticated, 403 for reader, and 200 for admin. A seven-run, 10,000-iteration instrumentation microbenchmark measured median 0.001942 ms per counter, timer, and safe event construction operation with log output disabled; it excludes application work and log I/O.

## Validation

- Full project suite: **144 passed, 1 skipped** in 4.40 seconds. The skip is the deliberately opt-in native Ollama test; the warning is the known upstream Starlette reference to AnyIO's deprecated `BlockingPortal` alias.
- Focused observability/API/frontend regression: **40 passed**. The broader component regression covering observability, LLM, RAG, ML, agent, API, and frontend passed before the final two focused metric tests were added; the final full suite above is authoritative.
- Phase 10 offline regression completed: 47 retrieval cases, deterministic repeat match, 13/13 safety contracts, six fact checks, and the unchanged U105 impossible-travel regression passed.
- Ruff lint passed; all **107 Python files** passed format checks. Python compilation and Git whitespace checks passed.
- `pip check` reported no broken requirements. Alembic reported no new upgrade operations. Docker Compose configuration validated.
- PostgreSQL and Qdrant containers were healthy. FastAPI returned ready with PostgreSQL, Qdrant, and Ollama `ok`; native Ollama listed `qwen3.5:4b`. OpenAPI included the admin bearer requirement for `/api/v1/metrics`.
- Streamlit returned HTTP 200 and `_stcore/health` returned `ok`; its admin metrics render test passed.
- `.env`, detailed live logs/results, the overhead result, and the model artifact were confirmed ignored. Diff secret/private-key and local-path scans were clean; test-only private marker strings remain intentional redaction fixtures.

Detailed runtime files remain under ignored `work/`.

## Limits

Metrics are process-local aggregates and reset on restart. Logs write to the local process stream. There is no durable storage, distributed tracing, alerting, retention, dashboard server, centralized collection, or tamper resistance. The one live timing is development evidence on a local synthetic workflow, not a production benchmark.

Phase 12 has not started.
