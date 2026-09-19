"""Portable configuration and bounded startup behavior used by Compose."""

from pathlib import Path

import pytest
from pydantic import SecretStr
from sqlalchemy.exc import OperationalError

from app.core.settings import Settings
from app.db import wait


class FakeEngine:
    def __init__(self):
        self.disposed = False

    def dispose(self):
        self.disposed = True


def compose_settings(**overrides) -> Settings:
    values = {
        "database_url": SecretStr("postgresql+psycopg://demo:secret@postgres:5432/demo"),
        "qdrant_url": "http://qdrant:6333",
        "ollama_base_url": "http://host.docker.internal:11434",
        "ml_model_path": Path("/app/models/anomaly/isolation_forest_daily_v1.joblib"),
        "database_startup_attempts": 3,
        "database_startup_delay_seconds": 0.1,
    }
    values.update(overrides)
    return Settings(**values)


def test_compose_service_urls_and_model_mount_are_configurable():
    settings = compose_settings()
    assert str(settings.qdrant_url) == "http://qdrant:6333/"
    assert str(settings.ollama_base_url) == "http://host.docker.internal:11434/"
    assert settings.ml_model_path == Path("/app/models/anomaly/isolation_forest_daily_v1.joblib")


def test_database_startup_wait_retries_then_succeeds(monkeypatch):
    engines = []
    checks = 0
    sleeps = []

    def engine_factory(_settings):
        engine = FakeEngine()
        engines.append(engine)
        return engine

    def check(_engine):
        nonlocal checks
        checks += 1
        if checks < 3:
            raise OperationalError("SELECT 1", {}, RuntimeError("not ready"))

    monkeypatch.setattr(wait, "create_db_engine", engine_factory)
    monkeypatch.setattr(wait, "check_db_connection", check)
    attempt = wait.wait_for_database(compose_settings(), sleep=sleeps.append)
    assert attempt == 3
    assert sleeps == [0.1, 0.1]
    assert all(engine.disposed for engine in engines)


def test_database_startup_wait_is_bounded(monkeypatch):
    monkeypatch.setattr(wait, "create_db_engine", lambda _settings: FakeEngine())

    def unavailable(_engine):
        raise OperationalError("SELECT 1", {}, RuntimeError("not ready"))

    monkeypatch.setattr(wait, "check_db_connection", unavailable)
    with pytest.raises(RuntimeError, match="startup deadline"):
        wait.wait_for_database(compose_settings(database_startup_attempts=2), sleep=lambda _: None)
