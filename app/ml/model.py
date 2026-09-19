"""Deterministic Isolation Forest training, scoring, and artifact persistence."""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import joblib
import numpy as np
import sklearn
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from app.ml.features import FEATURE_NAMES, Observation, feature_matrix

MODEL_VERSION = "isolation_forest_daily_v1"
ARTIFACT_SCHEMA_VERSION = 1


class ModelArtifactError(RuntimeError):
    pass


class IncompatibleModelArtifact(ModelArtifactError):
    pass


@dataclass(frozen=True)
class ModelConfig:
    name: str
    n_estimators: int
    contamination: float
    max_samples: str | int = "auto"
    random_state: int = 42


@dataclass
class ModelArtifact:
    pipeline: Pipeline
    metadata: dict[str, Any]


@dataclass(frozen=True)
class ScoredObservation:
    observation: Observation
    anomaly_score: float
    flagged_anomalous: bool


def _reference(matrix: np.ndarray) -> dict[str, dict[str, float]]:
    return {
        name: {
            "median": float(np.median(matrix[:, index])),
            "p90": float(np.quantile(matrix[:, index], 0.9)),
        }
        for index, name in enumerate(FEATURE_NAMES)
    }


def train_artifact(
    observations: list[Observation],
    config: ModelConfig,
    *,
    training_period_start: datetime,
    training_period_end: datetime,
) -> ModelArtifact:
    matrix = feature_matrix(observations)
    pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            (
                "isolation_forest",
                IsolationForest(
                    n_estimators=config.n_estimators,
                    contamination=config.contamination,
                    max_samples=config.max_samples,
                    random_state=config.random_state,
                    n_jobs=1,
                ),
            ),
        ]
    )
    pipeline.fit(matrix)
    metadata = {
        "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
        "model_version": MODEL_VERSION,
        "model_type": "IsolationForest",
        "config_name": config.name,
        "feature_names": list(FEATURE_NAMES),
        "observation_window_hours": 24,
        "training_period_start": training_period_start.astimezone(UTC).isoformat(),
        "training_period_end": training_period_end.astimezone(UTC).isoformat(),
        "training_observations": len(observations),
        "random_state": config.random_state,
        "n_estimators": config.n_estimators,
        "contamination": config.contamination,
        "max_samples": config.max_samples,
        "scikit_learn_version": sklearn.__version__,
        "trained_at": datetime.now(UTC).isoformat(),
        "feature_reference": _reference(matrix),
    }
    return ModelArtifact(pipeline=pipeline, metadata=metadata)


def score_observations(
    artifact: ModelArtifact, observations: list[Observation]
) -> list[ScoredObservation]:
    _validate_artifact(artifact)
    matrix = feature_matrix(observations)
    scores = -artifact.pipeline.decision_function(matrix)
    flags = artifact.pipeline.predict(matrix) == -1
    return [
        ScoredObservation(item, float(score), bool(flag))
        for item, score, flag in zip(observations, scores, flags, strict=True)
    ]


def _validate_artifact(artifact: object) -> ModelArtifact:
    if not isinstance(artifact, ModelArtifact):
        raise IncompatibleModelArtifact("Unexpected artifact type")
    metadata = artifact.metadata
    if metadata.get("artifact_schema_version") != ARTIFACT_SCHEMA_VERSION:
        raise IncompatibleModelArtifact("Artifact schema version mismatch")
    if tuple(metadata.get("feature_names", ())) != FEATURE_NAMES:
        raise IncompatibleModelArtifact("Feature schema mismatch")
    if metadata.get("model_version") != MODEL_VERSION:
        raise IncompatibleModelArtifact("Model version mismatch")
    if not isinstance(artifact.pipeline, Pipeline):
        raise IncompatibleModelArtifact("Missing preprocessing/model pipeline")
    return artifact


def save_artifact(artifact: ModelArtifact, path: Path) -> None:
    _validate_artifact(artifact)
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, prefix=path.name, suffix=".tmp", delete=False) as tmp:
        temporary = Path(tmp.name)
    try:
        joblib.dump(artifact, temporary)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def load_artifact(path: Path) -> ModelArtifact:
    if not path.is_file():
        raise FileNotFoundError(f"Model artifact not found: {path}")
    try:
        artifact = joblib.load(path)
    except Exception as exc:
        raise ModelArtifactError("Unable to load model artifact") from exc
    return _validate_artifact(artifact)
