"""Provider contract tests require no model, network, or live Ollama."""

import json

import httpx
import pytest

from app.core.settings import Settings
from app.llm.ollama import OllamaProvider
from app.llm.provider import (
    LLMInferenceError,
    LLMMalformedOutput,
    LLMModelMissing,
    LLMTimeout,
    LLMUnavailable,
)
from app.llm.schemas import AnalysisResponse


@pytest.fixture
def settings():
    return Settings(
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="test:4b",
        llm_context_length=2048,
        llm_temperature=0.1,
        llm_timeout_seconds=30,
    )


def provider(settings, handler):
    client = httpx.Client(base_url="http://127.0.0.1:11434", transport=httpx.MockTransport(handler))
    return OllamaProvider(settings, client)


def answer(content="Three steps."):
    return {
        "done": True,
        "model": "test:4b",
        "message": {"content": content},
        "load_duration": 1_000_000_000,
        "eval_count": 8,
    }


def test_health_ready(settings):
    def handler(request):
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "0.34.2"})
        return httpx.Response(200, json={"models": [{"name": "test:4b"}]})

    status = provider(settings, handler).health()
    assert (status.reachable, status.model_available, status.version) == (True, True, "0.34.2")


def test_health_missing_model(settings):
    def handler(request):
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "0.34.2"})
        return httpx.Response(200, json={"models": []})

    status = provider(settings, handler).health()
    assert status.reachable and not status.model_available
    assert "not installed" in status.detail


def test_health_unreachable_and_invalid(settings):
    def unreachable(request):
        raise httpx.ConnectError("connection refused")

    assert not provider(settings, unreachable).health().reachable
    assert not provider(settings, lambda r: httpx.Response(200, json={})).health().reachable


def test_generation_request_and_result(settings):
    def handler(request):
        payload = json.loads(request.content)
        assert payload["model"] == "test:4b"
        assert payload["options"]["num_ctx"] == 2048
        assert payload["options"]["temperature"] == 0.1
        assert payload["stream"] is False
        assert payload["messages"][-1]["content"] == "Give three steps"
        return httpx.Response(200, json=answer())

    result = provider(settings, handler).generate("Give three steps")
    assert result.text == "Three steps."
    assert result.load_seconds == 1
    assert result.output_tokens == 8
    assert result.duration_seconds >= 0


def test_structured_schema_and_validation(settings):
    data = {
        "summary": "No conclusion",
        "evidence": [],
        "interpretation": "Unknown",
        "recommended_next_steps": ["Gather facts"],
        "sufficient_evidence": False,
    }

    def handler(request):
        payload = json.loads(request.content)
        assert payload["format"]["type"] == "object"
        assert "sufficient_evidence" in payload["format"]["required"]
        return httpx.Response(200, json=answer(json.dumps(data)))

    result = provider(settings, handler).generate_structured("No facts", AnalysisResponse)
    assert not result.value.sufficient_evidence
    assert result.value.evidence == []


@pytest.mark.parametrize(
    "content",
    [
        "not JSON",
        "{}",
        '{"summary": 3}',
        '{"summary":"a","evidence":[],"interpretation":"b",'
        '"recommended_next_steps":[],"sufficient_evidence":"yes"}',
    ],
)
def test_structured_malformed(settings, content):
    p = provider(settings, lambda r: httpx.Response(200, json=answer(content)))
    with pytest.raises(LLMMalformedOutput):
        p.generate_structured("Prompt", AnalysisResponse)


@pytest.mark.parametrize(
    "response",
    [answer(""), {"done": False, "message": {"content": "x"}}, {"done": True}, ["wrong"]],
)
def test_bad_response_structure(settings, response):
    p = provider(settings, lambda r: httpx.Response(200, json=response))
    with pytest.raises(LLMMalformedOutput):
        p.generate("Prompt")


def test_truncated_response(settings):
    payload = answer("partial")
    payload["done_reason"] = "length"
    p = provider(settings, lambda r: httpx.Response(200, json=payload))
    with pytest.raises(LLMMalformedOutput, match="truncated"):
        p.generate("Prompt")


def test_invalid_http_json(settings):
    p = provider(settings, lambda r: httpx.Response(200, text="not JSON"))
    with pytest.raises(LLMMalformedOutput):
        p.generate("Prompt")


def test_timeout_unavailable_missing_and_server_error(settings):
    for exception, expected in (
        (httpx.ConnectTimeout("slow"), LLMTimeout),
        (httpx.ReadTimeout("slow"), LLMTimeout),
        (httpx.ConnectError("offline"), LLMUnavailable),
        (httpx.ReadError("disconnected"), LLMUnavailable),
    ):

        def fail(request, error=exception):
            raise error

        with pytest.raises(expected):
            provider(settings, fail).generate("Prompt")
    with pytest.raises(LLMModelMissing):
        provider(settings, lambda r: httpx.Response(404)).generate("Prompt")
    with pytest.raises(LLMInferenceError):
        provider(settings, lambda r: httpx.Response(503)).generate("Prompt")


def test_prompt_validation(settings):
    p = provider(settings, lambda r: httpx.Response(200, json=answer()))
    for prompt in (" ", "x" * 8001):
        with pytest.raises(ValueError):
            p.generate(prompt)


def test_request_log_omits_prompt_and_response(settings, caplog):
    secret_marker = "PRIVATE_PROMPT_MARKER"
    p = provider(settings, lambda r: httpx.Response(200, json=answer("PRIVATE_OUTPUT_MARKER")))
    with caplog.at_level("INFO"):
        p.generate(secret_marker)
    assert "provider=ollama" in caplog.text
    assert secret_marker not in caplog.text
    assert "PRIVATE_OUTPUT_MARKER" not in caplog.text


def test_configuration_limits():
    for kwargs in (
        {"llm_timeout_seconds": 0},
        {"llm_context_length": 32000},
        {"llm_temperature": 3},
        {"llm_max_output_tokens": 0},
    ):
        with pytest.raises(ValueError):
            Settings(**kwargs)
