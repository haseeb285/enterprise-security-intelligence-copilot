# Final engineering audit and publication readiness

**Scope:** Phase 16 verification only. No feature, dependency, API, page, model, tool, threshold, dataset, evaluation case, infrastructure component, or runtime behavior was added or changed.

## Implemented, tested, documented, demonstrated

`Yes` means the repository contains direct evidence for that column. Historical live evidence is identified where the final audit deliberately avoided an expensive rebuild or evaluation rerun.

| Capability | Implemented | Tested | Documented | Demonstrated / evaluated |
| --- | :---: | :---: | :---: | --- |
| PostgreSQL security data | Yes | Yes | Yes | Live integration passed; final API smoke read events. |
| Deterministic synthetic dataset | Yes | Yes | Yes | 120 users, 140 devices, 12,065 events, 6 incidents, 6 scenarios. |
| RAG ingestion and retrieval | Yes | Yes | Yes | 47-query Phase 10 retrieval evaluation. |
| `multilingual-e5-small` embeddings | Yes | Yes | Yes | Live corpus/evaluation used 384-dimensional normalized vectors. |
| Qdrant vector store | Yes | Yes | Yes | Final live collection: 384 dimensions, 28 policy chunks. |
| Fixed relevance gate | Yes | Yes | Yes | `0.805`; 34/39 answerable accepted and 8/8 unanswerable rejected. |
| Ollama / `qwen3.5:4b` | Yes | Yes | Yes | Mocked contracts, prior live evaluation, and final live smoke; opt-in unit marker skipped. |
| Structured generation | Yes | Yes | Yes | 12/12 checks and 4/4 schemas in Phase 10. |
| Bounded LangGraph | Yes | Yes | Yes | 20/20 expected integrated routes; five graph nodes. |
| Six read-only agent tools | Yes | Yes | Yes | Exact allowlist, access, routing, bound, and injection regressions pass. |
| Isolation Forest | Yes | Yes | Yes | 5/6 scenarios detected on synthetic holdout. |
| Twenty-feature engineering pipeline | Yes | Yes | Yes | Determinism, time bounds, leakage exclusions, and chronological split tested. |
| MLflow tracking | Yes | Yes | Yes | Local parameters, metrics, run, and artifact logging tested and exercised in Phase 7. |
| FastAPI | Yes | Yes | Yes | Ten-path OpenAPI contract and live ready API. |
| Streamlit | Yes | Yes | Yes | Client/render tests, historical browser verification, and final health response. |
| Grounding and provenance enforcement | Yes | Yes | Yes | 20/20 source/citation/score/flag fidelity; injection and unsupported-claim regressions. |
| Layered evaluation framework | Yes | Yes | Yes | Tracked retrieval, generation, integrated, ML, safety, latency, and manual-review results. |
| Observability and request IDs | Yes | Yes | Yes | Safe-field logs/metrics tested; final smoke used a correlated request ID. |
| Docker Compose | Yes | Yes | Yes | Final config valid; six existing containers healthy across development/validation stacks. |
| Clean bootstrap | Yes | Yes | Yes | Phase 12 fresh-volume migrate/seed/ingest/train/start and idempotency evidence; not repeated. |
| GitHub Actions workflow | Yes | Yes | Yes | Local YAML/policy validation and build design complete; first hosted run remains pending. |
| Security and hardening | Yes | Yes | Yes | Auth, roles, bounds, safe failures, prompt injection, concurrency, and publication scans pass. |

No cosmetic matrix gap requires implementation. The only demonstration boundary is GitHub Actions: the workflow is locally validated but has not run on GitHub because no remote is configured.

## Claim audit

Prominent README, demo, security, deployment, evaluation, and specification claims were checked against source, tests, Compose, and tracked evaluation artifacts.

- Phase 10 metrics, 154-test count, model and embedding names, 384-vector dimension, six tools, seven policy files, 28 policy chunks, data counts, latency, ML results, and exact U105 score/flag are consistent.
- The project specification remains an original requirements document; its `potential` routes and `likely` topology are not presented as implemented claims. Current documentation describes the actual implementation.
- Phase 8 and Phase 10 latency values differ because they are clearly labeled separate measured runs, not conflicting values.
- One real overstatement was corrected: native Ollama preserves access to macOS acceleration, but the recorded Phase 4 smoke run required CPU fallback after a Metal allocation failure. README and deployment wording now make no measured Metal-performance claim.
- Phase 15's self-referential Markdown/Ruff counts now state that they were recorded before its checkpoint file was added.

No evaluation result, threshold, model output, or test outcome was changed.

## Final validation

- Complete ordinary suite: **154 passed, 1 skipped** in 5.53 seconds. The skip is the opt-in live Ollama test.
- Ruff lint: passed.
- Ruff format: all **118** discovered source/document files passed after this audit file was added.
- `pip check`: no broken requirements.
- Alembic: no new upgrade operations detected.
- Compose bootstrap profile: valid with disposable values.
- OpenAPI: valid 3.1 document with 10 paths and bearer scheme.
- GitHub Actions: valid YAML with `quality`, `tests`, and `containers`; push-to-main and pull-request triggers; `contents: read`; five action uses pinned to full SHAs; no `pull_request_target` or `continue-on-error`.
- Documentation: **37** Markdown files, all local links resolved, all code fences balanced.
- README: exactly one Mermaid `flowchart TB`; delimiters and required primary components passed static sanity checks.
- Git whitespace: passed.

The known upstream Starlette/AnyIO deprecation warning remains non-failing.

## Final local stack smoke

No rebuild or bootstrap was needed. Existing PostgreSQL and Qdrant development and isolated validation containers were healthy. Native Ollama `0.34.2` listed `qwen3.5:4b`; Qdrant reported all shards ready; FastAPI reported application, PostgreSQL, Qdrant, and Ollama `ok`; Streamlit returned `ok`.

One real reader-role investigation used the demo's three-source U104 request. It returned HTTP 200 in 63.902 seconds with outcome `complete`, sufficient evidence, the expected three tools, five event records, one ML result, three cited policy records, three tool calls, five graph steps, and nine application-owned sources. This is a smoke observation, not a new benchmark.

## Publication safety and Git history

The final reachable publication set contains **145 tracked paths** and **277 unique reachable blobs**. The scan found no:

- committed `.env` beyond `.env.example`, tracked-but-ignored file, private key, or high-confidence cloud/API token;
- private/confidential policy directory, customer or personal dataset, runtime ground truth, model artifact, MLflow database/artifact, raw evaluation work output, temporary archive, or accidental binary;
- developer-specific macOS home path in tracked content or reachable blobs.

The synthetic policies, sanitized tracked evaluation summaries, disposable CI examples, container-internal `/home/esic` paths, and Phase 0 `/opt/anaconda3/...` environment record are intentional. History was not rewritten.

Before this commit, all 15 reachable commits used one non-noreply author identity. This final audit commit uses the same configured identity, making the post-commit result **16/16 reachable commits and one identity** with that mailbox. The value is not reproduced here. The owner must decide whether it is acceptable to publish. Removing it later requires a separate, explicit history rewrite before the first push.

## Screenshot readiness

No screenshot was fabricated. `docs/demo.md` accurately specifies these captures:

1. **Dashboard:** use the admin demo token and show readiness, the 12,065-event total, six incidents, and one chart.
2. **Investigation Copilot:** submit `Investigate suspicious activity for U104 on 2026-08-31 and determine whether relevant password policy controls apply.` Capture observed events, typed ML evidence, and a policy citation.
3. **Investigation Copilot:** submit `Is U105 behaving unusually on 2026-08-31?` Capture Germany/Japan events alongside score `-0.21107408822812324` and `flagged=false`.
4. **System Health / evaluation:** capture ready dependencies and aggregate metrics, or the tracked `evaluation/results/phase10-summary.md` table.

Review every image for tokens, local usernames, terminal history, `.env` content, and unrelated applications before committing it.

## GitHub publication checklist recorded at audit time

- [x] Review public exposure of the existing non-noreply author mailbox.
- [x] Capture and review the selected real screenshots.
- [x] Create the public GitHub repository and configure the intended remote.
- [x] Push `main` without rewriting history.
- [x] Inspect the public file list for unexpected files and confirm `.env`, models, runtime data, and work outputs are absent.
- [x] Verify the first GitHub Actions run succeeds on the hosted runner.
- [x] Add and verify the CI badge after the hosted workflow passes.
- [x] Apply the description and topics recorded in `docs/phase-15-checkpoint.md`.
- [x] Verify README tables, links, code blocks, images, and Mermaid rendering on GitHub.

## Known limitations and readiness decision

The project remains a local synthetic demonstration with demo bearer authentication, local-model latency, relevance-gate false negatives, Isolation Forest false positives, the U105 impossible-travel miss, one generic password-policy response, and no production identity, TLS, managed secrets, or high availability. At audit time, hosted CI and reviewed screenshots were still pending; both were completed during publication.

Engineering, validation, documentation, and tracked-content safety gates pass. At the time of this audit, public release was pending review of the non-noreply author mailbox. That identity choice was subsequently reviewed, and screenshots were added before publication.
