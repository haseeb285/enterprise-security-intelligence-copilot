# Phase 6 checkpoint — bounded LangGraph agent

**Scope:** Phase 6 only. Added a typed, bounded LangGraph investigation workflow over the existing policy retrieval and simulated SIEM services, an authenticated API route, live development evaluation, tests, and documentation. No ML model, MLflow tracking, UI, autonomous remediation, or Phase 7 work was added.

## Implemented

- LangGraph **1.2.11** with five fixed nodes: `route`, `tools`, `assess`, `synthesize`, and `finalize`. Typed state carries request, role, validated tool decisions, evidence, safe outcomes, sufficiency, counters, and the final response.
- Five allowlisted read-only tools backed by the Phase 2/3 service layer: `search_policy`, `search_security_events`, `get_user_events`, exact `get_event` for `EV######`, and admin-only `get_incident`.
- Model routing returns tool names only. Application code derives strict IDs, event type, and optional ISO timestamps from the request, adds explicitly requested sources omitted by the model, rejects ambiguous identifiers, and validates arguments with Pydantic.
- Hard limits: five graph steps, three tool calls, five event results per event tool, three policy chunks, no retries, and LangGraph recursion limit eight. Missing, forbidden, rejected, or failed required evidence produces an insufficient or explicit failure outcome without synthesis.
- Provenance remains application owned. Observed records retain PostgreSQL event/incident IDs or Qdrant chunk IDs and citation metadata; `sources` is rebuilt from those records. Policy context is a separate field. A generated `EV`, `INC`, or `U` identifier absent from source metadata rejects synthesis.
- Retrieved content is untrusted prompt data. Obvious embedded instruction lines are masked for synthesis, source text remains visible as observed evidence, system-changing recommendations are removed, and known overclaim or unsupported absence patterns are replaced with conservative application text.
- `POST /api/v1/investigate` accepts a 1–4,000 character request under Phase 5 demo bearer authentication. Readers can use policy/event tools; incident lookup enforces admin. Audit rows contain role, selected tools, safe per-tool outcomes, counters, and overall outcome, without request text, evidence, bearer tokens, or hidden reasoning.

## Measured local evaluation

Environment: Apple M3 with 16 GB unified memory, Python 3.11, native Ollama **0.34.2** with only `qwen3.5:4b` installed (4.7B, Q4_K_M), Docker Compose PostgreSQL **17.11** and Qdrant **1.19.1** on loopback. The dataset and policies are fictional and synthetic.

The final complete development run used all 18 cases in `evaluation/agent_cases.json`: three policy, four event search/detail, two incident, four multi-source, four unknown/no-answer, and one ambiguous request. Detailed outputs remain in ignored `work/phase6-agent-evaluation.json`.

| Measure | Actual result |
| --- | ---: |
| Requests | 18 |
| Exact expected tool-set selection | 18/18 |
| Procedural task completion | 18/18 |
| Unnecessary tool calls | 0 |
| Structured calls valid | 31/31 |
| Malformed structured calls | 0 |
| Evaluation failures | 0 |
| Mean end-to-end latency | 19.694 s |
| Median end-to-end latency | 20.860 s |

All five unknown/ambiguous cases returned insufficient evidence. Exact known event `EV000001` selected only `get_event` and returned that source; unknown `EV999999` selected only `get_event` and returned insufficient evidence.

Manual review verified that response `sources` exactly matched observed source IDs, `policy_context` contained only retrieved policy records, no system-changing recommendation survived, and insufficient cases exposed no fabricated evidence. It also found three unsafe synthesis patterns despite the perfect procedural score: an inference that failed logins were privileged access, an unsupported claim that incident notification had not occurred, and an unsupported claim that bounded user activity showed no policy violation. The synthesis instruction and deterministic filters were tightened. Targeted live reruns of the MFA/events and incident/policy cases completed in **49.703 s** and **24.949 s** with the offending claims removed. A **53.391 s** user-activity rerun exposed the last phrase variant; the final filter matches that captured live output and has a regression test. These findings show why the 18/18 metric is not a groundedness score.

## Final validation

- Full suite: **83 passed, 1 skipped**. The skipped native Ollama test is explicitly opt-in; actual Ollama inference was exercised by the 18-case evaluation, targeted reviews, and final API smoke. One upstream Starlette/AnyIO deprecation warning remains.
- Agent tests: **19 passed**, covering selective routing, exact event lookup, validated inputs, tool/step/result limits, no-answer and dependency failures, role enforcement, malformed/timeout handling, prompt injection, application-owned provenance, invented-ID rejection, policy relevance, unsafe recommendations, and unsupported synthesis patterns.
- Live API smoke: health **200** with application/PostgreSQL/Qdrant/Ollama all `ok`; OpenAPI **3.1.0** with eight paths; exact-event investigation **200**, selected only `get_event`, outcome `complete`, source `EV000001`.
- PostgreSQL accepted connections; Qdrant `/healthz` passed; Ollama `/api/version` returned 0.34.2 and `/api/tags` listed only `qwen3.5:4b`. PostgreSQL and Qdrant containers were healthy, so no restart was required.
- `ruff check .`, `ruff format --check .`, `pip check`, `alembic check`, `alembic current`, `alembic heads`, and `docker compose config --quiet` passed. Alembic is at `20260918_01 (head)` with no new operations.
- OpenAPI generation, repository whitespace checks, tracked-secret/private-data checks, and ignored runtime/private path checks passed before the checkpoint commit.

## Limits and next gate

This is a local demonstration, not a production security agent. Expected evaluation routes were hand-authored against the same synthetic system. Procedural completion checks response shape, evidence presence, routing, and safe no-answer behavior; it does not measure answer correctness or semantic groundedness. Regex safeguards cover known failures but cannot prove prompt-injection resistance or factuality. The policy subject gate can reject valid paraphrases, result limits can omit relevant history, and CPU latency is high. Demo bearer tokens are not enterprise SSO, and audit storage is not tamper resistant.

Phase 7, if approved, is the synthetic-data ML and MLflow phase: leakage-safe features, chronological train/holdout evaluation, artifact persistence, inference, experiment tracking, tests, and explicit synthetic-data limits. Phase 7 was not started here.
