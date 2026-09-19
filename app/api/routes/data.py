"""Versioned read-only telemetry and incident routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import Principal, get_api_service, get_principal, require_admin
from app.api.schemas import (
    AuditOut,
    DeviceId,
    ErrorOut,
    EventId,
    EventOut,
    EventQuery,
    IncidentId,
    IncidentOut,
    MetricsOut,
    PageOut,
    Severity,
    UserId,
)
from app.api.services import ApiService
from app.core.observability import ErrorCategory, emit, metrics
from app.db.repository import EventFilters

router = APIRouter(tags=["Simulated SIEM"])
ERRORS = {
    401: {"model": ErrorOut},
    403: {"model": ErrorOut},
    404: {"model": ErrorOut},
    503: {"model": ErrorOut},
}


def _db_action(
    service: ApiService,
    principal: Principal,
    action: str,
    resource: str,
    resource_id: str | None,
    operation,
):
    try:
        result = operation()
        service.audit(
            action,
            resource,
            resource_id,
            "success" if result is not None else "not_found",
            principal.role,
        )
        return result
    except SQLAlchemyError as exc:
        service.session.rollback()
        metrics().increment("dependency_failures_total", label="postgresql")
        emit(
            "database",
            "operation_failure",
            dependency="postgresql",
            outcome="failure",
            error_category=ErrorCategory.database_unavailable,
        )
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "PostgreSQL unavailable") from exc


@router.get(
    "/events",
    response_model=PageOut[EventOut],
    responses=ERRORS,
    summary="Search synthetic security events",
    description="Bounded, filtered simulated SIEM read. Requires a reader or admin token.",
    dependencies=[Depends(get_principal)],
)
def events(
    service: Annotated[ApiService, Depends(get_api_service)],
    principal: Annotated[Principal, Depends(get_principal)],
    user_id: UserId | None = None,
    start_time: Annotated[str | None, Query(max_length=64)] = None,
    end_time: Annotated[str | None, Query(max_length=64)] = None,
    severity: Severity | None = None,
    event_type: Annotated[str | None, Query(min_length=1, max_length=32)] = None,
    source_ip: Annotated[str | None, Query(max_length=45)] = None,
    device_id: DeviceId | None = None,
    incident_id: IncidentId | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
):
    query = EventQuery.model_validate(
        dict(
            user_id=user_id,
            start_time=start_time,
            end_time=end_time,
            severity=severity,
            event_type=event_type,
            source_ip=source_ip,
            device_id=device_id,
            incident_id=incident_id,
            limit=limit,
            offset=offset,
        )
    )
    filters = EventFilters(
        user_id=query.user_id,
        start_time=query.start_time,
        end_time=query.end_time,
        severity=query.severity.value if query.severity else None,
        event_type=query.event_type,
        source_ip=query.source_ip,
        device_id=query.device_id,
        incident_id=query.incident_id,
    )
    return _db_action(
        service,
        principal,
        "api_search_events",
        "security_event",
        None,
        lambda: service.events(filters, query.limit, query.offset),
    )


@router.get(
    "/events/{event_id}",
    response_model=EventOut,
    responses=ERRORS,
    summary="Get one synthetic security event",
    dependencies=[Depends(get_principal)],
)
def event(
    event_id: Annotated[EventId, Path()],
    service: Annotated[ApiService, Depends(get_api_service)],
    principal: Annotated[Principal, Depends(get_principal)],
):
    result = _db_action(
        service,
        principal,
        "api_get_event",
        "security_event",
        event_id,
        lambda: service.event(event_id),
    )
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")
    return result


@router.get(
    "/users/{user_id}/events",
    response_model=PageOut[EventOut],
    responses=ERRORS,
    summary="List one synthetic user's events",
    dependencies=[Depends(get_principal)],
)
def user_events(
    user_id: Annotated[UserId, Path()],
    service: Annotated[ApiService, Depends(get_api_service)],
    principal: Annotated[Principal, Depends(get_principal)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
):
    return _db_action(
        service,
        principal,
        "api_user_events",
        "user",
        user_id,
        lambda: service.user_events(user_id, limit, offset),
    )


@router.get(
    "/incidents",
    response_model=PageOut[IncidentOut],
    responses=ERRORS,
    summary="List synthetic incidents",
    description="Admin token required.",
    dependencies=[Depends(require_admin)],
)
def incidents(
    service: Annotated[ApiService, Depends(get_api_service)],
    principal: Annotated[Principal, Depends(require_admin)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
):
    return _db_action(
        service,
        principal,
        "api_list_incidents",
        "incident",
        None,
        lambda: service.incidents(limit, offset),
    )


@router.get(
    "/incidents/{incident_id}",
    response_model=IncidentOut,
    responses=ERRORS,
    summary="Get one synthetic incident",
    description="Admin token required.",
    dependencies=[Depends(require_admin)],
)
def incident(
    incident_id: Annotated[IncidentId, Path()],
    service: Annotated[ApiService, Depends(get_api_service)],
    principal: Annotated[Principal, Depends(require_admin)],
):
    result = _db_action(
        service,
        principal,
        "api_get_incident",
        "incident",
        incident_id,
        lambda: service.incident(incident_id),
    )
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Incident not found")
    return result


@router.get(
    "/audit",
    response_model=PageOut[AuditOut],
    responses=ERRORS,
    summary="List safe audit metadata",
    description="Bounded admin-only audit view. Internal detail payloads are omitted.",
    dependencies=[Depends(require_admin)],
)
def audit_logs(
    service: Annotated[ApiService, Depends(get_api_service)],
    principal: Annotated[Principal, Depends(require_admin)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
):
    return _db_action(
        service,
        principal,
        "api_list_audit",
        "audit_log",
        None,
        lambda: service.audit_logs(limit, offset),
    )


@router.get(
    "/metrics",
    response_model=MetricsOut,
    responses=ERRORS,
    summary="Read bounded operational metrics",
    description="Admin-only process-local counters and latency summaries; no content or IDs.",
    dependencies=[Depends(require_admin)],
)
def operational_metrics(
    request: Request,
    service: Annotated[ApiService, Depends(get_api_service)],
    principal: Annotated[Principal, Depends(require_admin)],
):
    return _db_action(
        service,
        principal,
        "api_get_metrics",
        "operational_metrics",
        None,
        request.app.state.metrics.snapshot,
    )
