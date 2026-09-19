# Phase 10 checkpoint — layered evaluation

**Scope:** Phase 10 only. Added a reproducible layered evaluation framework and fixed two defects exposed by it: the complete-suite CLI selection condition and a narrow generated-score guard. No model retraining, retrieval threshold tuning, frontend work, broad observability, deployment, or write-capable action was added.

> This is synthetic development evaluation on a small local suite. It is not production SOC performance, and no combined accuracy score is reported.

## Implementation

- Added the versioned `1.0.0` suite manifest while reusing the existing retrieval, structured-generation, routing, integrated, and ML artifacts.
- Added `python -m app.evaluation.run --offline|--live|--all` with ignored detailed output and deterministic sanitized JSON/Markdown summaries.
- Formalized retrieval gate rates, citation correctness, repeat consistency, per-case records, and cold/warm latency.
- Added integrated scoring for routing, execution bounds, typed category separation, identifiers, citations, exact ML output, sources, sufficiency, structured responses, and unsupported generated identifiers/scores.
- Added thirteen deterministic failure/safety contracts and six application-owned fact checks.
- Bound the explicit manual rubric to the reviewed runtime artifact hash.
- Fixed the existing integrated evaluator so an empty case selection runs the complete suite.
- Extended the score guard to filter rounded numeric references phrased as an ML/model score. Only the affected integrated case was rerun after the fix.

## Measured results

The generated, machine-derived result table is [evaluation/results/phase10-summary.md](../evaluation/results/phase10-summary.md). Highlights:

- Retrieval ranking: Recall@1/3/5 `1.000`, MRR `1.000`, citation/source `39/39`; fixed-gate acceptance `34/39`, rejection `8/8`.
- Structured generation: `12/12` checks, `4/4` valid schemas, zero malformed structured outputs.
- Integrated: `20/20` tool selection and completion; zero unnecessary calls; `35` valid and zero malformed structured calls; `20/20` provenance, citations, exact scores/flags, category separation, sufficiency, and execution limits; zero unsupported identifiers or score references.
- Deterministic fact checks: `6/6`. Safety/failure contracts: `13/13`.
- Manual rubric: `20/20` for supported facts, non-contradiction, uncertainty, ML separation, and no invented policy requirement; `19/20` direct answers.
- Baseline ML: `5/6` scenarios, `40/583` false positives (`6.86%`), `11.11%` flagged precision, Top-5 `2/6`, Top-10 `4/6`.
- Latency: retrieval mean/median `22.898/20.960 ms`; ML cold/warm median `52.808/14.169 ms`; integrated mean/median `26.620/29.563 s`.

## Impossible-travel regression

The regression passed because the system preserved the disagreement: events `EV012026` and `EV012027` show Germany and Japan successful logins fifteen minutes apart, while the unchanged model returns exact score `-0.21107408822812324`, `flagged=false`, and rank 325. No rule or model change forced a flag.

## Validation

- Offline evaluation completed with deterministic retrieval repeat equality, reused Phase 7 ML metrics, measured cold/warm inference, the named U105 regression, and `13/13` safety contracts.
- The live `qwen3.5:4b` structured run completed `12/12`; the live integrated run completed `20/20`. Only the one case affected by the rounded-score guard was rerun and merged after the fix.
- Full project suite: **129 passed, 1 skipped** in 4.23 seconds. The native Ollama contract remains deliberately opt in; the sole warning is the known upstream Starlette reference to AnyIO's deprecated `BlockingPortal` alias.
- Evaluation infrastructure contributed **9 passing tests**, including loading, expected labels, metrics, fidelity, unsupported sources/scores, serialization, safety scoring, CLI selection, and impossible travel.
- Ruff lint passed and all **103 Python files** passed the format check. Python compilation and diff whitespace checks passed.
- `pip check` reported no broken requirements. Alembic reported no new upgrade operations. Docker Compose configuration validated.
- PostgreSQL and Qdrant containers were healthy. FastAPI returned HTTP 200 `ready` with application, PostgreSQL, Qdrant, and Ollama all `ok`; native Ollama listed `qwen3.5:4b`.
- Detailed `work/` results, `.env`, and model artifacts were confirmed ignored. Sanitized tracked results contain no local absolute paths. Credential/private-key scans were clean.

## Limits and Phase 11 proposal

The small synthetic suite shares its codebase and data generator with the application. Deterministic checks cover protected facts and sources but cannot prove every natural-language sentence. The manual review is explicit rather than model-judged. Retrieval gate false negatives, the ML false-positive rate and impossible-travel miss, one generic policy answer, and local inference latency remain visible.

The exact proposed Phase 11 scope is structured observability for API requests, retrieval, tool calls, local LLM generation, ML inference, dependency failures, latency, correlation/request IDs, safe logs, and an operational audit review without logging prompts, evidence payloads, credentials, or hidden reasoning. Phase 11 has not started.
