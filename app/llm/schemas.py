"""Example strict output contract; citations are never model-authored."""

from pydantic import BaseModel, ConfigDict, Field


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    summary: str = Field(min_length=1)
    evidence: list[str]
    interpretation: str = Field(min_length=1)
    recommended_next_steps: list[str]
    sufficient_evidence: bool = Field(
        description=(
            "True when supplied facts support the narrow requested factual summary; "
            "false when facts are absent or unreadable. True does not prove cause or compromise."
        )
    )
