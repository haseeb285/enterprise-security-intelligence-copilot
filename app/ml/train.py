"""Reproducible Phase 7 training, evaluation, persistence, and MLflow CLI."""

import argparse
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.settings import Settings
from app.db.models import SecurityEvent
from app.db.session import create_db_engine
from app.ml.evaluation import evaluate_holdout, load_ground_truth
from app.ml.features import FEATURE_NAMES, build_daily_observations, chronological_split
from app.ml.model import ModelConfig, save_artifact, score_observations, train_artifact
from app.ml.tracking import log_run

PERIOD_START = datetime(2026, 8, 3, tzinfo=UTC)
SPLIT_CUTOFF = datetime(2026, 8, 24, tzinfo=UTC)
PERIOD_END = datetime(2026, 9, 1, tzinfo=UTC)
DEFAULT_MODEL_PATH = Path("models/anomaly/isolation_forest_daily_v1.joblib")
DEFAULT_TRUTH_PATH = Path("data/runtime/ground_truth.json")
DEFAULT_RESULT_PATH = Path("work/phase7-evaluation.json")
DEFAULT_MLFLOW_DB = Path("work/mlflow.db")
DEFAULT_MLFLOW_ARTIFACTS = Path("work/mlartifacts")
EXPERIMENT_NAME = "security-copilot-phase7"

CONFIGS = (
    ModelConfig("baseline", n_estimators=200, contamination=0.02),
    ModelConfig("sensitivity_check", n_estimators=300, contamination=0.01),
)


def _tracking_uri(path: Path) -> str:
    return f"sqlite:///{path.resolve()}"


def _clean_runtime(paths: list[Path]) -> None:
    root = Path.cwd().resolve()
    allowed = {(root / "work").resolve(), (root / "models").resolve()}
    for path in paths:
        resolved = path.resolve()
        if not any(resolved == base or base in resolved.parents for base in allowed):
            raise ValueError(f"Refusing to clean outside ignored runtime roots: {path}")
        if resolved.is_dir():
            shutil.rmtree(resolved)
        else:
            resolved.unlink(missing_ok=True)


def run_training(
    *,
    model_path: Path = DEFAULT_MODEL_PATH,
    truth_path: Path = DEFAULT_TRUTH_PATH,
    result_path: Path = DEFAULT_RESULT_PATH,
    mlflow_db: Path = DEFAULT_MLFLOW_DB,
    mlflow_artifacts: Path = DEFAULT_MLFLOW_ARTIFACTS,
    clean: bool = False,
) -> dict:
    if clean:
        _clean_runtime([model_path.parent, result_path, mlflow_db, mlflow_artifacts])
    engine = create_db_engine(Settings())
    try:
        with Session(engine) as session:
            events = list(
                session.scalars(
                    select(SecurityEvent)
                    .where(
                        SecurityEvent.timestamp >= PERIOD_START,
                        SecurityEvent.timestamp < PERIOD_END,
                    )
                    .order_by(SecurityEvent.timestamp, SecurityEvent.event_id)
                )
            )
    finally:
        engine.dispose()
    if not events:
        raise RuntimeError("No synthetic security events found; seed PostgreSQL first")
    observations = build_daily_observations(events, PERIOD_START, PERIOD_END)
    training, holdout = chronological_split(observations, SPLIT_CUTOFF)

    # Fit every unsupervised configuration before loading any scenario labels.
    fitted = []
    experiment_dir = Path("work/phase7-experiments")
    for config in CONFIGS:
        artifact = train_artifact(
            training,
            config,
            training_period_start=PERIOD_START,
            training_period_end=SPLIT_CUTOFF,
        )
        scored = score_observations(artifact, holdout)
        artifact_path = experiment_dir / f"{config.name}.joblib"
        save_artifact(artifact, artifact_path)
        fitted.append((config, artifact, scored, artifact_path))

    scenarios = load_ground_truth(truth_path)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    experiment_records = []
    for config, artifact, scored, artifact_path in fitted:
        evaluation = evaluate_holdout(scored, scenarios)
        evaluation_path = experiment_dir / f"{config.name}-evaluation.json"
        metadata_path = experiment_dir / f"{config.name}-metadata.json"
        evaluation_path.parent.mkdir(parents=True, exist_ok=True)
        evaluation_path.write_text(
            json.dumps(evaluation.as_json(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        metadata_path.write_text(
            json.dumps(artifact.metadata, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        mlflow_result = log_run(
            tracking_uri=_tracking_uri(mlflow_db),
            experiment_name=EXPERIMENT_NAME,
            artifact_root=mlflow_artifacts,
            run_name=config.name,
            parameters={
                **artifact.metadata,
                "feature_names": ",".join(FEATURE_NAMES),
                "holdout_period_start": SPLIT_CUTOFF.isoformat(),
                "holdout_period_end": PERIOD_END.isoformat(),
            },
            metrics={
                "scenario_recall": evaluation.scenario_recall,
                "false_positive_rate": evaluation.false_positive_rate,
                "flagged_precision": evaluation.flagged_precision,
                "top_5_scenario_capture": float(evaluation.top_5_scenario_capture),
                "top_10_scenario_capture": float(evaluation.top_10_scenario_capture),
                "scenario_score_mean": evaluation.scenario_score_mean,
                "normal_score_mean": evaluation.normal_score_mean,
            },
            artifact_files=[artifact_path, evaluation_path, metadata_path],
        )
        experiment_records.append(
            {
                "config": config.name,
                "evaluation": evaluation.as_json(),
                "mlflow": mlflow_result,
            }
        )

    # The baseline is selected before evaluation; the second run is a sensitivity check only.
    save_artifact(fitted[0][1], model_path)
    summary = {
        "notice": (
            "This model is trained and evaluated on synthetic demonstration data and is not "
            "a production security detection engine."
        ),
        "period_start": PERIOD_START.isoformat(),
        "split_cutoff": SPLIT_CUTOFF.isoformat(),
        "period_end": PERIOD_END.isoformat(),
        "training_observations": len(training),
        "holdout_observations": len(holdout),
        "feature_names": list(FEATURE_NAMES),
        "selected_config": CONFIGS[0].name,
        "model_path": str(model_path),
        "experiments": experiment_records,
    }
    result_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--truth-path", type=Path, default=DEFAULT_TRUTH_PATH)
    parser.add_argument("--result-path", type=Path, default=DEFAULT_RESULT_PATH)
    parser.add_argument("--mlflow-db", type=Path, default=DEFAULT_MLFLOW_DB)
    parser.add_argument("--mlflow-artifacts", type=Path, default=DEFAULT_MLFLOW_ARTIFACTS)
    parser.add_argument(
        "--clean", action="store_true", help="Remove only ignored Phase 7 runtime outputs first"
    )
    args = parser.parse_args()
    result = run_training(
        model_path=args.model_path,
        truth_path=args.truth_path,
        result_path=args.result_path,
        mlflow_db=args.mlflow_db,
        mlflow_artifacts=args.mlflow_artifacts,
        clean=args.clean,
    )
    compact = {
        "training_observations": result["training_observations"],
        "holdout_observations": result["holdout_observations"],
        "selected_config": result["selected_config"],
        "experiments": [
            {
                "config": item["config"],
                "scenario_recall": item["evaluation"]["scenario_recall"],
                "false_positive_rate": item["evaluation"]["false_positive_rate"],
                "top_10_scenario_capture": item["evaluation"]["top_10_scenario_capture"],
                "mlflow_run_id": item["mlflow"]["run_id"],
            }
            for item in result["experiments"]
        ],
    }
    print(result["notice"])
    print(json.dumps(compact, indent=2))


if __name__ == "__main__":
    main()
