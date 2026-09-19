"""Holdout evaluation against separately stored synthetic scenario truth."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from app.ml.model import ScoredObservation


@dataclass(frozen=True)
class ScenarioResult:
    scenario_id: str
    scenario_type: str
    observation_keys: tuple[str, ...]
    flagged: bool
    best_rank: int | None
    best_score: float | None


@dataclass(frozen=True)
class EvaluationResult:
    holdout_observations: int
    scenario_count: int
    scenarios_flagged: int
    scenario_recall: float
    flagged_observations: int
    flagged_scenario_observations: int
    false_positive_observations: int
    normal_holdout_observations: int
    false_positive_rate: float
    flagged_precision: float
    top_5_scenario_capture: int
    top_10_scenario_capture: int
    scenario_score_mean: float
    normal_score_mean: float
    scenario_results: tuple[ScenarioResult, ...]

    def as_json(self) -> dict:
        return asdict(self)


def load_ground_truth(path: Path) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(f"Ground truth not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "SYNTHETIC DEMONSTRATION DATA" not in payload.get("notice", ""):
        raise ValueError("Ground truth lacks synthetic-data notice")
    scenarios = payload.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("Ground truth has no scenarios")
    required = {"scenario_id", "scenario_type", "related_event_ids"}
    if any(not required <= set(item) for item in scenarios):
        raise ValueError("Ground truth scenario is malformed")
    return scenarios


def evaluate_holdout(scored: list[ScoredObservation], scenarios: list[dict]) -> EvaluationResult:
    if not scored:
        raise ValueError("Holdout evaluation needs scored observations")
    ranked = sorted(scored, key=lambda item: item.anomaly_score, reverse=True)
    rank_by_key = {_key(item): position for position, item in enumerate(ranked, start=1)}
    score_by_key = {_key(item): item.anomaly_score for item in scored}
    flag_by_key = {_key(item): item.flagged_anomalous for item in scored}
    events_by_key = {_key(item): set(item.observation.event_ids) for item in scored}

    scenario_keys: dict[str, set[str]] = {}
    results = []
    for scenario in scenarios:
        truth_ids = set(scenario["related_event_ids"])
        keys = {key for key, event_ids in events_by_key.items() if event_ids & truth_ids}
        scenario_keys[scenario["scenario_id"]] = keys
        ranks = [rank_by_key[key] for key in keys]
        scores = [score_by_key[key] for key in keys]
        results.append(
            ScenarioResult(
                scenario_id=scenario["scenario_id"],
                scenario_type=scenario["scenario_type"],
                observation_keys=tuple(sorted(keys)),
                flagged=any(flag_by_key[key] for key in keys),
                best_rank=min(ranks) if ranks else None,
                best_score=max(scores) if scores else None,
            )
        )

    all_scenario_keys = set().union(*scenario_keys.values())
    flagged_keys = {key for key, flag in flag_by_key.items() if flag}
    flagged_scenario = flagged_keys & all_scenario_keys
    normal_keys = set(flag_by_key) - all_scenario_keys
    false_positives = flagged_keys & normal_keys
    scenario_scores = [score_by_key[key] for key in all_scenario_keys]
    normal_scores = [score_by_key[key] for key in normal_keys]

    def top_capture(limit: int) -> int:
        top_keys = {_key(item) for item in ranked[:limit]}
        return sum(bool(keys & top_keys) for keys in scenario_keys.values())

    return EvaluationResult(
        holdout_observations=len(scored),
        scenario_count=len(results),
        scenarios_flagged=sum(item.flagged for item in results),
        scenario_recall=sum(item.flagged for item in results) / len(results),
        flagged_observations=len(flagged_keys),
        flagged_scenario_observations=len(flagged_scenario),
        false_positive_observations=len(false_positives),
        normal_holdout_observations=len(normal_keys),
        false_positive_rate=len(false_positives) / len(normal_keys) if normal_keys else 0.0,
        flagged_precision=len(flagged_scenario) / len(flagged_keys) if flagged_keys else 0.0,
        top_5_scenario_capture=top_capture(5),
        top_10_scenario_capture=top_capture(10),
        scenario_score_mean=float(np.mean(scenario_scores)) if scenario_scores else 0.0,
        normal_score_mean=float(np.mean(normal_scores)) if normal_scores else 0.0,
        scenario_results=tuple(results),
    )


def _key(item: ScoredObservation) -> str:
    observation = item.observation
    return (
        f"{observation.entity_type}:{observation.entity_id}:{observation.window_start.isoformat()}"
    )
