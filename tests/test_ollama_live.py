"""Opt-in live test: RUN_LIVE_OLLAMA=1 .venv/bin/python -m pytest -m live_ollama."""

import os

import pytest

from app.core.settings import get_settings
from app.llm.ollama import OllamaProvider
from app.llm.schemas import AnalysisResponse


@pytest.mark.live_ollama
def test_native_ollama_inference():
    if os.getenv("RUN_LIVE_OLLAMA") != "1":
        pytest.skip("opt-in live Ollama test")
    provider = OllamaProvider(get_settings())
    status = provider.health()
    assert status.reachable and status.model_available, status.detail
    result = provider.generate("Reply with exactly READY and nothing else.")
    assert result.text.strip() == "READY"
    structured = provider.generate_structured(
        "No supporting evidence is available. State you cannot determine the password "
        "policy. The evidence list must be empty.",
        AnalysisResponse,
    )
    assert not structured.value.sufficient_evidence
    assert structured.value.evidence == []
