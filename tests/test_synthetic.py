"""Behavioral checks for fictional baseline activity and injected scenarios."""

from collections import Counter
from datetime import UTC, timedelta
from ipaddress import ip_address, ip_network

from app.db.synthetic import SYNTHETIC_NOTICE, generate_dataset


def test_generation_is_deterministic_and_lightweight() -> None:
    first = generate_dataset(seed=42)
    second = generate_dataset(seed=42)
    changed = generate_dataset(seed=43)

    assert len(first.users) == 120
    assert len(first.devices) == 140
    assert 10_000 <= len(first.events) <= 30_000
    assert first.events == second.events
    assert first.scenarios == second.scenarios
    assert first.events[:100] != changed.events[:100]
    assert SYNTHETIC_NOTICE.startswith("SYNTHETIC DEMONSTRATION DATA")


def test_normal_activity_is_structured_and_consistent() -> None:
    data = generate_dataset(normal_event_count=2_000)
    ordinary = data.events[:2_000]
    users = {user["user_id"]: user for user in data.users}
    devices = {device["device_id"]: device for device in data.devices}
    types = Counter(event["event_type"] for event in ordinary)

    assert types["successful_login"] > 1_500
    assert types["failed_login"] < types["successful_login"]
    assert all(event["severity"] == "low" and event["incident_id"] is None for event in ordinary)
    assert all(event["timestamp"].tzinfo is UTC for event in data.events)
    assert sum(9 <= event["timestamp"].hour < 18 for event in ordinary) / len(ordinary) > 0.9
    assert sum(user["privileged"] for user in data.users) < len(data.users) / 10
    for event in ordinary:
        user = users[event["user_id"]]
        assert event["country"] == user["home_country"]
        assert devices[event["device_id"]]["owner_user_id"] == event["user_id"]
        assert ip_address(event["source_ip"]) in ip_network("198.51.100.0/24")


def test_injected_scenarios_have_intended_patterns_without_label_leakage() -> None:
    data = generate_dataset(normal_event_count=100)
    by_id = {event["event_id"]: event for event in data.events}
    scenarios = {scenario.scenario_type: scenario for scenario in data.scenarios}
    assert len(scenarios) == len(data.incidents) == 6

    brute = [by_id[event_id] for event_id in scenarios["brute_force"].related_event_ids]
    assert len(brute) == 25
    assert all(event["event_type"] == "failed_login" for event in brute)
    assert len({event["source_ip"] for event in brute}) == 1
    assert max(event["timestamp"] for event in brute) - min(
        event["timestamp"] for event in brute
    ) < timedelta(minutes=10)

    travel = [by_id[event_id] for event_id in scenarios["impossible_travel"].related_event_ids]
    assert [event["country"] for event in travel] == ["DE", "JP"]
    assert all(event["status"] == "success" for event in travel)
    assert (travel[1]["timestamp"] - travel[0]["timestamp"]).total_seconds() == 900

    compromise = [
        by_id[event_id] for event_id in scenarios["account_compromise_pattern"].related_event_ids
    ]
    assert [event["status"] for event in compromise] == ["failure"] * 12 + ["success"]
    assert all(event["country"] == "GB" for event in compromise)
    assert all(
        "scenario" not in key and "anomaly" not in key for event in data.events for key in event
    )
    assert all(event["incident_id"] is not None for event in data.events[100:])
