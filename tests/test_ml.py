"""Phase 7 leakage, temporal, model, inference, evaluation, and MLflow tests."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import joblib
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import Base, SecurityEvent, User
from app.ml.evaluation import evaluate_holdout, load_ground_truth
from app.ml.features import (
    FEATURE_NAMES,
    FORBIDDEN_FEATURE_FIELDS,
    build_daily_observations,
    build_observation,
    chronological_split,
    feature_matrix,
)
from app.ml.model import (
    IncompatibleModelArtifact,
    ModelArtifactError,
    ModelConfig,
    load_artifact,
    save_artifact,
    score_observations,
    train_artifact,
)
from app.ml.service import (
    AnomalyDetectionService,
    InsufficientHistoryError,
    InvalidAnalysisWindow,
    UnknownUserError,
)
from app.ml.tracking import log_run


@dataclass
class Event:
    event_id: str
    timestamp: datetime
    user_id: str | None = "U001"
    source_ip: str = "192.0.2.1"
    device_id: str | None = "D001"
    event_type: str = "successful_login"
    country: str | None = "US"
    privileged_account: bool | None = False


START = datetime(2026, 8, 3, tzinfo=UTC)


def _observations(days: int = 12):
    events = []
    for day in range(days):
        for index in range(3 + day % 4):
            events.append(
                Event(
                    event_id=f"EV{day:03d}{index:03d}",
                    timestamp=START + timedelta(days=day, hours=8 + index),
                    source_ip=f"192.0.2.{1 + index % 2}",
                    event_type="failed_login"
                    if index == 0 and day % 3 == 0
                    else "successful_login",
                )
            )
    return build_daily_observations(events, START, START + timedelta(days=days))


def test_features_are_deterministic_and_exclude_future_events():
    events = [
        Event("EV000001", START + timedelta(hours=1), event_type="failed_login"),
        Event("EV000002", START + timedelta(hours=2), source_ip="192.0.2.2"),
        Event("EV000003", START + timedelta(days=1, minutes=1), event_type="failed_login"),
    ]
    first = build_observation(
        events,
        entity_type="user",
        entity_id="U001",
        window_start=START,
        window_end=START + timedelta(days=1),
    )
    second = build_observation(
        list(reversed(events)),
        entity_type="user",
        entity_id="U001",
        window_start=START,
        window_end=START + timedelta(days=1),
    )
    assert first.features == second.features
    assert first.event_ids == second.event_ids == ("EV000001", "EV000002")
    assert first.features["failed_login_count"] == 1
    assert first.features["unique_source_ip_count"] == 2


def test_feature_schema_has_no_ground_truth_or_generator_leakage():
    assert not (set(FEATURE_NAMES) & FORBIDDEN_FEATURE_FIELDS)
    forbidden_terms = ("scenario", "ground", "label", "incident", "reason", "severity")
    assert all(not any(term in name for term in forbidden_terms) for name in FEATURE_NAMES)
    matrix = feature_matrix(_observations())
    assert matrix.shape == (12, len(FEATURE_NAMES))


def test_chronological_split_is_ordered_and_nonoverlapping():
    observations = _observations()
    cutoff = START + timedelta(days=8)
    training, holdout = chronological_split(observations, cutoff)
    assert len(training) == 8 and len(holdout) == 4
    assert max(item.window_end for item in training) <= cutoff
    assert min(item.window_start for item in holdout) >= cutoff


def test_model_training_persistence_and_preprocessing_consistency(tmp_path):
    observations = _observations()
    config = ModelConfig("test", n_estimators=40, contamination=0.1)
    artifact = train_artifact(
        observations,
        config,
        training_period_start=START,
        training_period_end=START + timedelta(days=12),
    )
    before = score_observations(artifact, observations)
    path = tmp_path / "model.joblib"
    save_artifact(artifact, path)
    loaded = load_artifact(path)
    after = score_observations(loaded, observations)
    assert [item.anomaly_score for item in before] == pytest.approx(
        [item.anomaly_score for item in after]
    )
    assert [item.flagged_anomalous for item in before] == [item.flagged_anomalous for item in after]
    assert loaded.metadata["feature_names"] == list(FEATURE_NAMES)


def test_missing_corrupt_and_incompatible_artifacts(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_artifact(tmp_path / "missing.joblib")
    corrupt = tmp_path / "corrupt.joblib"
    corrupt.write_bytes(b"not a joblib artifact")
    with pytest.raises(ModelArtifactError):
        load_artifact(corrupt)
    valid = train_artifact(
        _observations(),
        ModelConfig("test", 20, 0.1),
        training_period_start=START,
        training_period_end=START + timedelta(days=12),
    )
    valid.metadata["feature_names"] = ["leaked_scenario_id"]
    incompatible = tmp_path / "incompatible.joblib"
    joblib.dump(valid, incompatible)
    with pytest.raises(IncompatibleModelArtifact):
        load_artifact(incompatible)


def _service(tmp_path: Path):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    session.add(
        User(
            user_id="U001",
            display_name="Demo Person",
            department="IT",
            home_country="US",
            privileged=False,
            created_at=START,
        )
    )
    for index in range(3):
        session.add(
            SecurityEvent(
                event_id=f"EV90000{index}",
                timestamp=START + timedelta(hours=index + 1),
                user_id="U001",
                source_ip=f"192.0.2.{index + 1}",
                destination_ip=None,
                device_id=None,
                event_type="failed_login" if index else "successful_login",
                severity="low",
                action="deny" if index else "allow",
                status="failure" if index else "success",
                country="US",
                authentication_method="password",
                failed_attempts=1 if index else 0,
                successful_attempts=0 if index else 1,
                privileged_account=False,
                source="synthetic",
                description="Synthetic authentication event",
                incident_id=None,
            )
        )
    session.commit()
    artifact = train_artifact(
        _observations(),
        ModelConfig("test", 30, 0.1),
        training_period_start=START,
        training_period_end=START + timedelta(days=12),
    )
    path = tmp_path / "model.joblib"
    save_artifact(artifact, path)
    return engine, session, path


def test_inference_result_and_error_paths(tmp_path):
    engine, session, path = _service(tmp_path)
    try:
        service = AnomalyDetectionService(session, path)
        result = service.analyze_user("U001", START, START + timedelta(days=1))
        assert result.entity_id == "U001"
        assert isinstance(result.anomaly_score, float)
        assert set(result.feature_values) == set(FEATURE_NAMES)
        assert "not an attack determination" in result.statement
        with pytest.raises(UnknownUserError):
            service.analyze_user("U999", START, START + timedelta(days=1))
        with pytest.raises(InvalidAnalysisWindow):
            service.analyze_user("U001", START, START + timedelta(days=2))
        sparse = AnomalyDetectionService(session, path, minimum_events=4)
        with pytest.raises(InsufficientHistoryError):
            sparse.analyze_user("U001", START, START + timedelta(days=1))
        missing = AnomalyDetectionService(session, tmp_path / "missing.joblib")
        with pytest.raises(FileNotFoundError):
            missing.analyze_user("U001", START, START + timedelta(days=1))
    finally:
        session.close()
        engine.dispose()


def test_evaluation_uses_separate_ground_truth(tmp_path):
    observations = _observations(4)
    artifact = train_artifact(
        observations,
        ModelConfig("test", 20, 0.25),
        training_period_start=START,
        training_period_end=START + timedelta(days=4),
    )
    scored = score_observations(artifact, observations)
    truth = {
        "notice": "SYNTHETIC DEMONSTRATION DATA — NOT REAL SECURITY TELEMETRY",
        "scenarios": [
            {
                "scenario_id": "SCN001",
                "scenario_type": "test_pattern",
                "related_event_ids": [observations[-1].event_ids[0]],
                "expected_investigation_reason": "evaluation only",
            }
        ],
    }
    path = tmp_path / "truth.json"
    path.write_text(json.dumps(truth))
    scenarios = load_ground_truth(path)
    evaluation = evaluate_holdout(scored, scenarios)
    assert evaluation.scenario_count == 1
    assert evaluation.holdout_observations == 4
    assert evaluation.scenario_results[0].best_rank is not None
    assert "scenario" not in artifact.metadata["feature_names"]


def test_mlflow_logging_records_metrics_and_artifacts(tmp_path):
    artifact = tmp_path / "model.joblib"
    evaluation = tmp_path / "evaluation.json"
    artifact.write_bytes(b"synthetic model placeholder")
    evaluation.write_text("{}")
    result = log_run(
        tracking_uri=f"sqlite:///{tmp_path / 'mlflow.db'}",
        experiment_name="phase7-test",
        artifact_root=tmp_path / "artifacts",
        run_name="test-run",
        parameters={"random_state": 42},
        metrics={"scenario_recall": 0.5},
        artifact_files=[artifact, evaluation],
    )
    assert result["status"] == "FINISHED"
    assert result["run_id"]
