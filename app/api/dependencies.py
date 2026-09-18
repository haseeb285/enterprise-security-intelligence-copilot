"""Replaceable demo principal and dependency injection for application resources."""

from collections.abc import Iterator
from dataclasses import dataclass
from hmac import compare_digest
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.services import ApiService

bearer = HTTPBearer(auto_error=False, description="Local demo bearer token; not enterprise SSO")


@dataclass(frozen=True)
class Principal:
    role: str


def get_principal(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Principal:
    settings = request.app.state.settings
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    admin = settings.demo_api_token.get_secret_value()
    reader = settings.demo_read_token.get_secret_value()
    if compare_digest(token, admin):
        return Principal("admin")
    if compare_digest(token, reader):
        return Principal("reader")
    raise HTTPException(
        status.HTTP_401_UNAUTHORIZED, "Invalid credentials", headers={"WWW-Authenticate": "Bearer"}
    )


def require_admin(principal: Annotated[Principal, Depends(get_principal)]) -> Principal:
    if principal.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin role required")
    return principal


def get_session(request: Request) -> Iterator[Session]:
    factory = request.app.state.session_factory
    if factory is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "PostgreSQL unavailable")
    try:
        with factory() as session:
            yield session
    except SQLAlchemyError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "PostgreSQL unavailable") from exc


def get_api_service(session: Annotated[Session, Depends(get_session)]) -> ApiService:
    return ApiService(session)
