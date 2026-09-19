"""Small MLflow adapter for local SQLite tracking and local artifacts."""

from pathlib import Path

import mlflow
from mlflow import MlflowClient


def log_run(
    *,
    tracking_uri: str,
    experiment_name: str,
    artifact_root: Path,
    run_name: str,
    parameters: dict[str, object],
    metrics: dict[str, float],
    artifact_files: list[Path],
) -> dict[str, str]:
    artifact_root.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient(tracking_uri=tracking_uri)
    experiment = client.get_experiment_by_name(experiment_name)
    if experiment is None:
        experiment_id = client.create_experiment(
            experiment_name, artifact_location=artifact_root.resolve().as_uri()
        )
    else:
        experiment_id = experiment.experiment_id
    with mlflow.start_run(experiment_id=experiment_id, run_name=run_name) as active:
        mlflow.log_params({key: str(value) for key, value in parameters.items()})
        mlflow.log_metrics(metrics)
        for path in artifact_files:
            mlflow.log_artifact(str(path), artifact_path="phase7")
        run_id = active.info.run_id
    run = client.get_run(run_id)
    artifacts = client.list_artifacts(run_id, "phase7")
    if run.info.status != "FINISHED" or len(artifacts) != len(artifact_files):
        raise RuntimeError("MLflow run or artifacts did not complete")
    return {
        "run_id": run_id,
        "status": run.info.status,
        "artifact_uri": run.info.artifact_uri,
    }
