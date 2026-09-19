"""Typed, reusable HTTP client for the local FastAPI boundary."""

from datetime import datetime
from typing import Any, Generic, Literal, TypeVar
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

T = TypeVar("T")


class ApiClientError(RuntimeError):
    def __init__(self, kind: str, message: str, status_code: int | None = None):
        self.kind = kind
        self.status_code = status_code
        super().__init__(message)


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str
    dependencies: dict[str, str]


class MetricsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    uptime_seconds: float
    counters: dict[str, int]
    labeled_counters: dict[str, dict[str, int]]
    latency_ms: dict[str, dict[str, float | int]]
    labeled_latency_ms: dict[str, dict[str, dict[str, float | int]]]


class PageResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(extra="forbid")
    items: list[T]
    total: int
    limit: int
    offset: int


class EventRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str
    timestamp: datetime
    user_id: str | None
    source_ip: str
    destination_ip: str | None
    device_id: str | None
    event_type: str
    severity: str
    action: str
    status: str
    country: str | None
    authentication_method: str | None
    failed_attempts: int | None
    successful_attempts: int | None
    privileged_account: bool | None
    source: str
    description: str
    incident_id: str | None


class IncidentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    incident_id: str
    title: str
    severity: str
    status: str
    created_at: datetime
    description: str


class AuditRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    audit_id: int
    timestamp: datetime
    action: str
    resource_type: str
    resource_id: str | None
    result: str


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document: str
    source: str
    section: str
    page: int | None


class RetrievalEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str
    score: float
    chunk_id: str
    citation: Citation


class RetrievalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence: list[RetrievalEvidence]
    insufficient_evidence: bool


class EvidenceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["policy", "event", "incident"]
    source_id: str
    source: str
    text: str
    related_ids: list[str] = Field(default_factory=list)
    citation: dict[str, str | int | None] | None = None
    attributes: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class MLEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str
    entity_type: Literal["user", "source_ip"]
    entity_id: str
    window_start: datetime
    window_end: datetime
    anomaly_score: float
    flagged_anomalous: bool
    feature_values: dict[str, float]
    contributing_observations: list[str]
    model_version: str
    statement: str
    provenance: dict[str, str]


class InvestigationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str
    observed_evidence: list[EvidenceRecord]
    ml_analysis: list[MLEvidence]
    policy_context: list[EvidenceRecord]
    interpretation: str
    recommended_next_steps: list[str]
    evidence_sufficiency: bool
    sources: list[str]
    selected_tools: list[str]
    tool_results: dict[str, str]
    errors: list[str]
    outcome: str
    graph_steps: int
    tool_calls: int


def _base_url(value: str) -> str:
    parsed = urlparse(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("API base URL must be an explicit HTTP(S) URL")
    return value.rstrip("/")


class ApiClient:
    def __init__(
        self,
        base_url: str,
        token: str = "",
        *,
        timeout_seconds: float = 15,
        investigation_timeout_seconds: float = 210,
        transport: httpx.BaseTransport | None = None,
    ):
        self.base_url = _base_url(base_url)
        self.token = token.strip()
        self.timeout_seconds = timeout_seconds
        self.investigation_timeout_seconds = investigation_timeout_seconds
        self.transport = transport

    def _request(
        self,
        method: str,
        path: str,
        *,
        protected: bool = True,
        timeout: float | None = None,
        accepted_statuses: set[int] | None = None,
        **kwargs: Any,
    ) -> Any:
        if protected and not self.token:
            raise ApiClientError("authentication_required", "Enter a local demo bearer token.", 401)
        headers = {"Authorization": f"Bearer {self.token}"} if protected else {}
        try:
            with httpx.Client(
                base_url=self.base_url,
                headers=headers,
                timeout=timeout or self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = client.request(method, path, **kwargs)
        except httpx.TimeoutException as exc:
            raise ApiClientError(
                "timeout", "The API request timed out. The backend may still be working."
            ) from exc
        except httpx.TransportError as exc:
            raise ApiClientError(
                "unavailable", "FastAPI is unavailable. Start it and retry."
            ) from exc
        if response.is_success or response.status_code in (accepted_statuses or set()):
            try:
                return response.json()
            except ValueError as exc:
                raise ApiClientError("invalid_response", "FastAPI returned invalid JSON.") from exc
        messages = {
            401: ("unauthorized", "The demo token is missing or invalid."),
            403: ("forbidden", "This view requires the admin demo token."),
            404: ("not_found", "The requested synthetic record was not found."),
            422: ("invalid_input", "FastAPI rejected the submitted input."),
            503: ("dependency_unavailable", "A required local dependency is unavailable."),
        }
        kind, message = messages.get(
            response.status_code, ("api_error", "FastAPI could not complete the request.")
        )
        raise ApiClientError(kind, message, response.status_code)

    def health(self) -> HealthResponse:
        data = self._request("GET", "/health", protected=False, accepted_statuses={503})
        return HealthResponse.model_validate(data)

    def metrics(self) -> MetricsResponse:
        return MetricsResponse.model_validate(self._request("GET", "/metrics"))

    def events(
        self, filters: dict[str, Any] | None = None, *, limit: int = 25, offset: int = 0
    ) -> PageResponse[EventRecord]:
        params = {key: value for key, value in (filters or {}).items() if value not in (None, "")}
        params.update(limit=limit, offset=offset)
        data = self._request("GET", "/events", params=params)
        return TypeAdapter(PageResponse[EventRecord]).validate_python(data)

    def event(self, event_id: str) -> EventRecord:
        return EventRecord.model_validate(self._request("GET", f"/events/{event_id}"))

    def incidents(self, *, limit: int = 10, offset: int = 0) -> PageResponse[IncidentRecord]:
        data = self._request("GET", "/incidents", params={"limit": limit, "offset": offset})
        return TypeAdapter(PageResponse[IncidentRecord]).validate_python(data)

    def audit(self, *, limit: int = 50, offset: int = 0) -> PageResponse[AuditRecord]:
        data = self._request("GET", "/audit", params={"limit": limit, "offset": offset})
        return TypeAdapter(PageResponse[AuditRecord]).validate_python(data)

    def retrieve(self, query: str, *, top_k: int = 5) -> RetrievalResponse:
        data = self._request("POST", "/retrieval", json={"query": query, "top_k": top_k})
        return RetrievalResponse.model_validate(data)

    def investigate(self, request: str) -> InvestigationResponse:
        data = self._request(
            "POST",
            "/investigate",
            json={"request": request},
            timeout=self.investigation_timeout_seconds,
        )
        return InvestigationResponse.model_validate(data)
