"""Small provider contract shared by local inference and later application layers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic import BaseModel

StructuredT = TypeVar("StructuredT", bound=BaseModel)


@dataclass(frozen=True)
class HealthStatus:
    reachable: bool
    model_available: bool
    version: str | None
    detail: str


@dataclass(frozen=True)
class Generation:
    text: str
    model: str
    duration_seconds: float
    load_seconds: float | None = None
    output_tokens: int | None = None


@dataclass(frozen=True)
class StructuredGeneration:
    value: BaseModel
    generation: Generation


class LLMError(RuntimeError):
    """Base exception with an actionable, prompt-free message."""


class LLMUnavailable(LLMError):
    pass


class LLMModelMissing(LLMError):
    pass


class LLMTimeout(LLMError):
    pass


class LLMInferenceError(LLMError):
    pass


class LLMMalformedOutput(LLMError):
    pass


class LLMProvider(Protocol):
    def health(self) -> HealthStatus: ...

    def generate(self, prompt: str, system: str | None = None) -> Generation: ...

    def generate_structured(
        self, prompt: str, schema: type[StructuredT], system: str | None = None
    ) -> StructuredGeneration: ...
