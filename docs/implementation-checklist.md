# Phased implementation checklist

At every phase boundary: inspect changes, run relevant tests and Ruff, verify imports and component startup where available, fix failures, summarize evidence and limitations, and prepare a logical Git checkpoint. Record actual commands/results; never mark an unrun check as passed.

- [x] **0 — Environment and architecture:** inspect hardware, tools, disk, repository; choose architecture and resource strategy; save specification and persistent rules. See `phase-0-architecture.md`.
- [x] **1 — Foundation:** initialize Git, package/settings, dependency pins, venv instructions, ignore rules, example environment, quality tooling, smoke checks.
- [x] **2 — Database and synthetic data:** PostgreSQL schema/migrations, deterministic generator and seed CLI, filtered event/incident reads, DB tests.
- [x] **3 — RAG:** PDF/Markdown/TXT extraction, validation, chunking, deduplication, metadata, local embeddings, Qdrant upsert/retrieval, citations and relevance tests.
- [x] **4 — Local LLM:** provider interface, native Ollama adapter, configurable model, availability and timeout errors, mocked contract tests and local smoke test.
- [x] **5 — FastAPI:** versioned routes, schemas, validation, demo authentication/roles, safe errors, API tests and OpenAPI checks. See `phase-5-checkpoint.md`.
- [x] **6 — LangGraph agent:** typed state, selective evidence routing, approved tools, bounded graph, workflow/failure tests. See `phase-6-checkpoint.md`.
- [x] **7 — ML and MLflow:** leakage-safe daily features, chronological train/holdout evaluation, Isolation Forest persistence/inference, local tracked experiments, synthetic-data caveat. See `phase-7-checkpoint.md`.
- [x] **8 — Integrated analysis:** selective event/anomaly/policy evidence assembly, typed ML evidence, aligned windows, grounded generation, source validation, partial/insufficient paths, and measured multi-tool evaluation. See `phase-8-checkpoint.md`.
- [x] **9 — Streamlit:** working dashboard, copilot, investigation, knowledge, ML, health and audit views. See `phase-9-checkpoint.md`.
- [x] **10 — Evaluation:** representative answerable/unanswerable, investigation, multi-tool and failure cases; measurable retrieval, agent, generation and latency results from actual runs. See `evaluation.md` and `phase-10-checkpoint.md`.
- [x] **11 — Observability:** structured request/tool/retrieval/LLM/inference timing and failures, dependency health, audit review. See `observability.md` and `phase-11-checkpoint.md`.
- [x] **12 — Docker:** arm64-compatible pinned images, Compose startup, persistent volumes, host Ollama access, reproducible smoke test. See `deployment-local.md` and `phase-12-checkpoint.md`.
- [x] **13 — CI:** GitHub Actions lint/tests/build with mocked Ollama and no private services. See `ci.md` and `phase-13-checkpoint.md`.
- [x] **14 — Hardening:** targeted API/agent/grounding/concurrency regressions, dependency failure review, portability fix, full validation, and current/history publication scan. See `phase-14-checkpoint.md`.
- [x] **15 — Documentation and demo:** recruiter-first README, primary architecture diagram, real 3–5 minute demo story, screenshot plan, interview/CV guide, measured results, and clear limitations. See `phase-15-checkpoint.md`.
- [x] **16 — Final audit:** verified the implementation/test/documentation matrix and prominent claims, passed final local and stack gates, scanned current/reachable history, and recorded owner publication actions. See `final-audit.md`.

**Final gate:** All 16 phases are complete. Public release remains an owner action after the author-email privacy decision and optional screenshot capture described in `final-audit.md`.
