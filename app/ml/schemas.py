"""Validated public anomaly result contracts."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AnomalyResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_type: Literal["user", "source_ip"]
    entity_id: str
    window_start: datetime
    window_end: datetime
    anomaly_score: float
    flagged_anomalous: bool
    feature_values: dict[str, float]
    contributing_observations: list[str] = Field(max_length=5)
    model_version: str
    statement: str = (
        "Behavioral anomaly score from a synthetic-data demonstration model; "
        "this is not an attack determination."
    )

    @field_validator("window_start", "window_end")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("window timestamps must be timezone-aware")
        return value
