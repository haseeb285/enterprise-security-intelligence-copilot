# Phase 11 observability

The application uses low overhead process local observability. It does not add Prometheus, a log collector, or another always on service. Operational telemetry remains separate from the PostgreSQL audit trail.

## Correlation and structured logs

FastAPI accepts `X-Request-ID` values containing 1 to 64 letters, digits, `.`, `_`, or `-`. It generates a random 32 character hexadecimal identifier when the header is absent or unsafe, returns the identifier on every response, and places it in a context variable used by downstream components.

The `esic.observability` logger writes one compact JSON object per event. Its API completion event replaces Uvicorn's duplicate access line. Events cover dependency health, investigations, approved tool calls, retrieval, anomaly inference, Ollama inference, and safe dependency failures. Common fields include component, event, request ID, outcome, duration, and a stable error category. Component fields are an explicit allowlist. Arbitrary dictionaries, prompts, requests, evidence, generated prose, bearer tokens, connection strings, paths, and exception messages cannot be passed through the structured event helper.

Stable categories are validation, authentication, authorization, PostgreSQL unavailable, vector store unavailable, LLM unavailable, LLM timeout, LLM validation, model artifact unavailable, insufficient observation, tool failure, and internal error. Client responses remain coarse and do not expose these logs or dependency exception details.

## Process metrics

`OperationalMetrics` keeps thread safe counters and count, mean, minimum, and maximum latency summaries in memory. It tracks:

- API requests and failures
- investigations and failures
- retrieval calls and insufficient results
- LLM calls, failures, timeouts, and output tokens in logs when Ollama supplies them
- anomaly inference calls and failures
- calls, failures, and latency for the six allowlisted tools
- PostgreSQL, Qdrant, Ollama, and model artifact dependency failures

Labels are fixed sets, so request values cannot create unbounded cardinality. Metrics reset on API process restart and are not a durable audit record.

`GET /api/v1/metrics` returns the aggregate snapshot to the admin demo role. It contains no request IDs, synthetic entity IDs, content, paths, configuration, prompts, or evidence. Reading metrics creates one normal `api_get_metrics` audit entry. Internal telemetry events do not create audit entries.

## Live validation

On 2026-09-19, PostgreSQL and Qdrant containers were healthy and native Ollama listed `qwen3.5:4b` (4.7B, Q4_K_M). A live three source investigation used request ID `phase11-investigation-002` and selected policy search, synthetic event search, and anomaly analysis. It returned HTTP 200 `complete`, five event records, one typed ML result, and three cited policy records in 23.91 seconds.

The correlated log contained API, agent, tool, retrieval, ML, and LLM events. In process summaries measured API 23,901.547 ms, agent 23,878.629 ms, retrieval 41.848 ms, ML 35.659 ms, and two LLM calls with mean 6,501.301 ms. Tool means were 10,813.324 ms for the first policy search including lazy embedding model load, 20.934 ms for event search, and 35.737 ms for anomaly analysis. These are one local warm-model demonstration, not performance claims.

A log scan found none of the investigation request phrase, policy phrase, admin token, or reader token. Metrics access returned 401 without a token, 403 for the reader role, and 200 for admin. Streamlit returned HTTP 200 with a healthy `_stcore/health` endpoint, and its System Health view has an automated render check for the admin metrics summary.

A seven run microbenchmark of 10,000 counter, timer, and safe event construction operations measured median 0.001942 ms per operation (range 0.001918–0.002047 ms) with the log sink disabled. This isolates in process bookkeeping and excludes application work and log I/O.

## Operation

Use the normal API start command. `LOG_LEVEL` controls the structured logger level. Inspect JSON locally with a tool such as `jq`; do not redirect logs into the repository. Detailed Phase 11 validation artifacts are retained only under ignored `work/`.

Health and metrics are diagnostic aids. The local logger and in memory registry do not provide durable storage, alerting, distributed tracing, tamper resistance, retention, or production monitoring.
