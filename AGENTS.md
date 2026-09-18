# Enterprise Security Intelligence Copilot: engineering rules

Read `docs/project-specification.md` and `docs/phase-0-architecture.md` before changing architecture or scope. This repository is a local portfolio demonstration, not a deployed security product.

## Scope and phase gates

- Work through phases 0–16 in `docs/implementation-checklist.md`. Phases 0 and 1 are approved; complete only the currently authorized phase before moving to the next.
- At each phase boundary, inspect the diff, run relevant tests and lint, verify imports and startup where possible, fix failures, and record an honest checkpoint. Do not build later phases on a known broken foundation.
- Prefer one well-tested implementation per capability. Do not add a dependency only to satisfy a technology checklist.

## Data and claims

- Commit only synthetic security events and fictional, clearly labeled demonstration policies. Use documentation IP ranges. Keep all supplied private policies, credentials, `.env`, model artifacts, and runtime data out of Git.
- Call the event interface a **simulated SIEM**. Describe ML results as synthetic-data demonstrations, never as real-world detection performance. Do not claim cloud or production deployment.
- Do not invent events, policy requirements, citations, benchmark results, tests, or successful runs. If evidence is weak or missing, say so.

## Architecture and quality

- Run Ollama natively on macOS; keep the model configurable. Use defined, read-only evidence tools for the agent. Keep LLM interpretation separate from observed evidence, ML scores, policy context, and recommendations.
- Keep configuration in environment variables, validate inputs, limit request size, authenticate demo API routes, enforce basic roles, log audit events, and return safe errors. Document that demo authentication is not enterprise SSO.
- Preserve citation metadata and validate retrieval relevance. Fail clearly when Ollama, PostgreSQL, Qdrant, or the knowledge base is unavailable.
- Use deterministic synthetic data and reproducible evaluation. Publish only measured results with commands and environment details.
- Use type hints, small modules, migrations, automated tests, Ruff, CI, and structured logging. Mock Ollama in CI.

## Local hardware budget

Target Apple M3 with 16 GB unified memory. Run one quantized 4B-class Ollama model at a time, limit context/concurrency, use one cached embedding model, and avoid unnecessary always-on services. Verify actual memory and latency before tuning.
