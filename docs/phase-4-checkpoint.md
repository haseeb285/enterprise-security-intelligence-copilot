# Phase 4 checkpoint

Completed on 2026-09-18 on Apple M3 arm64 with 16 GB unified memory. This phase implements only a native macOS Ollama provider, text generation, schema-constrained generation, health and error handling, and a small local smoke evaluation. Phase 3 retrieval remains separate, including its 0.805 threshold and measured 34/39 positive acceptance and 8/8 negative rejection.

## Native installation and selected model

Installed the signed official macOS `Ollama-darwin.zip` as `/Applications/Ollama.app`; `codesign --verify --deep --strict` passed. Bundled CLI and API both reported **Ollama 0.34.2**. The CLI could not be linked into `/usr/local/bin` and Launch Services could not open the app inside this execution environment, so a native CLI `ollama serve` process was used. `/api/version` and `/api/tags` were reachable, and the selected model was present. PostgreSQL 17.11 and Qdrant v1.19.1 stayed healthy throughout.

Selected **`qwen3.5:4b`**, 4.66B parameters, Q4_K_M, approximately **3.4 GB** download. The single comparison candidate was `qwen3:4b-instruct`, 4.02B, Q4_K_M, approximately 2.5 GB. Both models were downloaded to Ollama's normal cache outside Git. Only one model was loaded at a time; the original comparison model was removed after evaluation, leaving only the selected model installed. The newer model was chosen because its structured responses avoided two unsupported evidence claims from the smaller model in the identical strict smoke set; it was slower and larger, and initially misclassified one evidence-sufficiency flag. A clarified field contract corrected that case in the selected model's final run. These twelve prompts do not establish general superiority.

The first Metal-backed load returned HTTP 500 because Ollama could not allocate a 10 KB Metal buffer in this execution environment. `LLAMA_ARG_DEVICE=none` allowed native **CPU** inference; `ollama ps` reported 100% CPU and context 4096. Metal latency and memory performance were not measured. This is an environment limitation; the binary itself supports arm64. Model loading was limited to one instance and one parallel request. The application requests a 4096-token context, 384 output tokens, temperature 0.1, 180-second inference read timeout, five-second connection timeout, and one-minute keep-alive. First cold load in the smoke trial was 3.54 seconds for Qwen3 and 5.07 seconds for Qwen3.5. First-token timing was not measured because the provider requests non-streaming responses.

## Measured local smoke results

`evaluation/llm_smoke.json` has 12 fictional prompts: eight text cases (including insufficient evidence and Arabic) and four strict structured cases. Checks cover exact formatting, key content, structured schema and sufficiency, and known unsupported evidence claims. Timings include HTTP and local generation. The comparison rows used the **same prompt file, provider settings, and checks**; the final selected row follows a clarification of `sufficient_evidence` and an explicit missing-backup-target prompt. See ignored `work/llm-smoke-qwen3.json`, `work/llm-smoke-qwen35.json`, and `work/llm-smoke-qwen35-validated.json` for response-level local records.

| Run | Smoke checks | Schema-valid | Mean / median latency | Observed issue |
| --- | ---: | ---: | ---: | --- |
| Qwen3 4B Instruct, strict comparison | 10/12 | 4/4 | 3.07 / 2.45 s | Invented absence of successful sign-ins; overstated backup reliability |
| Qwen3.5 4B, same strict comparison | 11/12 | 4/4 | 3.94 / 3.34 s | Cautious but incorrect sufficiency flag for a factual summary |
| Qwen3.5 4B, clarified final contract | 12/12 | 4/4 | 3.80 / 2.39 s | None caught by this small set or manual review of its four structured responses |

A preliminary Qwen3 trial with a 256-token output cap scored 11/12 and 3/4 schema-valid: one JSON response was cut off mid-string. Raising the cap to 384 and detecting `done_reason=length` made this failure explicit and removed it in later runs. The final insufficient-evidence text response declined to determine a password policy; structured insufficient-evidence cases returned `sufficient_evidence=false` and empty evidence. The Arabic instruction produced Arabic text. These are simple smoke observations, not proof of robust grounding or multilingual performance.

## Implementation and validation

`LLMProvider` protocol and typed results/errors live in `app/llm/provider.py`. `OllamaProvider` wraps native HTTP and classifies unreachable service, missing model, connection/read timeouts, inference errors, empty and malformed responses, and schema failures. `AnalysisResponse` uses strict Pydantic validation and has no model-authored citation field. Ollama's native JSON-schema `format` is used; there is no regex repair or retry loop. Logs contain provider, model, outcome, duration, and structured flag, never prompts or generated content. The ordinary tests use `httpx.MockTransport`; the separately marked live test is opt-in.

Validation completed:

- Native Ollama API/version, model list, real text generation, real structured generation, and insufficient-evidence prompts: passed on the selected model.
- PostgreSQL and Qdrant: Docker health `healthy`; Qdrant `/readyz` passed. Alembic schema check: no new upgrade operations.
- Full pytest suite: **47 passed, 1 opt-in live test skipped**. Separately, `RUN_LIVE_OLLAMA=1 .venv/bin/python -m pytest -m live_ollama -q`: **1 passed**, with 47 ordinary tests deselected.
- Ruff lint and format: passed (51 files formatted); `pip check`: no broken requirements; Compose config and `git diff --check`: passed. `.env`, private policy directory, and `work/` are Git-ignored. A scan of Phase 4 source, tests, prompts, and documentation found no private organization names or credential assignments; no model artifacts are tracked.

## Limits and next phase

The Mac execution environment could not initialize Metal, so this checkpoint contains CPU timings only. The GUI app and `/usr/local/bin` symlink were not usable here; the signed app and bundled CLI were installed and the native service was reachable. The model may still invent facts outside these prompts; Pydantic validates form, not factual support. The smoke set was iteratively improved after inspecting failures and is a development set, not an independent benchmark. No RAG answer generation, agent, tool calling, anomaly model, API, or UI was built. The Phase 3 Hugging Face model snapshot remains documented but unpinned in code.

**Proposed Phase 5 only, subject to approval:** implement a versioned FastAPI boundary with validated request/response schemas, bounded inputs, demo token authentication and basic roles, dependency health and safe error responses, audit hooks, mocked service tests, and OpenAPI validation. Do not add agent orchestration, RAG answer generation, ML, or UI in Phase 5.
