"""Typed frontend HTTP client and presentation support tests."""

from pathlib import Path

import httpx
import pytest
from streamlit.testing.v1 import AppTest

from frontend.client import ApiClient, ApiClientError
from frontend.support import count_values, event_rows, feature_rows, pagination, safe_text

BASE = "http://testserver/api/v1"
TOKEN = "reader-demo-token"


def response(status: int, payload: dict) -> httpx.Response:
    return httpx.Response(status, json=payload)


def event_payload(event_id="EV000001"):
    return {
        "event_id": event_id,
        "timestamp": "2026-08-31T10:00:00Z",
        "user_id": "U105",
        "source_ip": "198.51.100.75",
        "destination_ip": None,
        "device_id": "D105",
        "event_type": "successful_login",
        "severity": "medium",
        "action": "allow",
        "status": "success",
        "country": "DE",
        "authentication_method": "password",
        "failed_attempts": 0,
        "successful_attempts": 1,
        "privileged_account": False,
        "source": "synthetic",
        "description": "Synthetic login",
        "incident_id": "INC002",
    }


def investigation_payload(*, insufficient=False):
    ml = (
        []
        if insufficient
        else [
            {
                "source_id": "ml:isolation_forest_daily_v1:user:U105:2026-08-31",
                "entity_type": "user",
                "entity_id": "U105",
                "window_start": "2026-08-31T00:00:00Z",
                "window_end": "2026-09-01T00:00:00Z",
                "anomaly_score": -0.21107408822812324,
                "flagged_anomalous": False,
                "feature_values": {"event_count": 2.0, "unique_country_count": 2.0},
                "contributing_observations": ["country diversity is elevated"],
                "model_version": "isolation_forest_daily_v1",
                "statement": "Synthetic demonstration model; not an attack determination.",
                "provenance": {"service": "AnomalyDetectionService"},
            }
        ]
    )
    policy = (
        []
        if insufficient
        else [
            {
                "kind": "policy",
                "source_id": "chunk-1",
                "source": "synthetic/policy.md",
                "text": "Fictional MFA requirement.",
                "related_ids": [],
                "citation": {
                    "document": "Synthetic Policy",
                    "source": "synthetic/policy.md",
                    "section": "MFA",
                    "page": None,
                },
                "attributes": {},
            }
        ]
    )
    return {
        "summary": "Unable to provide a grounded investigation summary."
        if insufficient
        else "Two synthetic logins were retrieved.",
        "observed_evidence": [],
        "ml_analysis": ml,
        "policy_context": policy,
        "interpretation": "No supported interpretation is available."
        if insufficient
        else "Observed and model evidence remain distinct.",
        "recommended_next_steps": [],
        "evidence_sufficiency": not insufficient,
        "sources": [] if insufficient else [ml[0]["source_id"], "chunk-1"],
        "selected_tools": ["analyze_user_anomaly"],
        "tool_results": {"analyze_user_anomaly": "unknown_entity" if insufficient else "success"},
        "errors": ["analyze_user_anomaly:unknown_entity"] if insufficient else [],
        "outcome": "insufficient_evidence" if insufficient else "complete",
        "graph_steps": 4 if insufficient else 5,
        "tool_calls": 1,
    }


def test_authentication_header_and_pagination_query():
    seen = {}

    def handler(request):
        seen["authorization"] = request.headers.get("Authorization")
        seen["query"] = dict(request.url.params)
        return response(
            200,
            {"items": [event_payload()], "total": 41, "limit": 10, "offset": 20},
        )

    client = ApiClient(BASE, TOKEN, transport=httpx.MockTransport(handler))
    page = client.events({"user_id": "U105"}, limit=10, offset=20)
    assert seen["authorization"] == f"Bearer {TOKEN}"
    assert seen["query"] == {"user_id": "U105", "limit": "10", "offset": "20"}
    assert page.total == 41 and page.items[0].event_id == "EV000001"


def test_timeout_and_backend_unavailable_are_safe():
    def timeout(_request):
        raise httpx.ReadTimeout("private timeout detail")

    with pytest.raises(ApiClientError) as exc:
        ApiClient(BASE, TOKEN, transport=httpx.MockTransport(timeout)).events()
    assert exc.value.kind == "timeout" and "private" not in str(exc.value)

    def unavailable(request):
        raise httpx.ConnectError("private socket detail", request=request)

    with pytest.raises(ApiClientError) as exc:
        ApiClient(BASE, TOKEN, transport=httpx.MockTransport(unavailable)).health()
    assert exc.value.kind == "unavailable" and "private" not in str(exc.value)


@pytest.mark.parametrize(
    "status,kind",
    [
        (401, "unauthorized"),
        (403, "forbidden"),
        (404, "not_found"),
        (422, "invalid_input"),
        (503, "dependency_unavailable"),
    ],
)
def test_api_status_mapping(status, kind):
    client = ApiClient(
        BASE,
        TOKEN,
        transport=httpx.MockTransport(lambda _request: response(status, {"detail": "secret"})),
    )
    with pytest.raises(ApiClientError) as exc:
        client.events()
    assert exc.value.kind == kind and "secret" not in str(exc.value)


def test_missing_token_is_rejected_before_network():
    client = ApiClient(
        BASE,
        "",
        transport=httpx.MockTransport(lambda _request: pytest.fail("must not call backend")),
    )
    with pytest.raises(ApiClientError, match="Enter a local demo bearer token"):
        client.events()


def test_health_parsing_is_public():
    payload = {
        "status": "ready",
        "dependencies": {
            "application": "ok",
            "postgresql": "ok",
            "qdrant": "ok",
            "ollama": "ok",
        },
    }
    client = ApiClient(BASE, transport=httpx.MockTransport(lambda _request: response(200, payload)))
    result = client.health()
    assert result.status == "ready" and result.dependencies["ollama"] == "ok"
    payload["status"] = "degraded"
    payload["dependencies"]["ollama"] = "model_missing"
    degraded = ApiClient(
        BASE, transport=httpx.MockTransport(lambda _request: response(503, payload))
    ).health()
    assert degraded.status == "degraded" and degraded.dependencies["ollama"] == "model_missing"


def test_investigation_ml_and_policy_contract_parsing():
    client = ApiClient(
        BASE,
        TOKEN,
        transport=httpx.MockTransport(lambda _request: response(200, investigation_payload())),
    )
    result = client.investigate("Is U105 unusual?")
    assert result.ml_analysis[0].anomaly_score == -0.21107408822812324
    assert result.ml_analysis[0].flagged_anomalous is False
    assert result.policy_context[0].citation["source"] == "synthetic/policy.md"
    assert result.sources == [result.ml_analysis[0].source_id, "chunk-1"]


def test_insufficient_evidence_contract_parsing():
    client = ApiClient(
        BASE,
        TOKEN,
        transport=httpx.MockTransport(
            lambda _request: response(200, investigation_payload(insufficient=True))
        ),
    )
    result = client.investigate("Anomaly score U999")
    assert result.outcome == "insufficient_evidence"
    assert result.evidence_sufficiency is False and result.ml_analysis == []


def test_render_support_data_and_safe_text():
    event = ApiClient(
        BASE,
        TOKEN,
        transport=httpx.MockTransport(lambda _request: response(200, event_payload())),
    ).event("EV000001")
    assert count_values([event], "event_type") == {"successful_login": 1}
    assert event_rows([event])[0]["country"] == "DE"
    ml = (
        ApiClient(
            BASE,
            TOKEN,
            transport=httpx.MockTransport(lambda _request: response(200, investigation_payload())),
        )
        .investigate("test")
        .ml_analysis[0]
    )
    assert feature_rows(ml)[0] == {"feature": "event_count", "value": 2.0}
    assert safe_text("safe\x00<script>\ntext") == "safe<script>\ntext"
    assert pagination(41, 10, 20) == {
        "page": 3,
        "pages": 5,
        "has_previous": True,
        "has_next": True,
        "previous_offset": 10,
        "next_offset": 30,
    }


def test_streamlit_app_loads_without_live_backend():
    path = Path(__file__).resolve().parents[1] / "frontend/app.py"
    app = AppTest.from_file(path, default_timeout=10).run()
    assert not app.exception
    assert app.title[0].value == "Security overview"
