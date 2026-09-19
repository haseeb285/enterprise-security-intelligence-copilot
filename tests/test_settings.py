"""Foundation configuration contract tests."""

import pytest
from pydantic import ValidationError

from app.core.settings import Settings


def test_safe_local_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("DATABASE_URL", "DEMO_API_TOKEN", "DEMO_READ_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    settings = Settings(_env_file=None)

    assert settings.app_env == "development"
    assert settings.ollama_model == "qwen3.5:4b"
    assert settings.database_url is None
    assert settings.demo_api_token is None


def test_environment_override_and_secret_redaction(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_MODEL", "test-model")
    monkeypatch.setenv("DEMO_API_TOKEN", "synthetic-test-token")
    monkeypatch.setenv("DATABASE_URL", "synthetic-local-dsn")

    settings = Settings(_env_file=None)

    assert settings.ollama_model == "test-model"
    assert settings.demo_api_token is not None
    assert settings.demo_api_token.get_secret_value() == "synthetic-test-token"
    assert settings.database_url is not None
    assert settings.database_url.get_secret_value() == "synthetic-local-dsn"
    assert "synthetic-test-token" not in repr(settings)
    assert "synthetic-local-dsn" not in repr(settings)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("OLLAMA_BASE_URL", "ftp://invalid.example"),
        ("MAX_QUESTION_CHARS", "0"),
        ("REQUEST_TIMEOUT_SECONDS", "121"),
    ],
)
def test_invalid_configuration_is_rejected(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    monkeypatch.setenv(name, value)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
