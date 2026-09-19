# Phase 9 Streamlit frontend

The Streamlit application is a read-only HTTP client of the local FastAPI API. It does not import or connect to PostgreSQL, Qdrant, Ollama, LangGraph, or the anomaly service. FastAPI remains the single validation, authentication, authorization, audit, orchestration, and dependency boundary.

## Run locally

Start PostgreSQL and Qdrant, native Ollama, and FastAPI as described in the README. Then run:

```bash
ESIC_API_BASE_URL=http://127.0.0.1:8000/api/v1 \
  .venv/bin/streamlit run frontend/app.py --server.address 127.0.0.1
```

Open `http://127.0.0.1:8501`. Enter a local reader or admin demo bearer token in the password field. The token remains in the Streamlit session, is sent only in the `Authorization` header, and is never embedded in source code or written by the application. The default API target is loopback and can be changed with `ESIC_API_BASE_URL`.

With Docker Compose, Streamlit uses `ESIC_API_BASE_URL=http://api:8000/api/v1` on the application network. Its image contains only frontend code and frontend runtime dependencies. The container has no backend bind mounts and is not attached to the backend data network. The browser still opens the loopback URL documented in [local deployment](deployment-local.md).

## Views

- **Dashboard:** coarse dependency readiness, total synthetic event and incident counts, bounded event-type and severity charts, and recent records.
- **Investigation Copilot:** example and free-form requests sent to `POST /investigate`. It keeps observed records, typed ML output, fictional policy context, LLM interpretation, recommendations, sources, and sufficiency visibly separate.
- **Security Events:** bounded filters, pagination, and record details from the simulated SIEM routes.
- **Knowledge Base:** evidence-only policy retrieval with document, section, source, page, chunk, and relevance metadata.
- **ML Analytics:** typed anomaly evidence through the investigation API, including the exact score, flag, window, features, observations, model version, provenance, and synthetic-data warning.
- **System Health:** public coarse dependency status plus admin-only process counters and latency summaries from FastAPI.
- **Audit / About:** an admin-only bounded safe audit view plus architecture and demonstration limitations.

The investigation call is intentionally non-streaming and uses a 210-second client timeout because local LangGraph and Ollama runs measured about 29 seconds in Phase 8. Other calls use 15 seconds. The client maps timeouts, connection failures, invalid JSON, 401, 403, 404, 422, and 503 responses to short messages without exposing backend response details.

## Trust and display boundaries

All records and policy excerpts displayed by Streamlit are untrusted API data. They are rendered with Streamlit text, data, metric, chart, JSON, and caption components; unsafe HTML rendering is not enabled. Display helpers remove control characters and bound long text. The frontend does not infer citations, anomaly flags, or evidence sufficiency. It renders the typed values returned by FastAPI.

The dashboard charts use only the latest bounded sample of up to 100 events. They are descriptive views of synthetic data, not operational monitoring. The model score is not a probability, the flag is not proof of attack, and the application is not an enterprise security product.

## Live Phase 9 verification

The UI was exercised against the live local FastAPI service, PostgreSQL, Qdrant, native Ollama `qwen3.5:4b`, and the persisted synthetic anomaly model.

- Streamlit returned HTTP 200 and rendered the seven-page shell in a browser.
- The dashboard showed 12,065 synthetic events, 6 incidents, and ready system status.
- The U105 investigation for 2026-08-31 rendered `EV012026` (Germany at 10:00 UTC) and `EV012027` (Japan at 10:15 UTC), then separately rendered exact anomaly score `-0.21107408822812324`, `Not flagged`, and model version `isolation_forest_daily_v1`.
- Knowledge retrieval for `remote access MFA` rendered five cited results; the top result was the fictional Remote Access Policy with relevance `0.875`.
- U999 returned no sources and an explicit `insufficient_evidence` warning.
- A reader token was denied the audit view; an admin token received a bounded safe projection without internal audit details.
- An invalid token produced a safe authentication warning. With FastAPI stopped, Dashboard and System Health displayed the same actionable unavailable message without a Streamlit exception. FastAPI was then restarted and returned ready.

Detailed live outputs are retained only under ignored `work/` files. They are development evidence rather than a Phase 10 evaluation dataset.

## Live Phase 12 container verification

The first browser load found and fixed a container path defect that had left Streamlit's health endpoint green while application import failed. The image now explicitly sets `/app` as its Python import root. After rebuilding, the browser rendered the dashboard through the containerized FastAPI service and showed 12,065 events, 6 incidents, and ready health.

A browser-driven U105 request traveled from Streamlit to FastAPI with generated request ID `68ec5180fd504a4e9a723d17320d7fa3`. It completed in 34.56 seconds, rendered events `EV012026` and `EV012027`, exact model score `-0.21107408822812324`, model version `isolation_forest_daily_v1`, model provenance, and sufficient evidence. The UI also displayed `Not flagged`, preserving the known impossible-travel limitation rather than treating country diversity as proof of an attack.
