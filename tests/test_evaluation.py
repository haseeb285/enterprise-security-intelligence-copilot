"""Phase 10 suite loading, layered metrics, fidelity, and safety tests."""

import json

import pytest

from app.agent.evaluate_integrated import select_cases
from app.evaluation.cases import case_counts, load_suite
from app.evaluation.metrics import score_integrated, summarize_ml
from app.evaluation.run import _sanitized, _write
from app.evaluation.safety import evaluate_safety
from app.rag.evaluate import evaluate as evaluate_retrieval
from app.rag.service import Citation, Evidence, Retrieval


def test_versioned_case_loading_is_deterministic_and_tools_are_predefined():
    first, second = load_suite(), load_suite()
    assert first == second and first["version"] == "1.0.0"
    assert case_counts(first)["integrated"]["total"] == 20
    assert case_counts(first)["retrieval"]["total"] == 47
    assert all("expected_tools" in item for item in first["cases"]["integrated"])


def test_retrieval_metric_calculation_separates_ranking_and_gate():
    target = Evidence(
        "Sixteen characters.",
        0.9,
        "chunk-1",
        Citation("Password Policy", "synthetic/password.md", "Passwords", None),
    )
    irrelevant = Evidence(
        "Other.", 0.7, "chunk-2", Citation("Other", "synthetic/other.md", "Other", None)
    )

    class Service:
        def retrieve(self, query, top_k):
            return (
                Retrieval((target, irrelevant), False)
                if query == "password"
                else Retrieval((irrelevant,), False)
            )

    result = evaluate_retrieval(
        Service(),
        [
            {
                "id": "positive",
                "query": "password",
                "document": "Password Policy",
                "section": "Passwords",
            },
            {"id": "negative", "query": "lunch", "document": None},
        ],
        0.805,
    )
    assert result["recall_at_1"] == 1
    assert result["answerable_acceptance_rate"] == 1
    assert result["unanswerable_rejection_rate"] == 1
    assert result["citation_source_correct"] == 1


def integrated_fixture(summary="Observed EV000001 for U001."):
    response = {
        "summary": summary,
        "observed_evidence": [
            {
                "kind": "event",
                "source_id": "EV000001",
                "source": "postgresql.security_events",
                "text": "Synthetic event",
                "related_ids": ["U001", "INC001"],
                "citation": None,
                "attributes": {"country": "DE", "incident_id": "INC001"},
            }
        ],
        "ml_analysis": [],
        "policy_context": [],
        "interpretation": "Uncertainty is preserved.",
        "recommended_next_steps": [],
        "evidence_sufficiency": True,
        "sources": ["EV000001"],
        "selected_tools": ["get_event"],
        "tool_results": {"get_event": "success"},
        "errors": [],
        "outcome": "complete",
        "graph_steps": 5,
        "tool_calls": 1,
    }
    return {
        "id": "event",
        "selection_correct": True,
        "unnecessary_tool_calls": 0,
        "task_complete": True,
        "structured_valid": 2,
        "structured_malformed": 0,
        "anomaly_score_fidelity": True,
        "anomaly_flag_fidelity": True,
        "latency_seconds": 1.5,
        "response": response,
    }


def test_integrated_fidelity_and_unsupported_source_detection():
    case = {"id": "event", "category": "event", "expected_outcome": "complete"}
    clean = score_integrated([case], [integrated_fixture()], [])
    assert clean["summary"]["source_provenance_fidelity"] == 1
    assert clean["summary"]["unsupported_identifier_count"] == 0
    invented = integrated_fixture("Observed EV999999 for U001.")
    scored = score_integrated([case], [invented], [])
    assert scored["summary"]["unsupported_identifier_count"] == 1
    assert scored["records"][0]["unsupported_identifiers"] == ["EV999999"]


def test_integrated_fidelity_detects_inexact_score_reference():
    case = {"id": "event", "category": "event", "expected_outcome": "complete"}
    record = integrated_fixture("The ML analysis returned a score of 0.117.")
    record["response"]["ml_analysis"] = [
        {
            "source_id": "ml:model:user:U001:2026-08-31",
            "entity_id": "U001",
            "anomaly_score": 0.11672999155466501,
            "flagged_anomalous": True,
        }
    ]
    record["response"]["sources"].append("ml:model:user:U001:2026-08-31")
    scored = score_integrated([case], [record], [])
    assert scored["summary"]["anomaly_score_fidelity"] == 0
    assert scored["summary"]["unsupported_score_reference_count"] == 1


def test_failure_case_scoring_and_prompt_injection_contracts():
    suite = load_suite()
    result = evaluate_safety(suite["cases"]["safety"])
    assert result["case_count"] == 13
    assert result["passed"] == 13
    injection = [item for item in result["records"] if item["category"] == "prompt_injection"]
    assert all(item["details"]["masked_for_synthesis"] for item in injection)


def test_impossible_travel_regression_metrics_are_preserved():
    evaluation = {
        "holdout_observations": 1,
        "scenario_count": 1,
        "scenarios_flagged": 0,
        "scenario_recall": 0.0,
        "flagged_observations": 0,
        "flagged_scenario_observations": 0,
        "false_positive_observations": 0,
        "normal_holdout_observations": 0,
        "false_positive_rate": 0.0,
        "flagged_precision": 0.0,
        "top_5_scenario_capture": 0,
        "top_10_scenario_capture": 0,
        "scenario_results": [
            {
                "scenario_id": "SCN002",
                "scenario_type": "impossible_travel",
                "observation_keys": ["user:U105:2026-08-31T00:00:00+00:00"],
                "flagged": False,
                "best_rank": 325,
                "best_score": -0.21107408822812324,
            }
        ],
    }
    result = summarize_ml({"experiments": [{"config": "baseline", "evaluation": evaluation}]})
    assert result["impossible_travel"]["flagged"] is False
    assert result["impossible_travel"]["best_score"] == -0.21107408822812324


def test_result_serialization_omits_case_level_responses(tmp_path):
    payload = {
        "suite_version": "1.0.0",
        "notice": "SYNTHETIC DEMONSTRATION DATA",
        "case_counts": {},
        "offline": {
            "completed": True,
            "retrieval": {"recall_at_1": 1.0, "records": [{"private": "detail"}]},
            "ml": {"scenario_recall": 0.5},
            "safety": {"passed": 1, "records": [{"private": "detail"}]},
        },
    }
    path = tmp_path / "result.json"
    summary = _sanitized(payload)
    _write(path, summary)
    loaded = json.loads(path.read_text())
    assert "records" not in loaded["offline"]["retrieval"]
    assert "records" not in loaded["offline"]["safety"]


def test_score_integrated_rejects_mismatched_case_ids():
    with pytest.raises(ValueError, match="versioned case set"):
        score_integrated(
            [{"id": "expected", "category": "event", "expected_outcome": "complete"}],
            [integrated_fixture()],
            [],
        )


def test_integrated_cli_empty_selection_means_complete_suite():
    cases = [{"id": "one"}, {"id": "two"}]
    assert select_cases(cases, []) == cases
    assert select_cases(cases, ["two"]) == [{"id": "two"}]
    with pytest.raises(ValueError, match="Unknown case ID"):
        select_cases(cases, ["missing"])
