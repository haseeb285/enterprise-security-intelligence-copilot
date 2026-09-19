# Phase 9 checkpoint — Streamlit frontend

**Scope:** Phase 9 only. Added the Streamlit client and the minimum safe audit read required by its admin view. No Phase 10 evaluation framework, observability expansion, deployment, cloud service, autonomous remediation, or write-capable tool was added.

> All events, policies, incidents, and model results are synthetic demonstration data. The anomaly score is not a probability, and a model flag is not proof of attack or compromise.

## Implementation

- Added a seven-view Streamlit application: Dashboard, Investigation Copilot, Security Events, Knowledge Base, ML Analytics, System Health, and Audit / About.
- Added a reusable typed `httpx` client with validated base URLs, bearer headers, bounded timeouts, strict Pydantic response parsing, safe error mapping, and no direct dependency access.
- Preserved the Phase 8 response boundary: observed evidence, typed ML output, fictional policy context, LLM interpretation, recommendations, sources, execution metadata, and sufficiency remain separate.
- Added bounded filtering and pagination for events, evidence-only policy retrieval, typed feature rendering, dependency health, and an admin audit table.
- Added `GET /api/v1/audit`, an admin-only bounded newest-first projection. It omits the internal `details` column and audits successful reads.
- Added focused API-client, presentation-helper, Streamlit smoke, audit authorization, OpenAPI, and safe-projection tests.
- Pinned Streamlit `1.64.0`, added frontend package discovery, and recorded its transitive environment packages in the lock file.

## Live validation

Streamlit and FastAPI ran on loopback while PostgreSQL and Qdrant were healthy Compose services and native Ollama served `qwen3.5:4b`.

| Check | Measured result |
| --- | --- |
| Streamlit load | HTTP 200; seven-page navigation rendered in a browser |
| Dashboard | 12,065 synthetic events; 6 incidents; system ready |
| Real investigation | Streamlit → FastAPI → LangGraph completed without a UI exception |
| Observed U105 evidence | `EV012026` Germany 10:00 UTC and `EV012027` Japan 10:15 UTC |
| Typed U105 ML evidence | score `-0.21107408822812324`; not flagged; `isolation_forest_daily_v1` |
| Policy retrieval | 5 cited results for `remote access MFA`; top relevance `0.875` |
| Insufficient evidence | U999 showed no sources and `insufficient_evidence` |
| Authorization | reader denied audit; admin received bounded safe records |
| Invalid authentication | safe missing/invalid-token warning; no exception |
| Health | application, PostgreSQL, Qdrant, and Ollama ready |
| Backend unavailable | Dashboard and Health showed an actionable safe error; no exception |
| Direct backend access | none; frontend uses FastAPI HTTP routes only |

The impossible-travel demonstration intentionally exposes disagreement rather than hiding it: two successful logins appear fifteen minutes apart in Germany and Japan, while the daily aggregate Isolation Forest does not flag the user. The UI presents both facts and the model limitation.

## Final validation

- Full project suite: **119 passed, 1 skipped** in 4.26 seconds. The skipped native Ollama contract remains deliberately opt in. The only warning is the known upstream Starlette reference to AnyIO's deprecated `BlockingPortal` alias.
- The suite includes selective routing, execution bounds, provenance/citation, prompt-injection, typed ML, API, authorization, and frontend client/presentation coverage. The Phase 9 frontend module contributed **13 passing tests**.
- Ruff lint passed; all **94 Python files** passed the format check. Python byte compilation and diff whitespace checks passed.
- `pip check` reported no broken requirements. Alembic reported no new upgrade operations.
- Docker Compose configuration validated. PostgreSQL `17.11-bookworm` and Qdrant `1.19.1` were healthy; native Ollama listed `qwen3.5:4b` at 3.4 GB.
- Live FastAPI health returned HTTP 200 `ready` with application, PostgreSQL, Qdrant, and Ollama all `ok`; Streamlit returned HTTP 200.
- Live OpenAPI exposed the bearer-protected audit route. No token returned 401, reader returned 403, and admin returned 200 with no internal details field.
- The tracked-file credential/private-key scan was clean. `.env`, `work/`, `models/`, and `data/private/` paths were confirmed ignored; the lock file contains no absolute local path.

## Limits and Phase 10 proposal

Streamlit keeps its bearer token in session memory, but demo bearer authentication remains unsuitable for deployment. Investigations are non-streaming and can take about 29 seconds on the measured local system. Dashboard distributions use a bounded 100-record sample. The frontend depends on application-owned typed responses and cannot recover evidence when FastAPI is unavailable. Browser rendering and live checks cover one local configuration and are not broad usability or load tests.

The exact proposed Phase 10 scope is a representative evaluation framework for answerable and unanswerable policy questions, security investigations, multi-tool and failure cases, with measured retrieval, generation, agent, and latency results from actual runs. Phase 10 has not started.
