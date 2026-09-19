"""Public API contracts; no ORM objects or provider internals cross this boundary."""

from datetime import datetime
from enum import StrEnum
from ipaddress import ip_address
from typing import Annotated, Generic, TypeVar

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

EventId = Annotated[str, StringConstraints(max_length=8, pattern=r"^EV\d{6}$")]
UserId = Annotated[str, StringConstraints(max_length=4, pattern=r"^U\d{3}$")]
IncidentId = Annotated[str, StringConstraints(max_length=6, pattern=r"^INC\d{3}$")]
DeviceId = Annotated[str, StringConstraints(max_length=4, pattern=r"^D\d{3}$")]


class Severity(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class EventQuery(BaseModel):
    user_id: UserId | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    severity: Severity | None = None
    event_type: str | None = Field(default=None, min_length=1, max_length=32)
    source_ip: str | None = Field(default=None, max_length=45)
    device_id: DeviceId | None = None
    incident_id: IncidentId | None = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=1_000_000)

    @field_validator("start_time", "end_time")
    @classmethod
    def aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.utcoffset() is None:
            raise ValueError("Timestamp must include a timezone")
        return value

    @field_validator("source_ip")
    @classmethod
    def valid_ip(cls, value: str | None) -> str | None:
        if value is not None:
            ip_address(value)
        return value

    @model_validator(mode="after")
    def ordered_times(self) -> "EventQuery":
        if self.start_time and self.end_time and self.start_time > self.end_time:
            raise ValueError("start_time must not be after end_time")
        return self


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    timestamp: datetime
    user_id: str | None
    source_ip: str
    destination_ip: str | None
    device_id: str | None
    event_type: str
    severity: Severity
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


class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    incident_id: str
    title: str
    severity: Severity
    status: str
    created_at: datetime
    description: str


T = TypeVar("T")


class PageOut(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class ErrorOut(BaseModel):
    detail: str


class HealthOut(BaseModel):
    status: str
    dependencies: dict[str, str]


class AuditOut(BaseModel):
    """Safe audit projection; internal details and credentials never cross the API."""

    model_config = ConfigDict(from_attributes=True)

    audit_id: int
    timestamp: datetime
    action: str
    resource_type: str
    resource_id: str | None
    result: str


class RetrievalIn(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=5, ge=1, le=10)

    @field_validator("query")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Query cannot be blank")
        return value


class CitationOut(BaseModel):
    document: str
    source: str
    section: str
    page: int | None


class EvidenceOut(BaseModel):
    text: str
    score: float
    chunk_id: str
    citation: CitationOut


class RetrievalOut(BaseModel):
    evidence: list[EvidenceOut]
    insufficient_evidence: bool
