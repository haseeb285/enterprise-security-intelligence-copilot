"""PostgreSQL engine creation from validated environment settings."""

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.settings import Settings, get_settings


def create_db_engine(settings: Settings | None = None) -> Engine:
    settings = settings or get_settings()
    if settings.database_url is None:
        raise RuntimeError("DATABASE_URL is required. Set it in the ignored .env file.")
    url = settings.database_url.get_secret_value()
    if not url.startswith("postgresql+psycopg://"):
        raise ValueError("DATABASE_URL must use the postgresql+psycopg driver")
    return create_engine(url, pool_pre_ping=True)


def check_db_connection(engine: Engine) -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)
