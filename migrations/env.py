"""Alembic environment using the configured PostgreSQL URL."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import create_engine

from app.core.settings import get_settings
from app.db.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def database_url() -> str:
    secret = get_settings().database_url
    if secret is None:
        raise RuntimeError("DATABASE_URL is required to run Alembic migrations")
    value = secret.get_secret_value()
    if not value.startswith("postgresql+psycopg://"):
        raise ValueError("DATABASE_URL must use the postgresql+psycopg driver")
    return value


def run_migrations_offline() -> None:
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(database_url(), poolclass=pool.NullPool)
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
