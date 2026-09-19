"""Deterministic metric calculations over application-owned evaluation outputs."""

from __future__ import annotations

import re
from collections import Counter
from statistics import mean, median

IDENTIFIER = re.compile(r"\b(?:EV\d{6}|INC\d{3}|U\d{3})\b")
SCORE_REFERENCE = re.compile(
    r"\b(?:anomaly score|model score|ML analysis.{0,100}?\bscore)"
    r"(?:\s+(?:of|is)|\s*=)?\s*(-?\d+(?:\.\d+)?)",
    re.I,
)


def _prose(response: dict) -> str:
    return " ".join(
        [
            response.get("summary", ""),
            response.get("interpretation", ""),
            *response.get("recommended_next_steps", []),
        ]
    )


def _known_identifiers(response: dict) -> set[str]:
    known = set()
    for item in response.get("observed_evidence", []) + response.get("policy_context", []):
        known.update(IDENTIFIER.findall(str(item.get("source_id", ""))))
        known.update(item.get("related_ids", []))
        known.update(IDENTIFIER.findall(str(item.get("attributes", {}))))
    for item in response.get("ml_analysis", []):
        known.add(item.get("entity_id", ""))
    return {item for item in known if IDENTIFIER.fullmatch(item)}


def _fact_check(expectation: dict, response: dict) -> bool:
    kind, expected = expectation["kind"], expectation["expected"]
    if kind == "policy_text":
        text = " ".join(item["text"] for item in response.get("policy_context", []))
        return str(expected).lower() in text.lower()
    if kind == "event_id":
        return expected in {item["source_id"] for item in response.get("observed_evidence", [])}
    if kind == "countries":
        countries = {
            item.get("attributes", {}).get("country")
            for item in response.get("observed_evidence", [])
        }
        return countries == set(expected)
    if not response.get("ml_analysis"):
        return False
    ml = response["ml_analysis"][0]
    if kind == "anomaly_score":
        return ml["anomaly_score"] == expected
    if kind == "anomaly_flag":
        return ml["flagged_anomalous"] is expected
    raise ValueError(f"Unknown fact expectation: {kind}")


def score_integrated(cases: list[dict], records: list[dict], expectations: list[dict]) -> dict:
    case_by_id = {item["id"]: item for item in cases}
    record_by_id = {item["id"]: item for item in records}
    if set(record_by_id) != set(case_by_id):
        raise ValueError("Integrated results do not match the versioned case set")
    scored = []
    for case_id, case in case_by_id.items():
        record = record_by_id[case_id]
        response = record["response"]
        observed = response.get("observed_evidence", [])
        policies = response.get("policy_context", [])
        ml = response.get("ml_analysis", [])
        record_sources = {item["source_id"] for item in [*observed, *policies, *ml]}
        unsupported = sorted(
            set(IDENTIFIER.findall(_prose(response))) - _known_identifiers(response)
        )
        allowed_scores = {item["anomaly_score"] for item in ml}
        unsupported_scores = sorted(
            {
                float(value)
                for value in SCORE_REFERENCE.findall(_prose(response))
                if float(value) not in allowed_scores
            }
        )
        citation_ok = all(
            item.get("citation")
            and item["citation"].get("document")
            and item["citation"].get("source")
            and item["citation"].get("section")
            for item in policies
        )
        separation_ok = (
            all(item.get("kind") in {"event", "incident"} for item in observed)
            and all(item.get("kind") == "policy" for item in policies)
            and all("anomaly_score" in item and "flagged_anomalous" in item for item in ml)
        )
        expected_sufficient = case["expected_outcome"] == "complete"
        scored.append(
            {
                "id": case_id,
                "category": case["category"],
                "tool_selection_correct": record["selection_correct"],
                "procedural_completion": record["task_complete"],
                "execution_limits": response["graph_steps"] <= 5 and response["tool_calls"] <= 3,
                "source_provenance_fidelity": set(response["sources"]) == record_sources,
                "event_id_fidelity": all(
                    item["source_id"].startswith("EV")
                    and item["source"] == "postgresql.security_events"
                    for item in observed
                    if item["kind"] == "event"
                ),
                "incident_id_fidelity": all(
                    item["source_id"].startswith("INC")
                    for item in observed
                    if item["kind"] == "incident"
                ),
                "policy_citation_fidelity": citation_ok,
                "anomaly_score_fidelity": record["anomaly_score_fidelity"]
                and not unsupported_scores,
                "anomaly_flag_fidelity": record.get(
                    "anomaly_flag_fidelity", record["anomaly_score_fidelity"]
                ),
                "evidence_separation": separation_ok,
                "evidence_sufficiency": response["evidence_sufficiency"] is expected_sufficient,
                "structured_response_valid": True,
                "unsupported_identifiers": unsupported,
                "unsupported_score_references": unsupported_scores,
                "latency_seconds": record["latency_seconds"],
            }
        )
    fact_results = []
    for expectation in expectations:
        response = record_by_id[expectation["case_id"]]["response"]
        fact_results.append(
            {
                "id": expectation["id"],
                "case_id": expectation["case_id"],
                "passed": _fact_check(expectation, response),
            }
        )
    fields = [
        "tool_selection_correct",
        "procedural_completion",
        "execution_limits",
        "source_provenance_fidelity",
        "event_id_fidelity",
        "incident_id_fidelity",
        "policy_citation_fidelity",
        "anomaly_score_fidelity",
        "anomaly_flag_fidelity",
        "evidence_separation",
        "evidence_sufficiency",
        "structured_response_valid",
    ]
    latencies = [item["latency_seconds"] for item in scored]
    summary = {field: sum(bool(item[field]) for item in scored) for field in fields}
    summary.update(
        {
            "case_count": len(scored),
            "unnecessary_tool_calls": sum(item["unnecessary_tool_calls"] for item in records),
            "structured_calls": sum(item["structured_valid"] for item in records),
            "structured_malformed": sum(item["structured_malformed"] for item in records),
            "unsupported_identifier_count": sum(
                len(item["unsupported_identifiers"]) for item in scored
            ),
            "unsupported_identifier_case_count": sum(
                bool(item["unsupported_identifiers"]) for item in scored
            ),
            "unsupported_score_reference_count": sum(
                len(item["unsupported_score_references"]) for item in scored
            ),
            "deterministic_fact_checks": sum(item["passed"] for item in fact_results),
            "deterministic_fact_total": len(fact_results),
            "mean_latency_seconds": round(mean(latencies), 3),
            "median_latency_seconds": round(median(latencies), 3),
            "categories": dict(sorted(Counter(item["category"] for item in scored).items())),
        }
    )
    return {"summary": summary, "facts": fact_results, "records": scored}


def summarize_llm(payload: dict) -> dict:
    records = payload["results"]
    structured = [item for item in records if item["category"] == "structured"]
    insufficiency = [
        item
        for item in records
        if item["id"] in {"structured_insufficient", "structured_uncertain"}
    ]
    durations = [item["duration_seconds"] for item in records if "duration_seconds" in item]
    return {
        "case_count": len(records),
        "passed": sum(item["passed"] for item in records),
        "schema_valid": sum(item["structured_valid"] for item in structured),
        "schema_total": len(structured),
        "malformed_output_count": sum(not item["structured_valid"] for item in structured),
        "structured_evidence_discipline": sum(item["passed"] for item in structured),
        "insufficiency_instruction_following": sum(item["passed"] for item in insufficiency),
        "insufficiency_total": len(insufficiency),
        "mean_latency_seconds": round(mean(durations), 3),
        "median_latency_seconds": round(median(durations), 3),
    }


def summarize_ml(payload: dict) -> dict:
    baseline = next(item for item in payload["experiments"] if item["config"] == "baseline")[
        "evaluation"
    ]
    impossible = next(
        item
        for item in baseline["scenario_results"]
        if item["scenario_type"] == "impossible_travel"
    )
    return {
        "config": "baseline",
        "holdout_observations": baseline["holdout_observations"],
        "scenario_count": baseline["scenario_count"],
        "scenarios_flagged": baseline["scenarios_flagged"],
        "scenario_recall": baseline["scenario_recall"],
        "false_positive_observations": baseline["false_positive_observations"],
        "normal_holdout_observations": baseline["normal_holdout_observations"],
        "false_positive_rate": baseline["false_positive_rate"],
        "flagged_precision": baseline["flagged_precision"],
        "top_5_scenario_capture": baseline["top_5_scenario_capture"],
        "top_10_scenario_capture": baseline["top_10_scenario_capture"],
        "impossible_travel": impossible,
    }
