"""Repository, schema, and seed behavior using a fast isolated SQLite fixture.

Production migrations are verified separately against PostgreSQL; create_all is used
only here to keep unit tests independent of Docker.
"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine, delete, event, func, insert, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import AuditLog, Base, Incident, SecurityEvent
from app.db.repository import (
    EventFilters,
    get_event,
    get_incident,
    get_incidents,
    get_user_events,
    search_events,
)
from app.db.seed import seed_database
from app.db.synthetic import SYNTHETIC_NOTICE


@pytest.fixture
def seeded_database(tmp_path: Path):
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        connection.execute(text("INSERT INTO alembic_version VALUES ('20260918_01')"))
    truth_path = tmp_path / "ground_truth.json"
    result = seed_database(engine, normal_event_count=200, ground_truth_path=truth_path)
    yield engine, result, truth_path
    engine.dispose()


def test_seed_is_idempotent_and_truth_is_separate(seeded_database) -> None:
    engine, result, path = seeded_database
    assert result.status == "seeded"
    assert (result.users, result.devices, result.events, result.incidents, result.scenarios) == (
        120,
        140,
        265,
        6,
        6,
    )
    again = seed_database(engine, normal_event_count=200, ground_truth_path=path)
    assert again.status == "already_seeded"
    assert again.events == result.events
    with pytest.raises(RuntimeError, match="Existing seed differs"):
        seed_database(engine, seed=43, normal_event_count=200, ground_truth_path=path)
    truth = json.loads(path.read_text(encoding="utf-8"))
    assert truth["notice"] == SYNTHETIC_NOTICE
    assert len(truth["scenarios"]) == 6
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(SecurityEvent)) == 265
        assert session.scalar(select(func.count()).select_from(Incident)) == 6


def test_explicit_reset_changes_seed_without_duplication(seeded_database) -> None:
    engine, _, path = seeded_database
    changed = seed_database(
        engine, seed=43, normal_event_count=200, reset=True, ground_truth_path=path
    )
    assert changed.status == "seeded"
    assert changed.events == 265
    assert json.loads(path.read_text(encoding="utf-8"))["seed"] == 43
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(SecurityEvent)) == 265


def test_reset_refuses_populated_database_without_seed_marker(seeded_database) -> None:
    engine, _, path = seeded_database
    with Session(engine) as session, session.begin():
        session.execute(delete(AuditLog))
    with pytest.raises(RuntimeError, match="without a synthetic seed marker"):
        seed_database(engine, reset=True, normal_event_count=200, ground_truth_path=path)


def test_seed_requires_migration() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    try:
        Base.metadata.create_all(engine)
        with pytest.raises(RuntimeError, match="alembic upgrade head"):
            seed_database(engine, normal_event_count=1)
    finally:
        engine.dispose()


def test_repository_filters_and_pagination(seeded_database) -> None:
    engine, _, _ = seeded_database
    with Session(engine) as session:
        page = get_user_events(session, "U104", limit=10)
        assert page.total > 25
        assert len(page.items) == 10
        assert all(item.user_id == "U104" for item in page.items)
        second = get_user_events(session, "U104", limit=10, offset=10)
        assert not {item.event_id for item in page.items} & {item.event_id for item in second.items}
        assert search_events(session).limit == 50
        assert len(search_events(session).items) == 50
        exact = search_events(session, EventFilters(source_ip="203.0.113.201"))
        assert exact.total == 25
        assert all(item.source_ip == "203.0.113.201" for item in exact.items)
        high = search_events(session, EventFilters(severity="high", event_type="failed_login"))
        assert high.total >= 25
        assert all(
            item.severity == "high" and item.event_type == "failed_login" for item in high.items
        )
        device = search_events(session, EventFilters(device_id="D107"))
        assert all(item.device_id == "D107" for item in device.items)
        incident_events = search_events(session, EventFilters(incident_id="INC001"))
        assert incident_events.total == 25
        cutoff = datetime(2026, 8, 31, tzinfo=UTC)
        recent = search_events(session, EventFilters(start_time=cutoff))
        assert recent.total == 65
        assert all(item.timestamp >= cutoff.replace(tzinfo=None) for item in recent.items)
        older = search_events(session, EventFilters(end_time=cutoff - timedelta(seconds=1)))
        assert older.total == 200
        assert get_event(session, incident_events.items[0].event_id) is not None
        assert get_event(session, "EV999999") is None
        assert get_incident(session, "INC001") is not None
        assert get_incident(session, "INC999") is None
        assert get_incidents(session, limit=2).total == 6
        assert len(get_incidents(session, limit=2).items) == 2


def test_invalid_queries_and_model_constraints(seeded_database) -> None:
    engine, _, _ = seeded_database
    with Session(engine) as session:
        with pytest.raises(ValueError):
            get_event(session, "EV1 OR 1=1")
        with pytest.raises(ValueError):
            get_incident(session, "INCbad")
        with pytest.raises(ValueError):
            get_user_events(session, "Ubad")
        with pytest.raises(ValueError):
            search_events(session, limit=101)
        with pytest.raises(ValueError):
            search_events(session, EventFilters(start_time=datetime(2026, 8, 1)))
        with pytest.raises(ValueError):
            search_events(session, EventFilters(source_ip="not-an-ip"))
        with pytest.raises(ValueError):
            search_events(session, EventFilters(severity="unknown"))
        with pytest.raises(ValueError):
            search_events(
                session,
                EventFilters(
                    start_time=datetime(2026, 9, 1, tzinfo=UTC),
                    end_time=datetime(2026, 8, 1, tzinfo=UTC),
                ),
            )
        event_row = session.get(SecurityEvent, "EV000001")
        assert event_row is not None
        invalid = {
            column.name: getattr(event_row, column.name)
            for column in SecurityEvent.__table__.columns
        }
        invalid["event_id"] = "EV999998"
        invalid["failed_attempts"] = -1
        with pytest.raises(IntegrityError):
            session.execute(insert(SecurityEvent), [invalid])
            session.flush()
        session.rollback()
