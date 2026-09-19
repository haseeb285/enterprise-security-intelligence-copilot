"""Read-only live PostgreSQL verification when a local database is configured."""

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.settings import Settings
from app.db.models import Device, Incident, SecurityEvent, User
from app.db.repository import EventFilters, get_user_events, search_events
from app.db.session import create_db_engine


@pytest.mark.postgres_integration
def test_migrated_postgres_dataset_and_queries() -> None:
    settings = Settings()
    if settings.database_url is None:
        pytest.skip("DATABASE_URL not configured; live PostgreSQL test requires Compose")
    engine = create_db_engine(settings)
    try:
        with Session(engine) as session:
            assert session.scalar(text("SELECT version_num FROM alembic_version")) == "20260918_01"
            assert [
                session.scalar(select(func.count()).select_from(model))
                for model in (User, Device, SecurityEvent, Incident)
            ] == [120, 140, 12065, 6]
            assert search_events(session, EventFilters(source_ip="203.0.113.201")).total == 25
            assert all(event.user_id == "U104" for event in get_user_events(session, "U104").items)
            assert session.scalar(select(SecurityEvent.timestamp).limit(1)).tzinfo is not None
    finally:
        engine.dispose()
