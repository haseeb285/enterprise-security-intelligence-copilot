"""Low-overhead structured logs, request context, and bounded operational metrics."""

from __future__ import annotations

import json
import logging
import re
import threading
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from enum import StrEnum
from time import monotonic
from typing import Any
from uuid import uuid4

REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
LOGGER_NAME = "esic.observability"


class ErrorCategory(StrEnum):
    validation_error = "validation_error"
    authentication_error = "authentication_error"
    authorization_error = "authorization_error"
    database_unavailable = "database_unavailable"
    vector_store_unavailable = "vector_store_unavailable"
    llm_unavailable = "llm_unavailable"
    llm_timeout = "llm_timeout"
    llm_validation_error = "llm_validation_error"
    model_artifact_unavailable = "model_artifact_unavailable"
    insufficient_observation = "insufficient_observation"
    tool_failure = "tool_failure"
    internal_error = "internal_error"


_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_metrics: ContextVar[OperationalMetrics | None] = ContextVar("metrics", default=None)

TOOLS = {
    "search_policy",
    "search_security_events",
    "get_user_events",
    "get_incident",
    "get_event",
    "analyze_user_anomaly",
}
DEPENDENCIES = {"postgresql", "qdrant", "ollama", "model_artifact"}
COUNTERS = {
    "api_requests_total": None,
    "api_errors_total": None,
    "investigations_total": None,
    "investigation_failures_total": None,
    "retrieval_calls_total": None,
    "retrieval_insufficient_total": None,
    "llm_calls_total": None,
    "llm_failures_total": None,
    "llm_timeouts_total": None,
    "ml_inference_calls_total": None,
    "ml_inference_failures_total": None,
    "tool_calls_total": TOOLS,
    "tool_failures_total": TOOLS,
    "dependency_failures_total": DEPENDENCIES,
}
TIMERS = {
    "api_request_latency_ms": None,
    "investigation_latency_ms": None,
    "retrieval_latency_ms": None,
    "llm_latency_ms": None,
    "ml_inference_latency_ms": None,
    "tool_latency_ms": TOOLS,
}
LOG_FIELDS = {
    "method",
    "route",
    "status_code",
    "duration_ms",
    "outcome",
    "error_category",
    "provider",
    "model",
    "structured",
    "output_tokens",
    "top_k",
    "result_count",
    "insufficient_evidence",
    "highest_score",
    "collection",
    "embedding_model",
    "tools_selected",
    "tool_name",
    "tool_calls",
    "graph_steps",
    "evidence_categories",
    "model_version",
    "anomaly_flag",
    "observation_available",
    "dependency",
    "state",
}


def request_id() -> str | None:
    return _request_id.get()


def safe_request_id(value: str | None) -> str:
    return value if value and REQUEST_ID_RE.fullmatch(value) else uuid4().hex


@contextmanager
def observability_scope(
    *, request_id_value: str | None = None, registry: OperationalMetrics | None = None
) -> Iterator[str | None]:
    id_token = _request_id.set(
        request_id_value if request_id_value is not None else _request_id.get()
    )
    metric_token = _metrics.set(registry if registry is not None else _metrics.get())
    try:
        yield _request_id.get()
    finally:
        _metrics.reset(metric_token)
        _request_id.reset(id_token)


class OperationalMetrics:
    """Process-local bounded counters and latency summaries."""

    def __init__(self) -> None:
        self.started = monotonic()
        self._lock = threading.Lock()
        self._counters: dict[tuple[str, str | None], int] = defaultdict(int)
        self._timers: dict[tuple[str, str | None], dict[str, float]] = {}

    @staticmethod
    def _validate(definitions: dict, name: str, label: str | None) -> None:
        if name not in definitions:
            raise ValueError("Unknown operational metric")
        allowed = definitions[name]
        if (allowed is None and label is not None) or (
            allowed is not None and label not in allowed
        ):
            raise ValueError("Invalid operational metric label")

    def increment(self, name: str, *, label: str | None = None, amount: int = 1) -> None:
        self._validate(COUNTERS, name, label)
        if amount < 0:
            raise ValueError("Metric increments cannot be negative")
        with self._lock:
            self._counters[(name, label)] += amount

    def observe(self, name: str, duration_ms: float, *, label: str | None = None) -> None:
        self._validate(TIMERS, name, label)
        value = max(0.0, float(duration_ms))
        with self._lock:
            item = self._timers.setdefault(
                (name, label), {"count": 0.0, "total_ms": 0.0, "min_ms": value, "max_ms": value}
            )
            item["count"] += 1
            item["total_ms"] += value
            item["min_ms"] = min(item["min_ms"], value)
            item["max_ms"] = max(item["max_ms"], value)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            counters = dict(self._counters)
            timers = {key: dict(value) for key, value in self._timers.items()}
        plain = {
            name: counters.get((name, None), 0)
            for name, labels in COUNTERS.items()
            if labels is None
        }
        labeled = {
            name: {label: counters.get((name, label), 0) for label in sorted(labels)}
            for name, labels in COUNTERS.items()
            if labels is not None
        }

        def timing(item: dict[str, float]) -> dict[str, float | int]:
            count = int(item["count"])
            return {
                "count": count,
                "mean_ms": round(item["total_ms"] / count, 3),
                "min_ms": round(item["min_ms"], 3),
                "max_ms": round(item["max_ms"], 3),
            }

        plain_timers = {
            name: timing(timers[(name, None)])
            for name, labels in TIMERS.items()
            if labels is None and (name, None) in timers
        }
        labeled_timers = {
            name: {
                label: timing(timers[(name, label)])
                for label in sorted(labels)
                if (name, label) in timers
            }
            for name, labels in TIMERS.items()
            if labels is not None
        }
        return {
            "uptime_seconds": round(monotonic() - self.started, 3),
            "counters": plain,
            "labeled_counters": labeled,
            "latency_ms": plain_timers,
            "labeled_latency_ms": labeled_timers,
        }


DEFAULT_METRICS = OperationalMetrics()


def metrics() -> OperationalMetrics:
    return _metrics.get() or DEFAULT_METRICS


def emit(component: str, event: str, *, level: int = logging.INFO, **fields: Any) -> None:
    unknown = set(fields) - LOG_FIELDS
    if unknown:
        raise ValueError("Unsafe structured log field")
    clean: dict[str, Any] = {}
    for key, value in fields.items():
        if value is None:
            continue
        if isinstance(value, StrEnum):
            value = value.value
        if isinstance(value, str):
            value = value[:128]
        elif isinstance(value, (list, tuple)):
            value = [str(item)[:64] for item in value[:10]]
        elif not isinstance(value, (int, float, bool)):
            raise ValueError("Unsafe structured log value")
        clean[key] = value
    logging.getLogger(LOGGER_NAME).log(
        level,
        event,
        extra={
            "structured_event": {
                "component": component[:64],
                "event": event[:64],
                "request_id": request_id(),
                **clean,
            }
        },
    )


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        event = getattr(record, "structured_event", {})
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname.lower(),
            **event,
        }
        return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def configure_logging(level: str) -> None:
    # The structured API completion event replaces Uvicorn's second access line.
    logging.getLogger("uvicorn.access").disabled = True
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False
    if not any(getattr(handler, "esic_json", False) for handler in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        handler.esic_json = True  # type: ignore[attr-defined]
        logger.addHandler(handler)


def category_for_status(status_code: int) -> ErrorCategory | None:
    if status_code == 401:
        return ErrorCategory.authentication_error
    if status_code == 403:
        return ErrorCategory.authorization_error
    if status_code in {400, 413, 422}:
        return ErrorCategory.validation_error
    if status_code == 503:
        return ErrorCategory.internal_error
    if status_code >= 500:
        return ErrorCategory.internal_error
    return None
