"""Strict agent contracts: model decisions are data, never executable instructions."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.api.schemas import Severity

UserId = Annotated[str, StringConstraints(max_length=4, pattern=r"^U\d{3}$")]
IncidentId = Annotated[str, StringConstraints(max_length=6, pattern=r"^INC\d{3}$")]
EventId = Annotated[str, StringConstraints(max_length=8, pattern=r"^EV\d{6}$")]


class ToolName(StrEnum):
    search_policy = "search_policy"
    search_security_events = "search_security_events"
    get_user_events = "get_user_events"
    get_incident = "get_incident"
    get_event = "get_event"


class ToolDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: ToolName
    user_id: UserId | None = None
    incident_id: IncidentId | None = None
    event_id: EventId | None = None
    event_type: (
        Literal[
            "endpoint_heartbeat",
            "failed_login",
            "firewall_allow",
            "firewall_block",
            "privilege_change",
            "successful_login",
            "suspicious_process",
        ]
        | None
    ) = None
    severity: Severity | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    limit: int = Field(default=5, ge=1, le=5)

    @field_validator("start_time", "end_time")
    @classmethod
    def timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.utcoffset() is None:
            raise ValueError("time filter needs timezone")
        return value

    @model_validator(mode="after")
    def consistent(self) -> "ToolDecision":
        if self.start_time and self.end_time and self.start_time > self.end_time:
            raise ValueError("start_time after end_time")
        if self.name == ToolName.get_user_events and self.user_id is None:
            raise ValueError("get_user_events requires user_id")
        if self.name == ToolName.get_incident and self.incident_id is None:
            raise ValueError("get_incident requires incident_id")
        if self.name == ToolName.get_event and self.event_id is None:
            raise ValueError("get_event requires event_id")
        if self.name in {
            ToolName.search_policy,
            ToolName.get_incident,
            ToolName.get_user_events,
            ToolName.get_event,
        } and any((self.event_type, self.severity, self.start_time, self.end_time)):
            raise ValueError("irrelevant filters")
        if self.name == ToolName.search_policy and (self.user_id or self.incident_id):
            raise ValueError("irrelevant identifier")
        if self.name == ToolName.get_incident and self.user_id:
            raise ValueError("irrelevant identifier")
        if self.name == ToolName.get_user_events and self.incident_id:
            raise ValueError("irrelevant identifier")
        if self.name != ToolName.get_event and self.event_id:
            raise ValueError("irrelevant event identifier")
        if self.name == ToolName.get_event and (self.user_id or self.incident_id):
            raise ValueError("irrelevant identifier")
        return self


class RoutePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    classification: Literal["policy", "events", "incident", "multi", "unknown"]
    tools: list[ToolName] = Field(max_length=3)

    @model_validator(mode="after")
    def unique_tools(self) -> "RoutePlan":
        if len(self.tools) != len(set(self.tools)):
            raise ValueError("duplicate tools")
        return self


class Synthesis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=400)
    interpretation: str = Field(min_length=1, max_length=1200)
    recommended_next_steps: list[str] = Field(max_length=3)


class EvidenceRecord(BaseModel):
    kind: Literal["policy", "event", "incident"]
    source_id: str
    source: str
    text: str
    related_ids: list[str] = Field(default_factory=list)
    citation: dict[str, str | int | None] | None = None


class AgentResponse(BaseModel):
    summary: str
    observed_evidence: list[EvidenceRecord]
    policy_context: list[EvidenceRecord]
    interpretation: str
    recommended_next_steps: list[str]
    evidence_sufficiency: bool
    sources: list[str]
    selected_tools: list[ToolName]
    tool_results: dict[str, str]
    errors: list[str]
    outcome: str
    graph_steps: int
    tool_calls: int
