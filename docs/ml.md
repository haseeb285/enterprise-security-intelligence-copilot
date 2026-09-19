# Synthetic behavioral anomaly model

> This model is trained and evaluated on synthetic demonstration data and is not a production security detection engine.

Phase 7 implements ML independently of LangGraph and the API. It reads the existing simulated SIEM events, creates causal behavioral observations, fits a deterministic Isolation Forest, persists the preprocessing/model bundle, evaluates against the separate ignored scenario file, and logs two small experiments to local MLflow.

## Observation unit and temporal split

The observation unit is an **active entity in one non-overlapping UTC calendar day**. Events with a user become `user:U###` observations. An event without a user becomes a `source_ip:<address>` observation, which lets the same model represent the synthetic firewall burst. Only events with `window_start <= timestamp < window_end` contribute. Empty entity-days are not synthesized.

The fixed development split is chronological:

- Training: `[2026-08-03T00:00:00Z, 2026-08-24T00:00:00Z)`, 1,747 active observations.
- Holdout: `[2026-08-24T00:00:00Z, 2026-09-01T00:00:00Z)`, 589 active observations.

All six injected scenarios occur on August 31 in the holdout. Feature computation uses only events inside each observation window. No random split or future event is used.

## Final feature schema

All 20 features are numeric observations available by the window end:

1. `event_count`
2. `failed_login_count`
3. `successful_login_count`
4. `failed_to_success_ratio`
5. `unique_source_ip_count`
6. `unique_country_count`
7. `unique_device_count`
8. `unusual_hour_event_count`
9. `unusual_hour_fraction`
10. `privileged_event_count`
11. `privileged_event_fraction`
12. `firewall_block_count`
13. `firewall_allow_count`
14. `endpoint_alert_count`
15. `privilege_change_count`
16. `non_auth_event_count`
17. `non_auth_event_fraction`
18. `country_transition_count`
19. `active_hour_count`
20. `max_events_15m`

Unusual hours are before 06:00 or from 22:00 UTC. `max_events_15m` is calculated by a forward scan that sees only the current and prior timestamps. Country transitions follow chronological authentication events. The generalized non-authentication features give endpoint and network activity training variation; event-specific counts remain useful explanatory observations.

## Leakage analysis

The model matrix explicitly excludes scenario IDs/types, anomaly flags, evaluation labels, ground-truth reasons, related-event labels, incident IDs/titles, descriptions, audit rows, and all post-window information. Severity is also excluded because the synthetic generator assigns elevated severity to injected scenarios, making it a risky shortcut in this dataset. Entity ID, raw event IDs, timestamps, and source strings are metadata, not model columns.

`app.ml.features` accepts event records only. `app.ml.train` fits both unsupervised configurations before it loads `data/runtime/ground_truth.json`. Tests assert the final feature names contain none of the forbidden fields and prove that an event after the window does not affect the observation.

## Model, persistence, and scoring

The selected configuration was fixed before ground-truth review:

- scikit-learn `Pipeline`: median `SimpleImputer` then `IsolationForest`
- 200 trees, contamination `0.02`, `max_samples=auto`, `random_state=42`, one job
- model version `isolation_forest_daily_v1`

The sensitivity run uses 300 trees and contamination `0.01`. It is a comparison, not a ground-truth-selected replacement.

The ignored joblib artifact stores the fitted preprocessing pipeline, Isolation Forest, ordered feature schema, training period/count, configuration, library version, model version, and training feature medians/90th percentiles. Loading rejects the wrong artifact type, schema version, model version, or feature order. Joblib files can execute Python during loading, so the service must load only this locally generated trusted artifact.

`anomaly_score` is the negative Isolation Forest decision function, so a larger number is more anomalous. `flagged_anomalous` is the model's `predict == -1` result. Feature signals compare selected observed values with training 90th percentiles; they are contributing observations, not causal explanations. The result says “behavioral anomaly score” and does not claim an attack was detected.

## Measured holdout evaluation

Ground truth maps scenario event IDs to holdout observations only after fitting. Scenario recall counts a scenario when its observation is flagged. A false positive is a flagged holdout observation containing no scenario event. Precision is reported only as the fraction of flagged observations that contain a scenario. Ranking reports how many distinct scenarios appear in the highest-scored observations.

| Configuration | Scenario recall | False positives | False-positive rate | Flagged precision | Top-5 capture | Top-10 capture |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline, selected | 5/6 (83.33%) | 40/583 | 6.86% | 5/45 (11.11%) | 2/6 | 4/6 |
| Sensitivity check | 5/6 (83.33%) | 21/583 | 3.60% | 5/26 (19.23%) | 2/6 | 3/6 |

The baseline ranks brute force 1st, account-compromise pattern 3rd, privileged activity 8th, firewall burst 10th, and suspicious endpoint behavior 21st. It misses impossible travel, ranked 325th. That two-event pattern is not distinct enough under daily aggregate features. This failure is retained rather than tuning against the six-case evaluation set.

## Reproduce training and inspect MLflow

PostgreSQL must contain the deterministic Phase 2 seed and the ignored ground-truth file. Run:

```bash
MLFLOW_DISABLE_AGENT_HINT=1 .venv/bin/python -m app.ml.train --clean
```

`--clean` removes only Phase 7 outputs below ignored `work/` and `models/` paths. The selected artifact is `models/anomaly/isolation_forest_daily_v1.joblib`; detailed results are `work/phase7-evaluation.json`. MLflow 3.16.1 uses `work/mlflow.db` and `work/mlartifacts/`. To inspect the local runs:

```bash
.venv/bin/mlflow server \
  --backend-store-uri sqlite:///work/mlflow.db \
  --default-artifact-root "$(pwd)/work/mlartifacts" \
  --host 127.0.0.1 --port 5000
```

The clean measured run produced finished baseline run `8d3852e9157c42b282d92e6a59dd3519` and sensitivity run `91ba1fe86e06425f903e83797af8d7ed`. Each stores parameters, split periods, feature configuration, metrics, the joblib model, evaluation JSON, and metadata JSON. Runtime tracking data and model artifacts are Git-ignored.

## Inference service

`AnomalyDetectionService.analyze_user(user_id, start, end)` accepts an aware interval no longer than 24 hours, requires at least two events, applies the persisted pipeline, and returns the entity/window, score, flag, feature values, feature signals, and model version. Two events are enough to evaluate the retained impossible-travel example; this service availability threshold does not change the model, features, or artifact. It raises explicit errors for invalid users/windows, insufficient history, missing/corrupt artifacts, and incompatible schemas.

`default_user_window(user_id)` returns the user's latest active UTC calendar day. Phase 8 uses this deterministic, dataset-relative default only when the investigation supplies no time. The LangGraph tool is a thin read-only adapter over these methods and stores the result as typed ML evidence.

The live smoke for U104 on August 31 returned score `0.1316868314`, `flagged_anomalous=true`, and elevated failed-login, unusual-hour, and short-window frequency signals.

The Phase 8 impossible-travel check for U105 on August 31 returned the exact score `-0.21107408822812324` and `flagged_anomalous=false`, while event evidence showed Germany and Japan logins fifteen minutes apart. Both results remain visible in the final response.

## Limitations

The evaluation set is small, deterministic, and generated by the same codebase. Active-only entity-days omit inactivity, daily aggregation loses sequence detail, and a fixed global model does not learn per-user baselines. The selected 2% training contamination yielded 6.86% false positives on the shifted holdout. The score is not a calibrated probability. Impossible travel is missed. MLflow SQLite and local artifacts suit this single-user demonstration, not concurrent production tracking.
