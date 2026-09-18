"""Deterministic, entirely fictional security telemetry for development only."""

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from random import Random
from typing import Any

SYNTHETIC_NOTICE = "SYNTHETIC DEMONSTRATION DATA — NOT REAL SECURITY TELEMETRY"
ORGANIZATION = "Clockwork Badger Cooperative (fictional)"
WINDOW_START = datetime(2026, 8, 1, tzinfo=UTC)
WINDOW_DAYS = 30


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    scenario_type: str
    affected_user: str | None
    start_time: datetime
    end_time: datetime
    related_event_ids: tuple[str, ...]
    expected_investigation_reason: str

    def as_json(self) -> dict[str, Any]:
        value = asdict(self)
        value["start_time"] = self.start_time.isoformat()
        value["end_time"] = self.end_time.isoformat()
        value["related_event_ids"] = list(self.related_event_ids)
        return value


@dataclass
class SyntheticDataset:
    seed: int
    users: list[dict[str, Any]]
    devices: list[dict[str, Any]]
    incidents: list[dict[str, Any]]
    events: list[dict[str, Any]]
    scenarios: list[Scenario]


def generate_dataset(seed: int = 42, normal_event_count: int = 12_000) -> SyntheticDataset:
    """Generate normal activity and six fixed scenario shapes with seed-specific details."""

    if normal_event_count < 0 or normal_event_count > 30_000:
        raise ValueError("normal_event_count must be between 0 and 30000")
    rng = Random(seed)
    users: list[dict[str, Any]] = []
    devices: list[dict[str, Any]] = []
    incidents: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    scenarios: list[Scenario] = []
    departments = ("Operations", "Research", "Customer Care", "Finance", "Engineering")
    countries = ("US", "GB", "DE", "JP")
    for number in range(1, 121):
        user_id = f"U{number:03d}"
        users.append(
            {
                "user_id": user_id,
                "display_name": f"Demo Person {number:03d}",
                "department": departments[(number - 1) % len(departments)],
                "home_country": countries[(number - 1) // 30],
                "privileged": number <= 8,
                "created_at": WINDOW_START - timedelta(days=30),
            }
        )
        devices.append(
            {
                "device_id": f"D{number:03d}",
                "owner_user_id": user_id,
                "name": f"demo-workstation-{number:03d}",
                "kind": "laptop",
                "managed": True,
            }
        )
        if number <= 20:
            devices.append(
                {
                    "device_id": f"D{number + 120:03d}",
                    "owner_user_id": user_id,
                    "name": f"demo-tablet-{number:03d}",
                    "kind": "tablet",
                    "managed": True,
                }
            )

    def add_event(
        *,
        timestamp: datetime,
        user_id: str | None,
        source_ip: str,
        destination_ip: str | None = "192.0.2.10",
        device_id: str | None = None,
        event_type: str,
        severity: str,
        action: str,
        status: str,
        country: str | None = None,
        authentication_method: str | None = None,
        failed_attempts: int | None = None,
        successful_attempts: int | None = None,
        privileged_account: bool | None = None,
        source: str,
        description: str,
        incident_id: str | None = None,
    ) -> str:
        event_id = f"EV{len(events) + 1:06d}"
        events.append(
            {
                "event_id": event_id,
                "timestamp": timestamp,
                "user_id": user_id,
                "source_ip": source_ip,
                "destination_ip": destination_ip,
                "device_id": device_id,
                "event_type": event_type,
                "severity": severity,
                "action": action,
                "status": status,
                "country": country,
                "authentication_method": authentication_method,
                "failed_attempts": failed_attempts,
                "successful_attempts": successful_attempts,
                "privileged_account": privileged_account,
                "source": source,
                "description": description,
                "incident_id": incident_id,
            }
        )
        return event_id

    # Individual users keep a home country, familiar workstation, and mostly stable source IP.
    for _ in range(normal_event_count):
        number = rng.randrange(1, 121)
        user = users[number - 1]
        day = rng.randrange(WINDOW_DAYS)
        stamp = WINDOW_START + timedelta(days=day)
        if stamp.weekday() >= 5:
            stamp += timedelta(days=7 - stamp.weekday())
            if stamp >= WINDOW_START + timedelta(days=WINDOW_DAYS):
                stamp -= timedelta(days=7)
        hour = rng.randrange(9, 18) if rng.random() < 0.96 else rng.randrange(0, 24)
        stamp = stamp.replace(hour=hour, minute=rng.randrange(60), second=rng.randrange(60))
        source_ip = f"198.51.100.{(number * 3 + rng.randrange(3)) % 200 + 1}"
        device_id = (
            f"D{number + 120:03d}" if number <= 20 and rng.random() < 0.1 else f"D{number:03d}"
        )
        roll = rng.random()
        base = {
            "timestamp": stamp,
            "user_id": user["user_id"],
            "source_ip": source_ip,
            "device_id": device_id,
            "country": user["home_country"],
            "privileged_account": user["privileged"],
        }
        if roll < 0.82:
            add_event(
                **base,
                event_type="successful_login",
                severity="low",
                action="allow",
                status="success",
                authentication_method="password_mfa",
                failed_attempts=0,
                successful_attempts=1,
                source="identity_gateway",
                description="Authentication completed from a managed device.",
            )
        elif roll < 0.90:
            add_event(
                **base,
                event_type="failed_login",
                severity="low",
                action="deny",
                status="failure",
                authentication_method="password_mfa",
                failed_attempts=1,
                successful_attempts=0,
                source="identity_gateway",
                description="Authentication rejected; no access granted.",
            )
        elif roll < 0.95:
            add_event(
                **base,
                event_type="endpoint_heartbeat",
                severity="low",
                action="observe",
                status="healthy",
                source="endpoint_agent",
                description="Managed endpoint health signal received.",
            )
        else:
            add_event(
                **base,
                event_type="firewall_allow",
                severity="low",
                action="allow",
                status="allowed",
                source="network_gateway",
                description="Routine outbound traffic allowed.",
            )

    scenario_base = WINDOW_START + timedelta(days=30)

    def add_scenario(
        scenario_type: str,
        affected_user: str | None,
        title: str,
        severity: str,
        reason: str,
        event_specs: list[dict[str, Any]],
    ) -> None:
        incident_id = f"INC{len(incidents) + 1:03d}"
        event_ids = [add_event(**spec, incident_id=incident_id) for spec in event_specs]
        times = [spec["timestamp"] for spec in event_specs]
        incidents.append(
            {
                "incident_id": incident_id,
                "title": title,
                "severity": severity,
                "status": "open",
                "created_at": max(times) + timedelta(minutes=2),
                "description": "Fictional grouped event sequence for investigation practice.",
            }
        )
        scenarios.append(
            Scenario(
                scenario_id=f"SCN{len(scenarios) + 1:03d}",
                scenario_type=scenario_type,
                affected_user=affected_user,
                start_time=min(times),
                end_time=max(times),
                related_event_ids=tuple(event_ids),
                expected_investigation_reason=reason,
            )
        )

    brute_time = scenario_base.replace(hour=1, minute=0)
    add_scenario(
        "brute_force",
        "U104",
        "Repeated denied authentication",
        "high",
        "Twenty-five denials from one unfamiliar source within ten minutes.",
        [
            {
                "timestamp": brute_time + timedelta(seconds=20 * i),
                "user_id": "U104",
                "source_ip": "203.0.113.201",
                "device_id": None,
                "event_type": "failed_login",
                "severity": "high",
                "action": "deny",
                "status": "failure",
                "country": "JP",
                "authentication_method": "password",
                "failed_attempts": 1,
                "successful_attempts": 0,
                "privileged_account": False,
                "source": "identity_gateway",
                "description": "Authentication rejected; no access granted.",
            }
            for i in range(25)
        ],
    )

    travel_time = scenario_base.replace(hour=10, minute=0)
    add_scenario(
        "impossible_travel",
        "U105",
        "Distant authentication pair",
        "high",
        "Successful sign-ins from DE and JP only fifteen minutes apart.",
        [
            {
                "timestamp": travel_time + timedelta(minutes=15 * i),
                "user_id": "U105",
                "source_ip": "198.51.100.75" if i == 0 else "203.0.113.151",
                "device_id": "D105" if i == 0 else None,
                "event_type": "successful_login",
                "severity": "medium" if i == 0 else "high",
                "action": "allow",
                "status": "success",
                "country": "DE" if i == 0 else "JP",
                "authentication_method": "password_mfa" if i == 0 else "password",
                "failed_attempts": 0,
                "successful_attempts": 1,
                "privileged_account": False,
                "source": "identity_gateway",
                "description": "Authentication completed.",
            }
            for i in range(2)
        ],
    )

    privilege_time = scenario_base.replace(hour=2, minute=5)
    add_scenario(
        "privileged_account",
        "U003",
        "Privileged activity outside usual hours",
        "critical",
        "Privileged account activity at 02:05 from an unfamiliar source and device.",
        [
            {
                "timestamp": privilege_time + timedelta(minutes=i),
                "user_id": "U003",
                "source_ip": "203.0.113.203",
                "device_id": None,
                "event_type": "successful_login" if i == 0 else "privilege_change",
                "severity": "high" if i == 0 else "critical",
                "action": "allow" if i == 0 else "modify",
                "status": "success",
                "country": "JP",
                "authentication_method": "password" if i == 0 else None,
                "failed_attempts": 0 if i == 0 else None,
                "successful_attempts": 1 if i == 0 else None,
                "privileged_account": True,
                "source": "identity_gateway" if i == 0 else "access_control",
                "description": "Privileged account activity recorded.",
            }
            for i in range(3)
        ],
    )

    compromise_time = scenario_base.replace(hour=3, minute=0)
    add_scenario(
        "account_compromise_pattern",
        "U106",
        "Denied attempts followed by access",
        "high",
        "Twelve denied attempts followed by a success from a new source and geography.",
        [
            {
                "timestamp": compromise_time + timedelta(seconds=30 * i),
                "user_id": "U106",
                "source_ip": "203.0.113.206",
                "device_id": None,
                "event_type": "successful_login" if i == 12 else "failed_login",
                "severity": "critical" if i == 12 else "high",
                "action": "allow" if i == 12 else "deny",
                "status": "success" if i == 12 else "failure",
                "country": "GB",
                "authentication_method": "password",
                "failed_attempts": 0 if i == 12 else 1,
                "successful_attempts": 1 if i == 12 else 0,
                "privileged_account": False,
                "source": "identity_gateway",
                "description": "Authentication completed."
                if i == 12
                else "Authentication rejected.",
            }
            for i in range(13)
        ],
    )

    endpoint_time = scenario_base.replace(hour=11, minute=0)
    add_scenario(
        "suspicious_endpoint",
        "U107",
        "Unusual endpoint process sequence",
        "high",
        "Four elevated endpoint process signals on one managed device.",
        [
            {
                "timestamp": endpoint_time + timedelta(minutes=i),
                "user_id": "U107",
                "source_ip": "198.51.100.122",
                "device_id": "D107",
                "event_type": "suspicious_process",
                "severity": "high",
                "action": "observe",
                "status": "alert",
                "country": "JP",
                "privileged_account": False,
                "source": "endpoint_agent",
                "description": "Unusual process activity observed by endpoint sensor.",
            }
            for i in range(4)
        ],
    )

    firewall_time = scenario_base.replace(hour=12, minute=0)
    add_scenario(
        "firewall_burst",
        None,
        "Repeated network blocks",
        "medium",
        "Eighteen denied connections from one unfamiliar source within minutes.",
        [
            {
                "timestamp": firewall_time + timedelta(seconds=15 * i),
                "user_id": None,
                "source_ip": "203.0.113.208",
                "destination_ip": "192.0.2.88",
                "device_id": None,
                "event_type": "firewall_block",
                "severity": "medium",
                "action": "deny",
                "status": "blocked",
                "source": "network_gateway",
                "description": "Inbound connection blocked by network rule.",
            }
            for i in range(18)
        ],
    )
    return SyntheticDataset(seed, users, devices, incidents, events, scenarios)
