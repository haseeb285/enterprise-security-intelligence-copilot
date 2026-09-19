"""Versioned evaluation-suite loading and validation."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from app.agent.schemas import ToolName

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SUITE = ROOT / "evaluation/phase10_suite.json"


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_suite(path: Path = DEFAULT_SUITE) -> dict:
    payload = _read(path)
    if payload.get("version") != "1.0.0":
        raise ValueError("Unsupported evaluation suite version")
    if "SYNTHETIC DEMONSTRATION DATA" not in payload.get("notice", ""):
        raise ValueError("Evaluation suite lacks synthetic-data notice")
    datasets = payload.get("datasets")
    required = {
        "retrieval",
        "structured_generation",
        "agent_routing",
        "integrated",
        "fact_expectations",
        "safety",
    }
    if not isinstance(datasets, dict) or set(datasets) != required:
        raise ValueError("Evaluation suite dataset manifest is incomplete")
    loaded = {}
    for name, relative in datasets.items():
        dataset_path = (ROOT / relative).resolve()
        if ROOT not in dataset_path.parents or dataset_path.suffix != ".json":
            raise ValueError("Evaluation dataset path is invalid")
        value = _read(dataset_path)
        cases = value if isinstance(value, list) else value.get("cases")
        if not isinstance(cases, list) or not cases:
            raise ValueError(f"Evaluation dataset has no cases: {name}")
        ids = [item.get("id", f"retrieval-{index}") for index, item in enumerate(cases)]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Evaluation dataset has duplicate IDs: {name}")
        loaded[name] = cases
    allowed = {item.value for item in ToolName}
    for dataset in ("agent_routing", "integrated"):
        for case in loaded[dataset]:
            tools = case.get("expected_tools")
            if not isinstance(tools, list) or len(tools) > 3 or not set(tools) <= allowed:
                raise ValueError(f"Invalid expected tools for {case.get('id')}")
    return {**payload, "cases": loaded}


def case_counts(suite: dict) -> dict:
    counts = {}
    for name, cases in suite["cases"].items():
        categories = Counter(
            case.get(
                "category",
                "answerable"
                if name == "retrieval" and case.get("document")
                else "unanswerable"
                if name == "retrieval"
                else "fact_expectation",
            )
            for case in cases
        )
        counts[name] = {"total": len(cases), "categories": dict(sorted(categories.items()))}
    return counts
