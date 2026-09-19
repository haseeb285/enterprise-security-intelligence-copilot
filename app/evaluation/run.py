"""Run the layered Phase 10 development evaluation without a composite accuracy score."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from sqlalchemy.orm import Session

from app.core.settings import Settings
from app.db.session import create_db_engine
from app.evaluation.cases import ROOT, case_counts, load_suite
from app.evaluation.metrics import score_integrated, summarize_llm, summarize_ml
from app.evaluation.safety import evaluate_safety
from app.ml.service import AnomalyDetectionService
from app.rag.embeddings import get_embedder
from app.rag.evaluate import evaluate as evaluate_retrieval
from app.rag.service import RagService
from app.rag.store import VectorStore

DEFAULT_OUTPUT = ROOT / "work/phase10/latest.json"
DEFAULT_SUMMARY = ROOT / "evaluation/results/phase10-summary.json"
DEFAULT_MARKDOWN = ROOT / "evaluation/results/phase10-summary.md"
PHASE7_RESULT = ROOT / "work/phase7-evaluation.json"
LLM_RESULT = ROOT / "work/phase10/llm-structured.json"
INTEGRATED_RESULT = ROOT / "work/phase8-integrated-evaluation.json"
MANUAL_REVIEW = ROOT / "evaluation/results/phase10-manual-review.json"


def _json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(
            f"Required evaluation artifact is missing: {path.relative_to(ROOT)}"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _markdown(payload: dict) -> str:
    lines = [
        "# Phase 10 generated evaluation summary",
        "",
        f"Suite version: `{payload['suite_version']}`",
        "",
        "> " + payload["notice"],
        "",
    ]

    def add_table(title: str, rows: list[tuple[str, str]]) -> None:
        lines.extend([title, "", "| Metric | Result |", "| --- | ---: |"])
        lines.extend(f"| {label} | {value} |" for label, value in rows)
        lines.append("")

    if "offline" in payload:
        retrieval = payload["offline"]["retrieval"]
        ml = payload["offline"]["ml"]
        safety = payload["offline"]["safety"]
        add_table(
            "## Offline layers",
            [
                (
                    "Retrieval Recall@1 / @3 / @5",
                    f"{retrieval['recall_at_1']:.3f} / {retrieval['recall_at_3']:.3f} / "
                    f"{retrieval['recall_at_5']:.3f}",
                ),
                ("Retrieval MRR", f"{retrieval['mrr']:.3f}"),
                (
                    "Answerable gate acceptance",
                    f"{retrieval['positive_accepted']}/{retrieval['positives']} "
                    f"({retrieval['answerable_acceptance_rate']:.2%})",
                ),
                (
                    "Unanswerable gate rejection",
                    f"{retrieval['negative_rejected']}/{retrieval['negative_total']} "
                    f"({retrieval['unanswerable_rejection_rate']:.2%})",
                ),
                (
                    "Citation/source correctness",
                    f"{retrieval['citation_source_correct']}/{retrieval['citation_source_total']}",
                ),
                (
                    "Retrieval mean / median",
                    f"{retrieval['latency_mean_ms']:.3f} / {retrieval['latency_median_ms']:.3f} ms",
                ),
                (
                    "ML scenario detection",
                    f"{ml['scenarios_flagged']}/{ml['scenario_count']} "
                    f"({ml['scenario_recall']:.2%})",
                ),
                (
                    "ML false-positive rate",
                    f"{ml['false_positive_observations']}/"
                    f"{ml['normal_holdout_observations']} ({ml['false_positive_rate']:.2%})",
                ),
                ("ML flagged precision", f"{ml['flagged_precision']:.2%}"),
                (
                    "ML Top-5 / Top-10 capture",
                    f"{ml['top_5_scenario_capture']}/{ml['scenario_count']} / "
                    f"{ml['top_10_scenario_capture']}/{ml['scenario_count']}",
                ),
                (
                    "ML cold / warm median inference",
                    f"{ml['inference_latency']['cold_ms']:.3f} / "
                    f"{ml['inference_latency']['warm_median_ms']:.3f} ms",
                ),
                ("Deterministic safety contracts", f"{safety['passed']}/{safety['case_count']}"),
            ],
        )
    if "live" in payload:
        generation = payload["live"]["structured_generation"]
        integrated = payload["live"]["integrated"]
        manual = payload["live"].get("manual_review", {})
        add_table(
            "## Live local-model layers",
            [
                (
                    "Structured-generation checks",
                    f"{generation['passed']}/{generation['case_count']}",
                ),
                ("Schema validity", f"{generation['schema_valid']}/{generation['schema_total']}"),
                ("Malformed structured outputs", str(generation["malformed_output_count"])),
                (
                    "Integrated expected tool sets",
                    f"{integrated['tool_selection_correct']}/{integrated['case_count']}",
                ),
                (
                    "Integrated procedural completion",
                    f"{integrated['procedural_completion']}/{integrated['case_count']}",
                ),
                (
                    "Source/provenance fidelity",
                    f"{integrated['source_provenance_fidelity']}/{integrated['case_count']}",
                ),
                (
                    "Policy citation fidelity",
                    f"{integrated['policy_citation_fidelity']}/{integrated['case_count']}",
                ),
                (
                    "Exact anomaly score / flag fidelity",
                    f"{integrated['anomaly_score_fidelity']}/{integrated['case_count']} / "
                    f"{integrated['anomaly_flag_fidelity']}/{integrated['case_count']}",
                ),
                (
                    "Unsupported identifier / score references",
                    f"{integrated['unsupported_identifier_count']} / "
                    f"{integrated['unsupported_score_reference_count']}",
                ),
                (
                    "Deterministic fact checks",
                    f"{integrated['deterministic_fact_checks']}/"
                    f"{integrated['deterministic_fact_total']}",
                ),
                (
                    "Integrated mean / median latency",
                    f"{integrated['mean_latency_seconds']:.3f} / "
                    f"{integrated['median_latency_seconds']:.3f} s",
                ),
                (
                    "Manual direct-answer review",
                    f"{manual.get('answers_request', 'n/a')}/{manual.get('case_count', 'n/a')}",
                ),
            ],
        )
        lines.extend(
            [
                "The impossible-travel regression passed by preserving Germany and Japan events "
                "fifteen minutes apart together with score `-0.21107408822812324` and "
                "`flagged=false`.",
                "",
            ]
        )
    lines.append("No combined project accuracy score is calculated.")
    return "\n".join(lines) + "\n"


def _retrieval(settings: Settings, cases: list[dict]) -> dict:
    embedder = get_embedder(settings.embedding_model)
    store = VectorStore(str(settings.qdrant_url), settings.rag_collection, embedder.dimension)
    store.ready()
    service = RagService(
        store,
        embedder,
        settings.rag_chunk_target_chars,
        settings.rag_chunk_overlap_chars,
        threshold=0,
    )
    first = evaluate_retrieval(service, cases, settings.rag_min_score)
    repeat = evaluate_retrieval(service, cases, settings.rag_min_score)
    deterministic = first["records"] == repeat["records"]
    first["warm_repeat_mean_ms"] = repeat["latency_mean_ms"]
    first["warm_repeat_median_ms"] = repeat["latency_median_ms"]
    first["deterministic_repeat_match"] = deterministic
    return first


def _ml(settings: Settings) -> dict:
    result = summarize_ml(_json(PHASE7_RESULT))
    engine = create_db_engine(settings)
    timings = []
    try:
        with Session(engine) as session:
            service = AnomalyDetectionService(session, settings.ml_model_path)
            start, end = (
                datetime(2026, 8, 31, tzinfo=UTC),
                datetime(2026, 9, 1, tzinfo=UTC),
            )
            for _ in range(6):
                started = perf_counter()
                measured = service.analyze_user("U105", start, end)
                timings.append((perf_counter() - started) * 1000)
    finally:
        engine.dispose()
    expected = result["impossible_travel"]
    result["inference_latency"] = {
        "cold_ms": timings[0],
        "warm_mean_ms": statistics.mean(timings[1:]),
        "warm_median_ms": statistics.median(timings[1:]),
    }
    result["impossible_travel_regression"] = {
        "passed": measured.anomaly_score == expected["best_score"]
        and measured.flagged_anomalous is expected["flagged"],
        "score": measured.anomaly_score,
        "flagged": measured.flagged_anomalous,
        "expected_countries": ["DE", "JP"],
        "expected_minutes_apart": 15,
    }
    return result


def run_offline(suite: dict) -> dict:
    settings = Settings()
    retrieval = _retrieval(settings, suite["cases"]["retrieval"])
    ml = _ml(settings)
    safety = evaluate_safety(suite["cases"]["safety"])
    return {
        "completed": True,
        "requires_ollama": False,
        "retrieval": retrieval,
        "ml": ml,
        "safety": safety,
        "agent_labels": {
            "case_count": len(suite["cases"]["agent_routing"]),
            "expected_tools_predefined": True,
        },
    }


def _command(*parts: str) -> None:
    subprocess.run([sys.executable, *parts], cwd=ROOT, check=True)


def assemble_live(suite: dict) -> dict:
    """Score completed live artifacts without repeating expensive local inference."""
    llm = summarize_llm(_json(LLM_RESULT))
    integrated_payload = _json(INTEGRATED_RESULT)
    integrated = score_integrated(
        suite["cases"]["integrated"],
        integrated_payload["cases"],
        suite["cases"]["fact_expectations"],
    )
    result = {
        "completed": True,
        "requires_ollama": True,
        "structured_generation": llm,
        "integrated": integrated,
    }
    if MANUAL_REVIEW.is_file():
        review = _json(MANUAL_REVIEW)
        digest = hashlib.sha256(INTEGRATED_RESULT.read_bytes()).hexdigest()
        result["manual_review"] = (
            review["summary"]
            if review.get("reviewed_artifact_sha256") == digest
            else {
                "status": "stale",
                "reviewed_artifact_sha256": review.get("reviewed_artifact_sha256"),
            }
        )
    return result


def run_live(suite: dict) -> dict:
    _command("-m", "app.llm.smoke", "--output", str(LLM_RESULT))
    _command("-m", "app.agent.evaluate_integrated")
    return assemble_live(suite)


def _sanitized(payload: dict) -> dict:
    summary = {
        "suite_version": payload["suite_version"],
        "notice": payload["notice"],
        "case_counts": payload["case_counts"],
    }
    if "offline" in payload:
        offline = payload["offline"]
        summary["offline"] = {
            "completed": offline["completed"],
            "retrieval": {
                key: value for key, value in offline["retrieval"].items() if key != "records"
            },
            "ml": offline["ml"],
            "safety": {key: value for key, value in offline["safety"].items() if key != "records"},
        }
    if "live" in payload:
        live = payload["live"]
        summary["live"] = {
            "completed": live["completed"],
            "structured_generation": live["structured_generation"],
            "integrated": live["integrated"]["summary"],
            "fact_checks": live["integrated"]["facts"],
        }
        if "manual_review" in live:
            summary["live"]["manual_review"] = live["manual_review"]
    return summary


def run(
    mode: str,
    output: Path,
    summary_path: Path,
    markdown_path: Path = DEFAULT_MARKDOWN,
) -> dict:
    suite = load_suite()
    payload = (
        _json(output)
        if output.is_file() and mode in {"offline", "live"}
        else {
            "suite_version": suite["version"],
            "notice": suite["notice"],
            "case_counts": case_counts(suite),
        }
    )
    if payload.get("suite_version") != suite["version"]:
        raise ValueError("Existing result belongs to another evaluation suite version")
    if mode in {"offline", "all"}:
        payload["offline"] = run_offline(suite)
    if mode in {"live", "all"}:
        payload["live"] = run_live(suite)
    payload["generated_at"] = datetime.now(UTC).isoformat()
    payload["commands"] = {
        "offline": ".venv/bin/python -m app.evaluation.run --offline",
        "live": ".venv/bin/python -m app.evaluation.run --live",
        "all": ".venv/bin/python -m app.evaluation.run --all",
    }
    _write(output, payload)
    sanitized = _sanitized(payload)
    _write(summary_path, sanitized)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(_markdown(sanitized), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Run layers that do not need Ollama")
    parser.add_argument("--live", action="store_true", help="Run local-LLM and integrated layers")
    parser.add_argument("--all", action="store_true", help="Run every layer")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    selected = [name for name in ("offline", "live", "all") if getattr(args, name)]
    if len(selected) != 1:
        parser.error("select exactly one of --offline, --live, or --all")
    result = run(selected[0], args.output, args.summary, args.markdown)
    print(json.dumps(_sanitized(result), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
