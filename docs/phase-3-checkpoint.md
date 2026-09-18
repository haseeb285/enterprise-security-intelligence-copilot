# Phase 3 checkpoint

Completed on 2026-09-18, macOS Apple M3 arm64 with 16 GB unified memory, Python 3.11.7, local PostgreSQL 17.11, Qdrant `qdrant/qdrant:v1.19.1`, Sentence Transformers 6.0.1, and `intfloat/multilingual-e5-small` (384-dimensional, ~471 MB safetensors, MIT). No LLM or Ollama was installed or integrated in this phase.

## Deliverables

- Seven original Clockwork Badger Cooperative policies, each clearly labeled synthetic; Markdown, UTF-8 TXT, and text PDF extraction, validation, section/page-aware chunking, metadata, and citations.
- Local E5 passage/query embeddings and Qdrant with loopback-only configurable host/port, persistent named volume, and in-container `/readyz` health check.
- Idempotent ingestion with SHA-256 raw-document hashes, deterministic chunk IDs, changed-document replacement, explicit corpus-scoped deletion pruning, and configuration mismatch protection.
- Bounded, threshold-gated structured retrieval and a 47-case evaluation CLI with English and Arabic questions.
- Offline tests and a live local Qdrant test. Earlier PostgreSQL schema, migrations, generator, and queries remain intact.

## Actual local measurements

The CLI first downloaded the model into the normal Hugging Face cache, outside Git. The first run reported `model_init_s=73.185` (download included), `ingestion_s=0.497` for seven documents before the final label-only-chunk exclusion. A later warm model load reported `10.180 s`; repeat ingest reported `0.059 s`, discovered 7, ingested 0, skipped 7, created 0 chunks, avoided 28 duplicates, failures 0. Final default collection has **28 chunks**. Alternate 300/40 collection has 29.

| Configuration | Chunks | Recall@1 | Recall@3 | Recall@5 | MRR | No-answer rejected | Positive accepted | Arabic Recall@1 | Query mean / median |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| E5-small, 650 characters / 80 overlap | 28 | 39/39 (1.000) | 39/39 (1.000) | 39/39 (1.000) | 1.000 | 8/8 | 34/39 | 4/4 | 19.63 / 18.92 ms |
| E5-small, 300 characters / 40 overlap | 29 | 39/39 (1.000) | 39/39 (1.000) | 39/39 (1.000) | 1.000 | 8/8 | 34/39 | 4/4 | 18.27 / 17.12 ms |

The default is 650/80 because retrieval ranks and gating matched the shorter setting with one fewer vector; the small latency difference is run-to-run noise and not evidence of a speed advantage. Threshold **0.805** is a development-set choice: it rejects eight labeled no-answer questions but also suppresses evidence for five positive questions. Rank metrics use raw top-five results; gate counts apply the threshold. Four Arabic positives all ranked correctly at top one, but this tiny subset says little about general Arabic quality. Two Arabic negatives were rejected.

Representative live outputs: an English password-length query retrieved `Password and Authentication Policy — 1. Password requirements` at score 0.900; its Arabic counterpart retrieved the same citation at 0.807; the maternity-leave question returned `insufficient_evidence=True` and no citation.

## Validation

- `docker compose ps`: PostgreSQL 17.11 `healthy` at loopback `:5433`; Qdrant v1.19.1 `healthy` at loopback `:6333`; `/readyz` responded `all shards are ready`.
- `.venv/bin/alembic check`: no new upgrade operations; existing migration remains current.
- `.venv/bin/python -m pytest -q`: **28 passed**, including live Qdrant and PostgreSQL integration.
- `.venv/bin/ruff check .` and `.venv/bin/ruff format --check .`: passed.
- `.venv/bin/python -m pip check`: no broken requirements.
- `docker compose config --quiet`, `git diff --check`: passed.
- `git check-ignore`: private policy and `work/` paths ignored; model cache is outside Git.

## Limits and Phase 4 proposal

The 47 queries were written against the synthetic policies and used to select the threshold, so these are development-set scores, not independent quality estimates. The high rank scores are for a small and distinct corpus. No OCR is implemented; scanned PDFs fail as textless. E5 similarity alone cannot guarantee semantic answerability, and stronger no-answer evaluation is needed. The documented Hugging Face snapshot is not pinned in code; a later model revision should use a new collection. Chunk replacement is not an atomic multi-document operation, and a crash can temporarily leave two versions until re-ingestion. There is no public/private cross-corpus filtering beyond separate corpus markers and recommended separate collections.

**Proposed Phase 4 only, subject to approval:** add a configurable local LLM provider interface and native macOS Ollama adapter with availability, timeout and error handling, mocked contract tests, and a measured local smoke test. Do not add an agent, API, ML pipeline, or UI in Phase 4.
