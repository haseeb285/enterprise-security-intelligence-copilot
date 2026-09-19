"""Causal feature engineering for fixed UTC user/source daily observations."""

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal, Protocol

import numpy as np

EntityType = Literal["user", "source_ip"]

FEATURE_NAMES = (
    "event_count",
    "failed_login_count",
    "successful_login_count",
    "failed_to_success_ratio",
    "unique_source_ip_count",
    "unique_country_count",
    "unique_device_count",
    "unusual_hour_event_count",
    "unusual_hour_fraction",
    "privileged_event_count",
    "privileged_event_fraction",
    "firewall_block_count",
    "firewall_allow_count",
    "endpoint_alert_count",
    "privilege_change_count",
    "non_auth_event_count",
    "non_auth_event_fraction",
    "country_transition_count",
    "active_hour_count",
    "max_events_15m",
)

FORBIDDEN_FEATURE_FIELDS = frozenset(
    {
        "scenario_id",
        "scenario_type",
        "is_anomaly",
        "anomaly_label",
        "ground_truth",
        "expected_investigation_reason",
        "incident_id",
        "severity",
        "description",
    }
)


class EventLike(Protocol):
    event_id: str
    timestamp: datetime
    user_id: str | None
    source_ip: str
    device_id: str | None
    event_type: str
    country: str | None
    privileged_account: bool | None


@dataclass(frozen=True)
class Observation:
    entity_type: EntityType
    entity_id: str
    window_start: datetime
    window_end: datetime
    features: dict[str, float]
    event_ids: tuple[str, ...]


def _aware(value: datetime, name: str) -> datetime:
    if value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(UTC)


def _event_timestamp(event: EventLike) -> datetime:
    """Normalize UTC database timestamps; SQLite drops tzinfo in isolated tests."""
    if event.timestamp.utcoffset() is None:
        return event.timestamp.replace(tzinfo=UTC)
    return event.timestamp.astimezone(UTC)


def _validate_schema() -> None:
    forbidden = set(FEATURE_NAMES) & FORBIDDEN_FEATURE_FIELDS
    if forbidden:
        raise ValueError(f"Leakage fields in feature schema: {sorted(forbidden)}")


def _max_events_in_15m(events: list[EventLike]) -> int:
    timestamps = sorted(_event_timestamp(event) for event in events)
    active: deque[datetime] = deque()
    maximum = 0
    for timestamp in timestamps:
        boundary = timestamp - timedelta(minutes=15)
        while active and active[0] < boundary:
            active.popleft()
        active.append(timestamp)
        maximum = max(maximum, len(active))
    return maximum


def _values(events: list[EventLike]) -> dict[str, float]:
    _validate_schema()
    count = len(events)
    failed = sum(event.event_type == "failed_login" for event in events)
    succeeded = sum(event.event_type == "successful_login" for event in events)
    unusual = sum(
        _event_timestamp(event).hour < 6 or _event_timestamp(event).hour >= 22 for event in events
    )
    privileged = sum(bool(event.privileged_account) for event in events)
    non_auth = sum(event.event_type not in {"failed_login", "successful_login"} for event in events)
    auth_countries = [
        event.country
        for event in sorted(events, key=_event_timestamp)
        if event.event_type in {"failed_login", "successful_login"} and event.country is not None
    ]
    return {
        "event_count": float(count),
        "failed_login_count": float(failed),
        "successful_login_count": float(succeeded),
        "failed_to_success_ratio": failed / (succeeded + 1),
        "unique_source_ip_count": float(len({event.source_ip for event in events})),
        "unique_country_count": float(
            len({event.country for event in events if event.country is not None})
        ),
        "unique_device_count": float(
            len({event.device_id for event in events if event.device_id is not None})
        ),
        "unusual_hour_event_count": float(unusual),
        "unusual_hour_fraction": unusual / count,
        "privileged_event_count": float(privileged),
        "privileged_event_fraction": privileged / count,
        "firewall_block_count": float(
            sum(event.event_type == "firewall_block" for event in events)
        ),
        "firewall_allow_count": float(
            sum(event.event_type == "firewall_allow" for event in events)
        ),
        "endpoint_alert_count": float(
            sum(event.event_type == "suspicious_process" for event in events)
        ),
        "privilege_change_count": float(
            sum(event.event_type == "privilege_change" for event in events)
        ),
        "non_auth_event_count": float(non_auth),
        "non_auth_event_fraction": non_auth / count,
        "country_transition_count": float(
            sum(
                first != second
                for first, second in zip(auth_countries, auth_countries[1:], strict=False)
            )
        ),
        "active_hour_count": float(len({_event_timestamp(event).hour for event in events})),
        "max_events_15m": float(_max_events_in_15m(events)),
    }


def build_observation(
    events: list[EventLike],
    *,
    entity_type: EntityType,
    entity_id: str,
    window_start: datetime,
    window_end: datetime,
) -> Observation:
    """Build one observation using only events within [start, end)."""
    start = _aware(window_start, "window_start")
    end = _aware(window_end, "window_end")
    if start >= end:
        raise ValueError("window_start must precede window_end")
    selected = [
        event
        for event in events
        if start <= _event_timestamp(event) < end
        and (
            (entity_type == "user" and event.user_id == entity_id)
            or (
                entity_type == "source_ip"
                and event.user_id is None
                and event.source_ip == entity_id
            )
        )
    ]
    if not selected:
        raise ValueError("observation has no events")
    selected.sort(key=lambda event: (_event_timestamp(event), event.event_id))
    return Observation(
        entity_type=entity_type,
        entity_id=entity_id,
        window_start=start,
        window_end=end,
        features=_values(selected),
        event_ids=tuple(event.event_id for event in selected),
    )


def build_daily_observations(
    events: list[EventLike], period_start: datetime, period_end: datetime
) -> list[Observation]:
    """Aggregate active entities into non-overlapping UTC calendar-day windows."""
    start = _aware(period_start, "period_start")
    end = _aware(period_end, "period_end")
    if start >= end:
        raise ValueError("period_start must precede period_end")
    grouped: dict[tuple[datetime, EntityType, str], list[EventLike]] = defaultdict(list)
    for event in events:
        timestamp = _event_timestamp(event)
        if not start <= timestamp < end:
            continue
        window_start = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        if event.user_id is not None:
            entity_type: EntityType = "user"
            entity_id = event.user_id
        else:
            entity_type = "source_ip"
            entity_id = event.source_ip
        grouped[(window_start, entity_type, entity_id)].append(event)
    observations = []
    for (window_start, entity_type, entity_id), group in grouped.items():
        observations.append(
            build_observation(
                group,
                entity_type=entity_type,
                entity_id=entity_id,
                window_start=window_start,
                window_end=window_start + timedelta(days=1),
            )
        )
    return sorted(
        observations,
        key=lambda item: (item.window_start, item.entity_type, item.entity_id),
    )


def chronological_split(
    observations: list[Observation], cutoff: datetime
) -> tuple[list[Observation], list[Observation]]:
    split = _aware(cutoff, "cutoff")
    training = [item for item in observations if item.window_start < split]
    holdout = [item for item in observations if item.window_start >= split]
    if not training or not holdout:
        raise ValueError("chronological split needs nonempty training and holdout observations")
    if max(item.window_end for item in training) > split:
        raise ValueError("training observation crosses cutoff")
    return training, holdout


def feature_matrix(observations: list[Observation]) -> np.ndarray:
    _validate_schema()
    if not observations:
        raise ValueError("feature matrix needs observations")
    return np.asarray(
        [[item.features[name] for name in FEATURE_NAMES] for item in observations],
        dtype=float,
    )
