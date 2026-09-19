"""Pure presentation helpers kept independent of Streamlit for deterministic tests."""

from collections import Counter
from math import ceil
from typing import Any

from frontend.client import AuditRecord, EventRecord, MLEvidence


def safe_text(value: Any, *, max_chars: int = 5000) -> str:
    """Bound text and remove control characters; callers render it with text primitives."""
    text = str(value)
    cleaned = "".join(char for char in text if char in "\n\t" or ord(char) >= 32)
    return cleaned[:max_chars]


def count_values(items: list[EventRecord], field: str) -> dict[str, int]:
    counts = Counter(str(getattr(item, field) or "unknown") for item in items)
    return dict(sorted(counts.items(), key=lambda pair: (-pair[1], pair[0])))


def event_rows(items: list[EventRecord]) -> list[dict[str, Any]]:
    return [
        {
            "event_id": item.event_id,
            "timestamp": item.timestamp.isoformat(),
            "user": item.user_id,
            "type": item.event_type,
            "severity": item.severity,
            "status": item.status,
            "source_ip": item.source_ip,
            "device": item.device_id,
            "country": item.country,
            "incident": item.incident_id,
        }
        for item in items
    ]


def audit_rows(items: list[AuditRecord]) -> list[dict[str, Any]]:
    return [
        {
            "id": item.audit_id,
            "timestamp": item.timestamp.isoformat(),
            "action": item.action,
            "resource": item.resource_type,
            "resource_id": item.resource_id,
            "result": item.result,
        }
        for item in items
    ]


def feature_rows(item: MLEvidence) -> list[dict[str, float | str]]:
    return [
        {"feature": name, "value": value}
        for name, value in sorted(
            item.feature_values.items(), key=lambda pair: (-abs(pair[1]), pair[0])
        )
    ]


def pagination(total: int, limit: int, offset: int) -> dict[str, int | bool]:
    pages = max(1, ceil(total / limit))
    page = min(pages, offset // limit + 1)
    return {
        "page": page,
        "pages": pages,
        "has_previous": offset > 0,
        "has_next": offset + limit < total,
        "previous_offset": max(0, offset - limit),
        "next_offset": offset + limit,
    }
