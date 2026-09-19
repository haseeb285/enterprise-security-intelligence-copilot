"""Reusable anomaly inference service, independent of API and LangGraph."""

import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import SecurityEvent, User
from app.ml.features import build_observation
from app.ml.model import (
    IncompatibleModelArtifact,
    ModelArtifact,
    ModelArtifactError,
    load_artifact,
    score_observations,
)
from app.ml.schemas import AnomalyResult


class UnknownUserError(LookupError):
    pass


class InsufficientHistoryError(RuntimeError):
    pass


class InvalidAnalysisWindow(ValueError):
    pass


class AnomalyDetectionService:
    def __init__(self, session: Session, artifact_path: Path, *, minimum_events: int = 2):
        self.session = session
        self.artifact_path = artifact_path
        self.minimum_events = minimum_events
        self._artifact: ModelArtifact | None = None

    def default_user_window(self, user_id: str) -> tuple[datetime, datetime]:
        """Use the user's latest active UTC day; never reach beyond available data."""
        if not re.fullmatch(r"U\d{3}", user_id):
            raise ValueError("user_id must match U###")
        if self.session.scalar(select(User.user_id).where(User.user_id == user_id)) is None:
            raise UnknownUserError(user_id)
        latest = self.session.scalar(
            select(func.max(SecurityEvent.timestamp)).where(SecurityEvent.user_id == user_id)
        )
        if latest is None:
            raise InsufficientHistoryError("No events are available for this user")
        latest = latest.replace(tzinfo=UTC) if latest.tzinfo is None else latest.astimezone(UTC)
        start = latest.replace(hour=0, minute=0, second=0, microsecond=0)
        return start, start + timedelta(days=1)

    def _model(self) -> ModelArtifact:
        if self._artifact is None:
            self._artifact = load_artifact(self.artifact_path)
        return self._artifact

    @staticmethod
    def _window(start: datetime, end: datetime) -> tuple[datetime, datetime]:
        if start.utcoffset() is None or end.utcoffset() is None:
            raise InvalidAnalysisWindow("Analysis timestamps must be timezone-aware")
        normalized_start = start.astimezone(UTC)
        normalized_end = end.astimezone(UTC)
        if normalized_start >= normalized_end:
            raise InvalidAnalysisWindow("Analysis start must precede end")
        if normalized_end - normalized_start > timedelta(hours=24):
            raise InvalidAnalysisWindow("Analysis window cannot exceed 24 hours")
        return normalized_start, normalized_end

    def analyze_user(self, user_id: str, start: datetime, end: datetime) -> AnomalyResult:
        if not re.fullmatch(r"U\d{3}", user_id):
            raise ValueError("user_id must match U###")
        window_start, window_end = self._window(start, end)
        if self.session.scalar(select(User.user_id).where(User.user_id == user_id)) is None:
            raise UnknownUserError(user_id)
        events = list(
            self.session.scalars(
                select(SecurityEvent)
                .where(
                    SecurityEvent.user_id == user_id,
                    SecurityEvent.timestamp >= window_start,
                    SecurityEvent.timestamp < window_end,
                )
                .order_by(SecurityEvent.timestamp, SecurityEvent.event_id)
            )
        )
        if len(events) < self.minimum_events:
            raise InsufficientHistoryError(
                f"At least {self.minimum_events} events are required in the analysis window"
            )
        observation = build_observation(
            events,
            entity_type="user",
            entity_id=user_id,
            window_start=window_start,
            window_end=window_end,
        )
        artifact = self._model()
        scored = score_observations(artifact, [observation])[0]
        return AnomalyResult(
            entity_type="user",
            entity_id=user_id,
            window_start=window_start,
            window_end=window_end,
            anomaly_score=scored.anomaly_score,
            flagged_anomalous=scored.flagged_anomalous,
            feature_values=observation.features,
            contributing_observations=_signals(observation.features, artifact.metadata),
            model_version=artifact.metadata["model_version"],
        )


def _signals(features: dict[str, float], metadata: dict) -> list[str]:
    reference = metadata.get("feature_reference", {})
    labels = {
        "failed_login_count": "failed-login frequency is elevated",
        "unique_source_ip_count": "source-IP diversity is elevated",
        "unique_country_count": "country diversity is elevated",
        "unusual_hour_fraction": "unusual-hour activity is elevated",
        "privileged_event_count": "privileged-account activity is elevated",
        "firewall_block_count": "firewall-block frequency is elevated",
        "endpoint_alert_count": "endpoint-alert frequency is elevated",
        "privilege_change_count": "privilege-change activity is elevated",
        "non_auth_event_count": "non-authentication activity volume is elevated",
        "country_transition_count": "authentication country changes are elevated",
        "max_events_15m": "short-window event frequency is elevated",
    }
    signals = []
    for name, label in labels.items():
        threshold = reference.get(name, {}).get("p90")
        if threshold is not None and features[name] > threshold:
            signals.append(label)
    return signals[:5] or ["no individual feature exceeded its training 90th percentile"]


__all__ = [
    "AnomalyDetectionService",
    "IncompatibleModelArtifact",
    "InsufficientHistoryError",
    "InvalidAnalysisWindow",
    "ModelArtifactError",
    "UnknownUserError",
]
