"""Phase 8 typed ML evidence, routing, alignment, and partial-failure contracts."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.agent.graph import InvestigationAgent
from app.agent.routing import validated_decisions
from app.agent.schemas import EvidenceRecord, MLEvidence, RoutePlan, Synthesis, ToolDecision
from app.agent.tools import AgentTools, ToolExecutionError
from app.ml.schemas import AnomalyResult
from app.ml.service import InsufficientHistoryError, UnknownUserError

START = datetime(2026, 8, 31, tzinfo=UTC)
END = START + timedelta(days=1)
SCORE = -0.21107408822812324


class Provider:
    def __init__(self, tools, synthesis=None):
        self.tools = tools
        self.synthesis = synthesis or Synthesis(
            summary="Synthetic evidence was retrieved.",
            interpretation="The observed facts and model analysis should be reviewed separately.",
            recommended_next_steps=["Review related events."],
        )
        self.calls = []

    def generate_structured(self, prompt, schema, system=None):
        self.calls.append((schema, prompt, system))
        value = (
            RoutePlan(classification="multi", tools=self.tools)
            if schema is RoutePlan
            else self.synthesis
        )
        return SimpleNamespace(value=value)


def ml_evidence(flagged=False):
    return MLEvidence(
        source_id="ml:isolation_forest_daily_v1:user:U105:2026-08-31",
        entity_type="user",
        entity_id="U105",
        window_start=START,
        window_end=END,
        anomaly_score=SCORE,
        flagged_anomalous=flagged,
        feature_values={"event_count": 2.0, "unique_country_count": 2.0},
        contributing_observations=["country diversity is elevated"],
        model_version="isolation_forest_daily_v1",
        statement=(
            "Behavioral anomaly score from a synthetic-data demonstration model; "
            "this is not an attack determination."
        ),
        provenance={
            "service": "app.ml.service.AnomalyDetectionService",
            "model_version": "isolation_forest_daily_v1",
            "data_source": "postgresql.security_events",
        },
    )


class IntegratedTools:
    def __init__(self, *, fail_ml=False, empty_policy=False):
        self.calls = []
        self.fail_ml = fail_ml
        self.empty_policy = empty_policy

    def run(self, decision, _request, _role):
        name = decision.name.value
        self.calls.append(decision)
        if name == "analyze_user_anomaly":
            if self.fail_ml:
                raise ToolExecutionError("dependency_failure")
            return [ml_evidence()]
        if name == "search_policy":
            if self.empty_policy:
                return []
            return [
                EvidenceRecord(
                    kind="policy",
                    source_id="chunk-mfa",
                    source="synthetic/mfa.md",
                    text="Fictional MFA controls apply to remote access.",
                    citation={
                        "document": "Synthetic Access Policy",
                        "source": "synthetic/mfa.md",
                        "section": "MFA",
                        "page": None,
                    },
                )
            ]
        return [
            EvidenceRecord(
                kind="event",
                source_id=f"EV00010{index}",
                source="postgresql.security_events",
                text="Synthetic authentication event",
                related_ids=["U105"],
                attributes={
                    "timestamp": (START + timedelta(hours=index)).isoformat(),
                    "country": "DE" if index == 5 else "JP",
                },
            )
            for index in (5, 6)
        ]


@pytest.mark.parametrize(
    "query,proposal,expected",
    [
        ("What does the remote access policy require?", ["search_policy"], ["search_policy"]),
        (
            "Show failed logins for U104.",
            ["analyze_user_anomaly", "search_security_events"],
            ["search_security_events"],
        ),
        (
            "Is U104 behaving unusually?",
            ["analyze_user_anomaly", "search_security_events"],
            ["analyze_user_anomaly", "search_security_events"],
        ),
        (
            "Investigate suspicious activity for U104 and determine whether relevant "
            "policy controls apply.",
            ["search_policy", "search_security_events", "analyze_user_anomaly"],
            ["search_policy", "search_security_events", "analyze_user_anomaly"],
        ),
        (
            "What is the anomaly score for U104?",
            ["search_policy", "analyze_user_anomaly"],
            ["analyze_user_anomaly"],
        ),
        (
            "Do MFA policy controls apply to failed login events for U104?",
            ["search_policy", "search_security_events"],
            ["search_policy", "search_security_events"],
        ),
    ],
)
def test_selective_integrated_routing(query, proposal, expected):
    decisions = validated_decisions(RoutePlan(classification="multi", tools=proposal), query)
    assert [item.name.value for item in decisions] == expected


def test_typed_ml_evidence_and_exact_score_fidelity():
    provider = Provider(["analyze_user_anomaly"])
    result = InvestigationAgent(provider, IntegratedTools()).run(
        "What is the anomaly score for U105 on 2026-08-31?", "reader"
    )
    assert result.observed_evidence == [] and result.policy_context == []
    assert result.ml_analysis[0].anomaly_score == SCORE
    assert result.ml_analysis[0].flagged_anomalous is False
    assert result.ml_analysis[0].feature_values["unique_country_count"] == 2.0
    assert result.sources == ["ml:isolation_forest_daily_v1:user:U105:2026-08-31"]
    assert "ML_ANALYSIS" in provider.calls[1][1]
    assert "not a probability" in provider.calls[1][2]
    assert "no observed event evidence" in result.interpretation


def test_temporal_alignment_for_date_timestamp_and_invalid_range():
    date_request = "Is U105 behaving unusually on 2026-08-31?"
    decisions = validated_decisions(
        RoutePlan(classification="multi", tools=["search_security_events", "analyze_user_anomaly"]),
        date_request,
    )
    assert {(item.start_time, item.end_time) for item in decisions} == {(START, END)}
    at = datetime(2026, 9, 1, 12, tzinfo=UTC)
    decisions = validated_decisions(
        RoutePlan(classification="events", tools=["analyze_user_anomaly"]),
        "What is the anomaly score for U105 at 2026-09-01T12:00:00Z?",
    )
    assert decisions[0].start_time == at - timedelta(hours=24)
    assert decisions[0].end_time == at
    with pytest.raises(ValueError, match="Invalid time range"):
        validated_decisions(
            RoutePlan(classification="events", tools=["analyze_user_anomaly"]),
            "Anomaly score U105 from 2026-09-02T00:00:00Z to 2026-09-01T00:00:00Z",
        )


def test_ml_failure_returns_partial_event_evidence():
    tools = IntegratedTools(fail_ml=True)
    result = InvestigationAgent(
        Provider(["search_security_events", "analyze_user_anomaly"]), tools
    ).run("Is U105 behaving unusually on 2026-08-31?", "reader")
    assert result.outcome == "partial_evidence"
    assert result.evidence_sufficiency is False
    assert len(result.observed_evidence) == 2 and result.ml_analysis == []
    assert result.tool_results["analyze_user_anomaly"] == "dependency_failure"
    assert "analyze_user_anomaly:dependency_failure" in result.errors
    assert "ML analysis was unavailable" in result.interpretation


def test_impossible_travel_disagreement_remains_visible():
    tools = IntegratedTools()
    result = InvestigationAgent(
        Provider(["search_security_events", "analyze_user_anomaly"]), tools
    ).run("Is U105 behaving unusually on 2026-08-31?", "reader")
    assert {item.attributes["country"] for item in result.observed_evidence} == {"DE", "JP"}
    assert result.ml_analysis[0].flagged_anomalous is False
    assert result.ml_analysis[0].anomaly_score == SCORE


class AnomalyFake:
    def __init__(self, failure=None):
        self.failure = failure
        self.calls = []

    def default_user_window(self, user_id):
        self.calls.append(("default", user_id))
        if self.failure:
            raise self.failure
        return START, END

    def analyze_user(self, user_id, start, end):
        self.calls.append(("analyze", user_id, start, end))
        if self.failure:
            raise self.failure
        return AnomalyResult(
            entity_type="user",
            entity_id=user_id,
            window_start=start,
            window_end=end,
            anomaly_score=SCORE,
            flagged_anomalous=False,
            feature_values={"event_count": 2.0},
            contributing_observations=[
                "no individual feature exceeded its training 90th percentile"
            ],
            model_version="isolation_forest_daily_v1",
        )


def test_ml_tool_reuses_service_default_and_maps_safe_failures():
    fake = AnomalyFake()
    tools = AgentTools(SimpleNamespace(), lambda: object(), fake)
    result = tools.run(
        ToolDecision(name="analyze_user_anomaly", user_id="U105"),
        "What is the anomaly score for U105?",
        "reader",
    )[0]
    assert result.anomaly_score == SCORE
    assert fake.calls == [("default", "U105"), ("analyze", "U105", START, END)]

    for failure, code in [
        (UnknownUserError("U999"), "unknown_entity"),
        (InsufficientHistoryError("too few"), "insufficient_history"),
        (FileNotFoundError("private model path"), "dependency_failure"),
        (RuntimeError("secret inference detail"), "inference_failure"),
    ]:
        broken = AgentTools(SimpleNamespace(), lambda: object(), AnomalyFake(failure))
        with pytest.raises(ToolExecutionError) as exc:
            broken.run(
                ToolDecision(name="analyze_user_anomaly", user_id="U105"),
                "What is the anomaly score for U105?",
                "reader",
            )
        assert exc.value.code == code
        assert "private model path" not in str(exc.value)


def test_default_event_window_matches_anomaly_window():
    filters_seen = []

    def events(filters, limit, offset):
        filters_seen.append((filters, limit, offset))
        return SimpleNamespace(items=[])

    fake = AnomalyFake()
    tools = AgentTools(SimpleNamespace(events=events), lambda: object(), fake)
    tools.run(
        ToolDecision(name="search_security_events", user_id="U105"),
        "Is U105 behaving unusually?",
        "reader",
    )
    filters, limit, offset = filters_seen[0]
    assert (filters.start_time, filters.end_time) == (START, END)
    assert (limit, offset) == (5, 0)


def test_invented_anomaly_score_and_write_action_are_filtered():
    synthesis = Synthesis(
        summary="The anomaly score is 0.99.",
        interpretation="The score proves compromise.",
        recommended_next_steps=["Disable U105.", "Review related events."],
    )
    result = InvestigationAgent(
        Provider(["analyze_user_anomaly"], synthesis), IntegratedTools()
    ).run("What is the anomaly score for U105 on 2026-08-31?", "reader")
    assert result.outcome == "complete"
    assert "0.99" not in result.summary
    assert "anomaly_score_reference_filtered" in result.errors
    assert result.recommended_next_steps == ["Review related events."]
    assert "write_action_recommendation_filtered" in result.errors
