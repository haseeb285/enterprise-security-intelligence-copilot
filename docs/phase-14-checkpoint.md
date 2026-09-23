# Phase 14 checkpoint — practical hardening

**Scope:** Phase 14 only. This pass hardened existing boundaries with small tests and one grounding fix. It did not add production IAM, services, tools, models, infrastructure, frontend features, or Phase 15 documentation work. Existing RAG, LLM, ML, and integrated evaluation settings and measured results were unchanged.

## Changes and findings

- Expanded API regressions to assert safe missing/invalid bearer responses and a generic malformed-JSON validation response that does not echo submitted connection data. Existing tests continue to cover reader/admin separation, strict IDs, timezone-aware ranges, pagination/result/input caps, PostgreSQL failure, Qdrant failure, Ollama/model readiness, and missing ML artifacts.
- Added user-text and event-evidence injection regressions alongside the existing policy-evidence regression. Request text cannot expand the request-derived tool set, evidence stays untrusted in synthesis, and write recommendations are filtered.
- Added an exact six-tool allowlist regression. The graph still permits only policy/event/user/incident lookup and bounded anomaly analysis; there is no shell, arbitrary SQL/HTTP, deletion, IP block, user disable, password change, or other write tool.
- Added generated anomaly-flag validation parallel to the existing exact-score validation. A claim such as “flagged anomalous” is retained only when it agrees with typed application-owned ML evidence; a conflict becomes a neutral application-reported flag reference and records `anomaly_flag_reference_filtered`.
- Added one two-thread sanity check over the same compiled graph. Overlapping investigations retained distinct request IDs, state, source lists, and event evidence.
- Replaced the README's machine-specific Anaconda executable with the portable `python3.11` command. Container user paths and the historical Phase 0 environment inventory were retained because they describe their actual contexts.

## Publication check

The current index contains 140 tracked files. The reachable Git history contains 140 unique paths and 258 blobs. Filename and content checks found:

- no committed `.env` other than the intentional `.env.example`;
- no tracked-but-ignored files;
- no private policy/data directories, runtime ground truth, model artifacts, MLflow databases/artifacts, local work/output files, private keys, or high-confidence AWS, GitHub, OpenAI, Slack, or Google credentials;
- no reachable `/Users/<name>/...` path;
- only fictional policies, deterministic synthetic fixtures, documentation IP ranges, and explicitly disposable example credentials.

The reachable history scan did not modify history. Git metadata contains one non-noreply author mailbox. This is normal commit identity metadata and its public exposure was reviewed before publication. `git fsck` also reported pre-existing unreachable objects. They are outside the reachable publication set and are not transferred by a normal branch push.

## Validation results

- Focused API/agent/ML/evaluation hardening suite: **71 passed** in 2.31 seconds.
- Complete ordinary suite: **154 passed, 1 skipped** in 4.56 seconds. The only skip was the opt-in live Ollama test. PostgreSQL and Qdrant integration tests passed.
- Ruff lint: passed.
- Ruff format check: all **113** discovered Python files formatted.
- `pip check`: no broken requirements.
- Alembic consistency: no new upgrade operations.
- Compose bootstrap profile: valid with disposable environment values.
- OpenAPI: valid 3.1 document with 10 versioned paths and bearer security scheme.
- CI workflow: YAML parsed with the expected `quality`, `tests`, and `containers` jobs; its existing policy assertions remain covered by the suite.
- Live local readiness: API reported ready with PostgreSQL, Qdrant, and Ollama all `ok`; the configured `qwen3.5:4b` model was installed. Existing PostgreSQL, Qdrant, API, and Streamlit containers were healthy.
- Diff whitespace check and reachable current/history publication scans: passed, subject to the author-mailbox privacy decision above.

The suite still reports the known upstream Starlette/AnyIO deprecation warning. Native Ollama generation remains opt-in and was not repeated because this phase changed no provider, model, prompt contract, or evaluation configuration.

## Phase boundary

Phase 14 is complete after the single logical checkpoint commit. Phase 15 has not started.

## Proposed Phase 15 scope — PUBLIC DOCUMENTATION AND DEMO POLISH

Polish the README and focused topic documentation, provide a short reproducible policy and investigation walkthrough, surface the existing measured results and architecture clearly, and state limitations without changing system behavior or evaluation claims.
