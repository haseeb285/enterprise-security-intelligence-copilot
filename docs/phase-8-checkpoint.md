# Phase 8 checkpoint — integrated evidence analysis

**Scope:** Phase 8 only. Integrated the existing Phase 7 anomaly service into the Phase 6 LangGraph and existing investigation endpoint. No Streamlit, broad Phase 10 evaluation framework, deployment, cloud service, autonomous remediation, or write-capable tool was added.

> All events and model results are synthetic demonstration data. The anomaly score is not a probability, and a model flag is not proof of attack or compromise.

## Implementation

- Added allowlisted read-only `analyze_user_anomaly`, a thin adapter over `AnomalyDetectionService`. It returns typed entity/window, exact score and flag, all feature values, contributing observations, model version, statement, and provenance.
- Preserved `search_policy`, `search_security_events`, `get_user_events`, `get_event`, and `get_incident`. Routing invokes ML only for explicit anomaly, unusual-behavior, ML, or suspicious-activity requests. Anomaly-score requests use ML only; ordinary failed-login and policy requests do not gain unnecessary tools.
- Added request-derived temporal windows. A date means its UTC day; one timestamp means the preceding 24 hours; two timestamps mean an ordered `[start,end)` range. Without a time, ML uses the user's latest active UTC day. Combined event/ML requests use the same window.
- Reduced the inference service availability threshold from three events to two so it can score the existing two-event impossible-travel observation. This does not alter the model, feature schema, artifact, training, or Phase 7 holdout results.
- Split graph state and API output into observed event/incident evidence, typed ML analysis, fictional policy context, LLM interpretation, and advisory recommendations. Event records now preserve structured timestamps, country, device, IP, status, type, user, and incident provenance.
- Partial evidence reaches synthesis when one selected dependency fails. ML error outcomes distinguish unknown entity, insufficient history, invalid window, dependency failure, and inference failure. Missing ML is stated explicitly while valid event or policy evidence remains.
- Added application guards for generated identifiers, exact score references, policy-violation claims without policy, anomaly claims without ML, unsupported absence/certainty, and write-action recommendations. Retrieved text stays untrusted and injection lines are masked in the synthesis copy.
- Extended the existing `POST /api/v1/investigate` response schema with `ml_analysis`; no parallel API was added. `ML_MODEL_PATH` configures the ignored trusted artifact.

## Measured integrated evaluation

The 20 cases in `evaluation/integrated_agent_cases.json` cover event only, policy only, ML only, event+ML, event+policy, all three sources, unknown user, insufficient history, no policy, missing model, impossible travel, retrieved prompt injection, invalid time, and an ambiguous request. Normal cases used live PostgreSQL, Qdrant, the persisted anomaly artifact, and native Ollama `qwen3.5:4b`. The missing-model and malicious-policy cases are explicit evaluation fixtures.

Command:

```bash
.venv/bin/python -m app.agent.evaluate_integrated
```

Two corrected cases were rerun with `--case-id ... --merge`; successful prior cases were retained rather than repeated.

| Metric | Measured result |
| --- | ---: |
| Cases completed | 20/20 |
| Expected tool sets | 20/20 |
| Unnecessary tool calls | 0 |
| Provenance fidelity | 20/20 |
| Policy citation fidelity | 20/20 |
| Exact anomaly score/flag fidelity | 20/20 |
| Valid structured calls | 35 |
| Malformed structured calls | 0 |
| Evaluation failures | 0 |
| Mean latency | 28.564 seconds |
| Median latency | 29.157 seconds |

The ignored detailed result is `work/phase8-integrated-evaluation.json`. Metrics describe one local deterministic synthetic development set and do not establish real-world detection or general prompt-injection performance.

## Impossible-travel disagreement

For U105 on 2026-08-31, observed records `EV012026` and `EV012027` show successful logins from Germany and Japan fifteen minutes apart. The typed ML result reports exact score `-0.21107408822812324`, `flagged_anomalous=false`, two events, two countries, and one country transition. The completed response exposes both facts and says the model did not determine an attack. No rule or model change was added to force a detection.

## Failure and grounding review

- Missing model: event evidence remained, outcome was `partial_evidence`, sufficiency was false, and the interpretation said the local model dependency failed.
- Unknown user and insufficient history: no ML status was claimed and the result was `insufficient_evidence`.
- No relevant policy: no violation was claimed.
- Retrieved prompt injection: the malicious instruction line remained visible in returned policy context for audit but was replaced with `[untrusted instruction removed]` before synthesis.
- Inexact generated score: the prose reference was removed while the exact application-owned `ml_analysis.anomaly_score` remained.
- Write actions: account, password, firewall, process, permission, record-deletion, and similar system changes have no tool, and matching recommendations are filtered.

## Validation

- Full deterministic project suite: **104 passed, 1 skipped**, with the native Ollama test deliberately opt in and one upstream Starlette/AnyIO deprecation warning.
- New Phase 8 integrated contract tests: **13 collected**. Phase 6/8 agent tests: **32 passed** after the final score, partial-failure, and default-window guards. ML, agent, API, and integrated groups total **57 tests**.
- Live representative inference: U105 score `-0.21107408822812324`, flag false, two events; U106 score `0.11672999155466501`, flag true, thirteen events.
- Ruff lint and format passed.
- PostgreSQL and Qdrant Compose containers were healthy; native Ollama reported configured `qwen3.5:4b`; the Qdrant health endpoint passed.
- Live FastAPI health returned `200 ready` with PostgreSQL, Qdrant, Ollama, and application all `ok`. OpenAPI contained the authenticated investigation route, `ml_analysis`, and `MLEvidence` schema.
- `pip check` reported no broken requirements. `alembic check` found no new upgrade operations. Docker Compose configuration validated.
- The tracked-file secret/private-data scan was clean. `.env`, the model artifact, evaluation output, and runtime ground truth were confirmed ignored.

## Limits and Phase 9 proposal

The router uses deterministic English cue patterns around a structured LLM proposal, so novel paraphrases may be conservatively rejected. The LLM can still produce weak prose even though typed evidence and deterministic guards preserve claims and provenance. Daily aggregate ML loses sequence semantics, has a high Phase 7 holdout false-positive rate, and misses impossible travel. A joblib artifact must be locally trusted. Evaluation fixtures test one direct injection pattern and one missing-model path; they do not prove broad security.

The exact proposed Phase 9 scope is a Streamlit client over existing APIs with dashboard, copilot investigation, cited knowledge, ML evidence, dependency health, and audit views. It should preserve the typed categories, demo authentication, read-only behavior, and local resource budget. Phase 9 has not started.
