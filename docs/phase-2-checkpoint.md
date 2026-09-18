# Phase 2 checkpoint

Completed on 2026-09-18 using macOS arm64, Python 3.11.7, PostgreSQL `17.11-bookworm` arm64, SQLAlchemy 2.0.54, Alembic 1.20.0, and psycopg 3.3.5. This phase implements only the structured data layer and synthetic dataset.

## Implemented

- One local PostgreSQL Compose service with a persistent named volume, loopback host binding, configured credentials and port, and a health check.
- SQLAlchemy models for fictional users, devices, security events, incidents, and audit logs; an initial Alembic migration; bounded repository queries.
- Deterministic synthetic generator and idempotent seed CLI. A separate ignored JSON file contains scenario ground truth for future evaluation.
- SQLite-backed isolated tests for generator, models, repository, safety checks, and reset, plus a read-only live PostgreSQL integration test when configured.

## Measured live results

| Check | Result |
| --- | --- |
| Container/image | PostgreSQL 17.11, arm64, Docker health `healthy` |
| Fresh migration | `alembic upgrade head` succeeded to `20260918_01` |
| Migration/schema agreement | `alembic check`: no new upgrade operations |
| Seed 42 | 120 users, 140 devices, 12,065 security events, 6 incidents, 6 injected scenarios |
| Initial generation / insert | 0.032 s / 1.260 s |
| Explicit reset generation / insert | 0.031 s / 1.455 s |
| Repeat seed | `already_seeded`, no duplicate insertion |
| Live repository checks | 25 matching brute-force source events; bounded user and incident pages; UTC-aware PostgreSQL timestamp |
| Full pytest suite | 15 passed, including Phase 1 tests and live PostgreSQL integration |
| Ruff lint and format | Passed |
| `pip check` | No broken requirements |

The six scenario types are brute-force pattern, impossible-travel pattern, privileged-account anomaly, account-compromise pattern, suspicious endpoint behavior, and firewall burst. Event and incident content is synthetic demonstration material, not a production detection dataset. `data/runtime/ground_truth.json` and `.env` are Git-ignored. No scenario label or expected reason is stored as an event feature; incident links must be excluded from later ML features.

## Limits and next phase

SQLite unit tests use `create_all` for isolation; PostgreSQL uses Alembic. The seed CLI is designed for a dedicated demo database and refuses replacement if its manifest or expected counts are missing. Future operational writes will require revisiting the seed guard and audit count policy. No API, RAG, agent, LLM, ML training, or frontend exists yet.

Proposed Phase 3 only: add a compact local embedding model and Qdrant service; build PDF/Markdown/TXT extraction, validation, deterministic chunking, duplicate detection, metadata-preserving ingestion, relevance-gated retrieval, citation tests, and a clean ingestion CLI. Select and pin the embedding model after checking current Python/arm64 compatibility and memory use. Wait for user approval before beginning.
