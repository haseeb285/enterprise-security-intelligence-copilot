"""Constrain structured model routes to explicit requester intent and inputs."""

import re
from datetime import UTC, datetime, timedelta

from app.agent.schemas import RoutePlan, ToolDecision, ToolName

USER_RE = re.compile(r"\bU\d{3}\b")
INCIDENT_RE = re.compile(r"\bINC\d{3}\b")
EVENT_ID_RE = re.compile(r"\bEV\d{6}\b")
TIME_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})\b")
DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b(?!T)")
POLICY_RE = re.compile(
    r"\b(policy|policies|require|requires|requirement|mfa|password|vpn|backup|retention|controls?)\b",
    re.I,
)
EVENT_RE = re.compile(r"\b(event|events|login|logins|firewall|telemetry|alerts?|blocks?)\b", re.I)
ACTIVITY_RE = re.compile(r"\b(activity|behavior|behaviour)\b", re.I)
ML_RE = re.compile(
    r"\b(anomal(?:y|ies|ous)|unusual(?:ly)?|behaviorally unusual|behaviourally unusual|"
    r"suspicious activity|anomaly score|ml analysis|machine learning)\b",
    re.I,
)
ML_ONLY_RE = re.compile(r"\b(anomaly score|run (?:the )?anomaly|ml analysis)\b", re.I)


def required_tools(request: str) -> list[ToolName]:
    """Return only sources justified by explicit request cues."""
    names: list[ToolName] = []
    wants_ml = bool(ML_RE.search(request) and USER_RE.search(request))
    if POLICY_RE.search(request):
        names.append(ToolName.search_policy)
    if INCIDENT_RE.search(request):
        names.append(ToolName.get_incident)
    if EVENT_ID_RE.search(request):
        names.append(ToolName.get_event)
    user_id = USER_RE.search(request)
    if EVENT_RE.search(request) and not EVENT_ID_RE.search(request):
        names.append(ToolName.search_security_events)
    elif user_id and wants_ml and not ML_ONLY_RE.search(request):
        names.append(ToolName.search_security_events)
    elif user_id and ACTIVITY_RE.search(request) and not wants_ml:
        names.append(ToolName.get_user_events)
    if wants_ml:
        names.append(ToolName.analyze_user_anomaly)
    return list(dict.fromkeys(names))


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


def requested_window(request: str) -> tuple[datetime | None, datetime | None]:
    """Map explicit request time to a bounded [start, end) observation window."""
    times = TIME_RE.findall(request)
    dates = DATE_RE.findall(request)
    if len(times) > 2 or (times and dates) or len(dates) > 1:
        raise ValueError("Ambiguous time range")
    parsed = [datetime.fromisoformat(value.replace("Z", "+00:00")) for value in times]
    if len(parsed) == 2:
        return parsed[0], parsed[1]
    if len(parsed) == 1:
        return parsed[0] - timedelta(hours=24), parsed[0]
    if dates:
        start = datetime.fromisoformat(dates[0]).replace(tzinfo=UTC)
        return start, start + timedelta(days=1)
    return None, None


def validated_decisions(plan: RoutePlan, request: str) -> list[ToolDecision]:
    """A model proposes tool names; request cues constrain names and all arguments."""
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
    if len(set(users)) > 1 or len(set(incidents)) > 1 or len(set(events)) > 1:
        raise ValueError("Ambiguous identifiers")
    start, end = requested_window(request)
    if start is not None and end is not None and start >= end:
        raise ValueError("Invalid time range")
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
            values.update(
                user_id=users[0] if users else None,
                incident_id=incidents[0] if incidents else None,
                event_type=event_type_from_request(request),
                start_time=start,
                end_time=end,
            )
        elif name == ToolName.analyze_user_anomaly:
            values.update(user_id=users[0], start_time=start, end_time=end)
        decisions.append(ToolDecision.model_validate(values))
    return decisions
