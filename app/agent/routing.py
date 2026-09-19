"""Constrain structured model routes to explicit requester intent and inputs."""

import re
from datetime import datetime

from app.agent.schemas import RoutePlan, ToolDecision, ToolName

USER_RE = re.compile(r"\bU\d{3}\b")
INCIDENT_RE = re.compile(r"\bINC\d{3}\b")
EVENT_ID_RE = re.compile(r"\bEV\d{6}\b")
TIME_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})\b")
POLICY_RE = re.compile(
    r"\b(policy|policies|require|requires|requirement|mfa|password|vpn|backup|retention)\b", re.I
)
EVENT_RE = re.compile(r"\b(event|events|login|logins|firewall|telemetry|alerts?|blocks?)\b", re.I)
ACTIVITY_RE = re.compile(r"\b(activity|behavior|behaviour)\b", re.I)


def required_tools(request: str) -> list[ToolName]:
    """Return only sources explicitly asked for; vague requests select nothing."""
    names = []
    if POLICY_RE.search(request):
        names.append(ToolName.search_policy)
    if INCIDENT_RE.search(request):
        names.append(ToolName.get_incident)
    if EVENT_ID_RE.search(request):
        names.append(ToolName.get_event)
    user_id = USER_RE.search(request)
    event_requested = EVENT_RE.search(request)
    if event_requested and not EVENT_ID_RE.search(request):
        names.append(ToolName.search_security_events)
    elif user_id and ACTIVITY_RE.search(request):
        names.append(ToolName.get_user_events)
    return names


def event_type_from_request(request: str) -> str | None:
    lowered = request.lower()
    if re.search(r"\bfailed\s+(?:login|authentication)", lowered):
        return "failed_login"
    if re.search(r"\bsuccessful\s+(?:login|authentication)", lowered):
        return "successful_login"
    if "firewall" in lowered and re.search(r"\bblock", lowered):
        return "firewall_block"
    if "firewall" in lowered and re.search(r"\ballow", lowered):
        return "firewall_allow"
    if "heartbeat" in lowered:
        return "endpoint_heartbeat"
    if "privilege" in lowered and "change" in lowered:
        return "privilege_change"
    if "suspicious" in lowered and "process" in lowered:
        return "suspicious_process"
    return None


def validated_decisions(plan: RoutePlan, request: str) -> list[ToolDecision]:
    """A model proposes tool names; explicit request cues constrain and complete the route."""
    required = required_tools(request)
    if not required:
        return []
    ordered = [name for name in plan.tools if name in required]
    ordered.extend(name for name in required if name not in ordered)
    if len(ordered) > 3:
        raise ValueError("Too many requested evidence sources")
    users = USER_RE.findall(request)
    incidents = INCIDENT_RE.findall(request)
    events = EVENT_ID_RE.findall(request)
    times = TIME_RE.findall(request)
    if len(set(users)) > 1 or len(set(incidents)) > 1 or len(set(events)) > 1 or len(times) > 2:
        raise ValueError("Ambiguous identifiers or time range")
    parsed_times = [datetime.fromisoformat(value.replace("Z", "+00:00")) for value in times]
    decisions = []
    for name in ordered:
        values = {"name": name, "limit": 5}
        if name == ToolName.get_user_events:
            values["user_id"] = users[0]
        elif name == ToolName.get_incident:
            values["incident_id"] = incidents[0]
        elif name == ToolName.get_event:
            values["event_id"] = events[0]
        elif name == ToolName.search_security_events:
            values["user_id"] = users[0] if users else None
            values["incident_id"] = incidents[0] if incidents else None
            values["event_type"] = event_type_from_request(request)
            values["start_time"] = parsed_times[0] if parsed_times else None
            values["end_time"] = parsed_times[1] if len(parsed_times) > 1 else None
        decisions.append(ToolDecision.model_validate(values))
    return decisions
