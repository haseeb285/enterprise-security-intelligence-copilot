"""Bounded PostgreSQL readiness wait for container process startup."""

from __future__ import annotations

import time
from collections.abc import Callable

from sqlalchemy.exc import SQLAlchemyError

from app.core.settings import Settings, get_settings
from app.db.session import check_db_connection, create_db_engine


def wait_for_database(
    settings: Settings,
    *,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    """Return the successful attempt number or fail after a bounded wait."""

    for attempt in range(1, settings.database_startup_attempts + 1):
        engine = None
        try:
            engine = create_db_engine(settings)
            check_db_connection(engine)
            return attempt
        except (SQLAlchemyError, OSError):
            if attempt == settings.database_startup_attempts:
                break
            sleep(settings.database_startup_delay_seconds)
        finally:
            if engine is not None:
                engine.dispose()
    raise RuntimeError("PostgreSQL did not become ready before the startup deadline")


def main() -> None:
    attempt = wait_for_database(get_settings())
    print(f"PostgreSQL ready after attempt {attempt}")


if __name__ == "__main__":
    main()
