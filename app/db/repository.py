"""Bounded, parameterized reads for future API routes and agent tools."""

from dataclasses import dataclass
from datetime import UTC, datetime
from ipaddress import ip_address
from re import fullmatch
from typing import Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.db.models import Incident, SecurityEvent

T = TypeVar("T")
MAX_PAGE_SIZE = 100


@dataclass(frozen=True)
class Page(Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True)
class EventFilters:
    user_id: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    severity: str | None = None
    event_type: str | None = None
    source_ip: str | None = None
    device_id: str | None = None
    incident_id: str | None = None


def _valid_id(value: str, prefix: str, digits: int) -> str:
    if not fullmatch(rf"{prefix}\d{{{digits}}}", value):
        raise ValueError(f"Invalid {prefix} identifier")
    return value


def _page_args(limit: int, offset: int) -> None:
    if not 1 <= limit <= MAX_PAGE_SIZE:
        raise ValueError(f"limit must be between 1 and {MAX_PAGE_SIZE}")
    if offset < 0:
        raise ValueError("offset cannot be negative")


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("time filters must be timezone-aware")
    return value.astimezone(UTC)


def get_event(session: Session, event_id: str) -> SecurityEvent | None:
    return session.get(SecurityEvent, _valid_id(event_id, "EV", 6))


def search_events(
    session: Session, filters: EventFilters | None = None, *, limit: int = 50, offset: int = 0
) -> Page[SecurityEvent]:
    _page_args(limit, offset)
    filters = filters or EventFilters()
    conditions = []
    if filters.user_id is not None:
        conditions.append(SecurityEvent.user_id == _valid_id(filters.user_id, "U", 3))
    if filters.start_time is not None:
        conditions.append(SecurityEvent.timestamp >= _utc(filters.start_time))
    if filters.end_time is not None:
        conditions.append(SecurityEvent.timestamp <= _utc(filters.end_time))
    if (
        filters.start_time
        and filters.end_time
        and _utc(filters.start_time) > _utc(filters.end_time)
    ):
        raise ValueError("start_time must not be after end_time")
    if filters.severity is not None:
        if filters.severity not in {"low", "medium", "high", "critical"}:
            raise ValueError("Invalid severity")
        conditions.append(SecurityEvent.severity == filters.severity)
    if filters.event_type is not None:
        conditions.append(SecurityEvent.event_type == filters.event_type)
    if filters.source_ip is not None:
        ip_address(filters.source_ip)
        conditions.append(SecurityEvent.source_ip == filters.source_ip)
    if filters.device_id is not None:
        conditions.append(SecurityEvent.device_id == _valid_id(filters.device_id, "D", 3))
    if filters.incident_id is not None:
        conditions.append(SecurityEvent.incident_id == _valid_id(filters.incident_id, "INC", 3))
    query: Select[tuple[SecurityEvent]] = select(SecurityEvent).where(*conditions)
    total = session.scalar(select(func.count()).select_from(SecurityEvent).where(*conditions)) or 0
    items = list(
        session.scalars(
            query.order_by(SecurityEvent.timestamp.desc(), SecurityEvent.event_id.desc())
            .limit(limit)
            .offset(offset)
        )
    )
    return Page(items, total, limit, offset)


def get_user_events(
    session: Session, user_id: str, *, limit: int = 50, offset: int = 0
) -> Page[SecurityEvent]:
    return search_events(session, EventFilters(user_id=user_id), limit=limit, offset=offset)


def get_incident(session: Session, incident_id: str) -> Incident | None:
    return session.get(Incident, _valid_id(incident_id, "INC", 3))


def get_incidents(session: Session, *, limit: int = 50, offset: int = 0) -> Page[Incident]:
    _page_args(limit, offset)
    total = session.scalar(select(func.count()).select_from(Incident)) or 0
    items = list(
        session.scalars(
            select(Incident)
            .order_by(Incident.created_at.desc(), Incident.incident_id.desc())
            .limit(limit)
            .offset(offset)
        )
    )
    return Page(items, total, limit, offset)
