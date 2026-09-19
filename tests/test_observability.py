"""Phase 11 observability behavior without external monitoring infrastructure."""

import json
import logging

import pytest

from app.core.observability import (
    JsonFormatter,
    OperationalMetrics,
    configure_logging,
    emit,
    observability_scope,
    safe_request_id,
)


def test_request_id_validation_and_generation():
    assert safe_request_id("case-123.A") == "case-123.A"
    assert safe_request_id("bad value") != "bad value"
    assert len(safe_request_id(None)) == 32


def test_structured_json_is_correlated_and_content_safe():
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "done", (), None)
    with observability_scope(request_id_value="trace-123"):
        # Capture the shape emitted by the same safe-field boundary.
        record.structured_event = {
            "component": "tool",
            "event": "execution_complete",
            "request_id": "trace-123",
            "tool_name": "get_event",
            "outcome": "success",
        }
    payload = json.loads(JsonFormatter().format(record))
    assert payload["request_id"] == "trace-123"
    assert payload["tool_name"] == "get_event"
    assert "prompt" not in payload and "evidence" not in payload and "token" not in payload


def test_emit_rejects_unapproved_content_fields():
    with pytest.raises(ValueError, match="Unsafe structured log field"):
        emit("llm", "unsafe", prompt="private")
    with pytest.raises(ValueError, match="Unsafe structured log value"):
        emit("llm", "unsafe", state={"private": "value"})


def test_structured_api_log_replaces_duplicate_access_log():
    access = logging.getLogger("uvicorn.access")
    previous = access.disabled
    try:
        configure_logging("INFO")
        assert access.disabled
    finally:
        access.disabled = previous


def test_metrics_are_bounded_and_summarized():
    registry = OperationalMetrics()
    registry.increment("api_requests_total")
    registry.increment("tool_calls_total", label="get_event")
    registry.observe("api_request_latency_ms", 4.0)
    registry.observe("api_request_latency_ms", 6.0)
    snapshot = registry.snapshot()
    assert snapshot["counters"]["api_requests_total"] == 1
    assert snapshot["labeled_counters"]["tool_calls_total"]["get_event"] == 1
    assert snapshot["latency_ms"]["api_request_latency_ms"] == {
        "count": 2,
        "mean_ms": 5.0,
        "min_ms": 4.0,
        "max_ms": 6.0,
    }
    with pytest.raises(ValueError, match="Invalid operational metric label"):
        registry.increment("tool_calls_total", label="attacker-controlled")
    with pytest.raises(ValueError, match="Unknown operational metric"):
        registry.increment("dynamic_metric")
