# Local LLM foundation (Phase 4)

This phase adds a provider boundary for text and schema-constrained generation. It does **not** combine policy retrieval with generation, implement an agent, or serve a chat API. Ollama runs natively on macOS, outside Docker. PostgreSQL and Qdrant remain separate Compose services.

## Installation and model

The [official macOS `Ollama-darwin.zip`](https://ollama.com/download/mac) for **Ollama 0.34.2** was downloaded and installed as `/Applications/Ollama.app`. The bundled arm64-compatible CLI is `/Applications/Ollama.app/Contents/Resources/ollama`. This execution environment could not register the app with Launch Services or create a `/usr/local/bin/ollama` symlink, so validation used the bundled CLI directly. The model lives in Ollama's normal cache under `~/.ollama/models`, outside Git.

The [Ollama `qwen3:4b-instruct` registry entry](https://ollama.com/library/qwen3%3A4b-instruct) lists 4.02B parameters, Q4_K_M, about 2.5 GB download, Apache 2.0, and tool support. The [newer `qwen3.5:4b` entry](https://ollama.com/library/qwen3.5%3A4b) lists 4.66B parameters, Q4_K_M, about 3.4 GB, and multimodal support. Both were evaluated after the first model made unsupported claims in two otherwise valid structured responses. The default is `qwen3.5:4b`: it avoided two unsupported evidence claims seen with the smaller candidate, while both produced 4/4 schema-valid responses. It is larger and slower in the local CPU trial. Its initial sufficiency flag was overly cautious, and manual review later caught a separate unsupported recovery-target claim. A clarified sufficiency contract and explicit missing-target case led to 12/12 final smoke checks. The original comparison model was removed after evaluation. This local comparison is not a general quality claim.

The observed Ollama process reported 100% CPU. In this execution environment its Metal backend failed to initialize even a tiny buffer, returning HTTP 500. Starting native Ollama with `LLAMA_ARG_DEVICE=none` allowed successful CPU inference. The model's Apple Silicon binary was verified as arm64-compatible, but **Metal performance was not measured**. This CPU fallback is an environment finding, not a project default. For normal macOS use, start the app normally when possible; the validated fallback command is:

```bash
LLAMA_ARG_DEVICE=none OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_NUM_PARALLEL=1 \
  /Applications/Ollama.app/Contents/Resources/ollama serve
```

In a second terminal, verify with the bundled CLI and `/api/version`, then pull the one selected model if needed:

```bash
/Applications/Ollama.app/Contents/Resources/ollama pull qwen3.5:4b
/Applications/Ollama.app/Contents/Resources/ollama list
curl -fsS http://127.0.0.1:11434/api/version
```

## Configuration and boundary

`app/llm/provider.py` defines the narrow `LLMProvider` protocol, result types, health status, and actionable error types. `app/llm/ollama.py` owns Ollama HTTP, its native `/api/version`, `/api/tags`, and `/api/chat` payloads. Future application layers can call the protocol without using Ollama-specific request details. `app/llm/schemas.py` provides a strict Pydantic `AnalysisResponse` with summary, evidence, interpretation, next steps, and evidence sufficiency. It deliberately has no citation field. Later citations must come from retrieval or tool metadata.

Environment settings: `OLLAMA_BASE_URL=http://127.0.0.1:11434`, `OLLAMA_MODEL=qwen3.5:4b`, `LLM_TIMEOUT_SECONDS=180`, `LLM_TEMPERATURE=0.1`, `LLM_CONTEXT_LENGTH=4096`, `LLM_MAX_OUTPUT_TOKENS=384`, `LLM_KEEP_ALIVE=1m`. A 4K context is adequate for the planned compact retrieved evidence and avoids the model's much larger advertised maximum. One-minute keep-alive limits idle model memory. The adapter sends non-streaming requests, bounds prompt length to 8,000 characters, limits output tokens, and distinguishes connect/read timeout, unreachable service, missing model, HTTP failure, incomplete/truncated response, and invalid JSON/schema. It does not retry automatically. The `httpx` connect timeout is 5 seconds; the read timeout uses `LLM_TIMEOUT_SECONDS`.

When the later application runs in Docker, override `OLLAMA_BASE_URL=http://host.docker.internal:11434` and configure native Ollama binding deliberately for that environment. The current provider does not change network exposure or add an application container.

Structured generation passes `AnalysisResponse.model_json_schema()` as Ollama's [native `format`](https://docs.ollama.com/capabilities/structured-outputs) and validates returned JSON with strict Pydantic rules. A short system instruction asks for concise JSON, explicit-fact evidence only, and empty evidence when none is supplied. The sufficiency field is defined for a narrow factual summary, not proof of a broader security conclusion. Bad JSON, missing fields, wrong types, extra fields, empty content, or truncation fails clearly; no regex repair or unbounded retry. Provider logs only model, outcome, duration, and whether output was structured. Prompts, private evidence, and generated text are not logged by the provider.

## Evaluation and limits

Run the 12 fictional prompts in `evaluation/llm_smoke.json` with:

```bash
.venv/bin/python -m app.llm.smoke
RUN_LIVE_OLLAMA=1 .venv/bin/python -m pytest -m live_ollama
```

The CLI writes detailed responses and latency to ignored `work/llm-smoke-results.json` for local inspection; it prints only concise pass/fail data. Eight text prompts cover exact instructions, three-step formatting, security terminology, fictional evidence, insufficient evidence, and Arabic. Four prompts test schema-constrained output and sufficiency. Checks are simple development smoke criteria, not a benchmark or proof of hallucination resistance. A first run at 256 output tokens had 11/12 passes and 3/4 valid structured outputs: one schema response was cut off mid-JSON. The default was raised to 384 tokens and a concise structured instruction was added. The same stricter 12-case set was run against both candidates; after a sufficiency-contract clarification and explicit missing-target case, the selected model passed 12/12 checks with 4/4 valid schemas. Measured comparison and final latencies are in `phase-4-checkpoint.md`.

The model can still make unsupported assertions even when its JSON validates. Schema validation guarantees shape and types, not factual correctness. Later integrated evaluation must check evidence grounding and refuse invented citations. Phase 3 threshold 0.805 and its 34/39 positive acceptance, 8/8 negative rejection measurements remain unchanged.
