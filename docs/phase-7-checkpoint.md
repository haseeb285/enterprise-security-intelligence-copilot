# Phase 7 checkpoint — synthetic anomaly detection and MLflow

**Scope:** Phase 7 only. Added leakage-safe feature engineering, chronological Isolation Forest training, persisted preprocessing/model state, independent inference, separate ground-truth evaluation, local MLflow tracking, tests, and documentation. The model was not added to LangGraph or an API route; that integration belongs to Phase 8.

> This model is trained and evaluated on synthetic demonstration data and is not a production security detection engine.

## Implementation

- Observation: one active user or userless source IP in one non-overlapping UTC calendar day.
- Twenty causal numeric features cover activity volume, login success/failure, source/country/device diversity, unusual hours, privileged activity, network/endpoint/privilege events, generalized non-authentication activity, chronological country transitions, active hours, and maximum 15-minute frequency.
- Scenario IDs/types, labels, reasons, incident fields, descriptions, audit data, post-window events, and severity are excluded. Both unsupervised models fit before the ignored scenario truth is loaded.
- Training period `[2026-08-03, 2026-08-24)` has 1,747 active observations. Holdout `[2026-08-24, 2026-09-01)` has 589. No random split is used.
- Selected scikit-learn 1.9.1 pipeline: median imputer and Isolation Forest with 200 trees, contamination 0.02, `max_samples=auto`, `random_state=42`, and one job. A 300-tree, contamination 0.01 sensitivity run is logged separately. Baseline selection was fixed before ground-truth review.
- The ignored 1,980,441-byte `isolation_forest_daily_v1.joblib` bundle contains preprocessing, model, exact schema, training metadata, and feature references. Load-time compatibility checks reject missing, corrupt, or mismatched artifacts.
- `AnomalyDetectionService` is independent of LangGraph and FastAPI. It validates a user and aware window up to 24 hours, requires three events, loads the trusted local artifact, and returns a behavioral score, model flag, observed feature values, non-causal feature signals, and model version.

## Measured evaluation

The clean reproducible command was `MLFLOW_DISABLE_AGENT_HINT=1 .venv/bin/python -m app.ml.train --clean` against the deterministic PostgreSQL seed and separately stored `data/runtime/ground_truth.json`.

| Result | Baseline, selected | Sensitivity check |
| --- | ---: | ---: |
| Scenario recall | 5/6 (83.33%) | 5/6 (83.33%) |
| False positives / normal holdout | 40/583 | 21/583 |
| False-positive rate | 6.86% | 3.60% |
| Flagged precision | 5/45 (11.11%) | 5/26 (19.23%) |
| Top-5 scenario capture | 2/6 | 2/6 |
| Top-10 scenario capture | 4/6 | 3/6 |
| Mean scenario score | 0.0376583 | 0.0172142 |
| Mean normal score | -0.1630316 | -0.1830538 |

The selected baseline ranked brute force 1st, account compromise 3rd, privileged activity 8th, firewall burst 10th, and suspicious endpoint behavior 21st. Impossible travel was missed and ranked 325th with score -0.2110741. The failure is documented without further tuning against the six scenarios.

The selected-artifact inference smoke for U104 over August 31 reloaded the persisted bundle, returned score 0.1316868 and `flagged_anomalous=true`, and identified elevated failed-login, unusual-hour, and short-window activity. It described a behavioral anomaly rather than an attack.

## MLflow

MLflow 3.16.1 uses ignored SQLite `work/mlflow.db` and local `work/mlartifacts/`. Clean-run IDs:

- Baseline: `8d3852e9157c42b282d92e6a59dd3519`, status `FINISHED`.
- Sensitivity: `91ba1fe86e06425f903e83797af8d7ed`, status `FINISHED`.

Both runs were read back through `MlflowClient`; each contains parameters, feature/split configuration, metrics, model joblib, evaluation JSON, and model metadata JSON. MLflow 3.11.0 was reported as yanked by PyPI during dependency setup and was stopped before installation; the non-yanked 3.16.1 release is pinned.

## Validation

- ML tests: **8 passed**, covering deterministic and causal features, no future events, forbidden leakage fields, chronological split, pipeline persistence consistency, artifact failures, inference and error paths, separate truth evaluation, and a real temporary SQLite MLflow run.
- Full project suite: **91 passed, 1 skipped**. The native Ollama test remains explicitly opt-in; one upstream Starlette/AnyIO deprecation warning remains.
- Existing Phase 6 agent tests: **19 passed**.
- Ruff lint/format and `pip check` passed. PostgreSQL, Qdrant, Ollama, Alembic, Compose, Git/private-data, and ignored-artifact checks passed at the phase gate.

## Limits and next gate

The six scenario cases are a small, deterministic development set generated in the same repository. Active-only daily observations omit inactivity and lose fine sequence structure. A single global model does not learn personal baselines. The score is not calibrated probability or causal evidence. The baseline's 6.86% holdout false-positive rate is high, and impossible travel is missed. The service loads joblib only from a trusted local path. SQLite MLflow is suitable for this single-user demo, not concurrent production tracking.

Phase 8, if approved, is integrated analysis: add the anomaly service as a bounded read-only LangGraph tool, assemble event/anomaly/policy evidence, preserve typed provenance and separate observed/model/LLM fields, enforce insufficient-evidence and failure behavior, expose the integrated contract through the API, and evaluate multi-tool grounding. Phase 8 was not started here.
