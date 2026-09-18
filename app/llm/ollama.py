"""Native macOS Ollama HTTP adapter. No prompt or generated text is logged."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from app.core.settings import Settings
from app.llm.provider import (
    Generation,
    HealthStatus,
    LLMInferenceError,
    LLMMalformedOutput,
    LLMModelMissing,
    LLMTimeout,
    LLMUnavailable,
    StructuredGeneration,
    StructuredT,
)

LOGGER = logging.getLogger(__name__)


class OllamaProvider:
    """One small Ollama-specific boundary around HTTP and response validation."""

    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self.settings = settings
        self.model = settings.ollama_model
        self.client = client or httpx.Client(
            base_url=str(settings.ollama_base_url),
            timeout=httpx.Timeout(settings.llm_timeout_seconds, connect=5, write=10, pool=5),
        )

    def health(self) -> HealthStatus:
        try:
            version_response = self.client.get("/api/version")
            version_response.raise_for_status()
            version = version_response.json().get("version")
            if not isinstance(version, str) or not version:
                raise ValueError("missing version")
            tags_response = self.client.get("/api/tags")
            tags_response.raise_for_status()
            models = tags_response.json().get("models")
            if not isinstance(models, list):
                raise ValueError("missing model list")
            available = any(
                isinstance(item, dict) and self.model in (item.get("name"), item.get("model"))
                for item in models
            )
            detail = (
                "ready"
                if available
                else (
                    f"Ollama is reachable, but {self.model} is not installed; pull that model first"
                )
            )
            return HealthStatus(True, available, version, detail)
        except (httpx.ConnectError, httpx.TimeoutException):
            return HealthStatus(False, False, None, "Ollama is unreachable; start native Ollama")
        except (httpx.HTTPError, ValueError, TypeError, AttributeError):
            return HealthStatus(False, False, None, "Ollama health response is invalid")

    def _post(self, prompt: str, system: str | None, schema: type[BaseModel] | None) -> Generation:
        if not prompt.strip() or len(prompt) > 8000:
            raise ValueError("Prompt must have 1–8000 characters")
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        request: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "think": False,
            "keep_alive": self.settings.llm_keep_alive,
            "options": {
                "num_ctx": self.settings.llm_context_length,
                "num_predict": self.settings.llm_max_output_tokens,
                "temperature": self.settings.llm_temperature,
            },
        }
        if schema is not None:
            request["format"] = schema.model_json_schema()
        start = time.perf_counter()
        outcome = "failure"
        try:
            response = self.client.post("/api/chat", json=request)
            if response.status_code == 404:
                raise LLMModelMissing(
                    f"Ollama model {self.model} is missing; run `ollama pull {self.model}`"
                )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or payload.get("done") is not True:
                raise LLMMalformedOutput("Ollama returned an incomplete or invalid response")
            if payload.get("done_reason") == "length":
                raise LLMMalformedOutput(
                    "Ollama response was truncated; increase LLM_MAX_OUTPUT_TOKENS "
                    "or shorten the prompt"
                )
            message = payload.get("message")
            content = message.get("content") if isinstance(message, dict) else None
            if not isinstance(content, str) or not content.strip():
                raise LLMMalformedOutput("Ollama returned empty or invalid content")
            model = payload.get("model")
            if not isinstance(model, str) or not model:
                raise LLMMalformedOutput("Ollama response omitted its model")
            outcome = "success"
            return Generation(
                content.strip(),
                model,
                time.perf_counter() - start,
                payload.get("load_duration") / 1e9
                if isinstance(payload.get("load_duration"), (int, float))
                else None,
                payload.get("eval_count") if isinstance(payload.get("eval_count"), int) else None,
            )
        except httpx.TimeoutException as exc:
            raise LLMTimeout(
                f"Ollama inference timed out after {self.settings.llm_timeout_seconds} seconds"
            ) from exc
        except httpx.ConnectError as exc:
            raise LLMUnavailable("Ollama is unreachable; start native Ollama") from exc
        except httpx.RequestError as exc:
            raise LLMUnavailable("Ollama connection failed; check the native service") from exc
        except httpx.HTTPStatusError as exc:
            raise LLMInferenceError(
                f"Ollama request failed with HTTP {exc.response.status_code}; "
                "check the native Ollama logs and model memory"
            ) from exc
        except (ValueError, TypeError) as exc:
            raise LLMMalformedOutput("Ollama returned invalid JSON or response structure") from exc
        finally:
            LOGGER.info(
                "llm_request provider=ollama model=%s outcome=%s duration_ms=%.1f structured=%s",
                self.model,
                outcome,
                (time.perf_counter() - start) * 1000,
                schema is not None,
            )

    def generate(self, prompt: str, system: str | None = None) -> Generation:
        return self._post(prompt, system, None)

    def generate_structured(
        self, prompt: str, schema: type[StructuredT], system: str | None = None
    ) -> StructuredGeneration:
        concise = (
            "Return concise JSON matching the schema. Keep each string brief and use at most "
            "two evidence items and two next steps. Evidence items must restate only explicit "
            "input facts. Do not assume unmentioned events did not occur or generalize from one "
            "test. Do not claim a target, benchmark, or policy requirement was met unless its "
            "value is supplied. If no evidence is available, set sufficient_evidence to false "
            "and evidence "
            "to an empty list. Set sufficient_evidence to true when supplied facts support a "
            "cautious factual summary; this does not prove cause or compromise."
        )
        generation = self._post(prompt, f"{concise}\n{system}" if system else concise, schema)
        try:
            value = schema.model_validate_json(generation.text)
        except ValidationError as exc:
            LOGGER.warning("llm_structured_validation_failure provider=ollama model=%s", self.model)
            raise LLMMalformedOutput("Ollama structured output failed schema validation") from exc
        return StructuredGeneration(value, generation)
