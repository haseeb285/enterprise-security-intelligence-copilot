# Phase 3 local policy retrieval

This is an evidence retrieval demonstration over original, fictional policies. It neither interprets policy with an LLM nor answers questions. The `data/policies/synthetic/` documents all carry the two required demonstration labels. Put private local documents only under ignored `data/private_policies/`; never use them for public evaluation.

## Design and selected embedding model

Qdrant `qdrant/qdrant:v1.19.1` runs in Compose with a persistent named volume and a loopback-only, configurable port. `/readyz` is checked after startup. The local Python client holds all vector-store calls in `app/rag/store.py`. PostgreSQL remains a separate service.

Selected `intfloat/multilingual-e5-small` (MIT, 384 dimensions, ~471 MB safetensors, 100-language training, 512-token maximum) for a 16 GB M3. It runs on CPU and its model instance is cached per process. E5 requires `query:`/`passage:` prefixes and normalized embeddings. The model loads through Sentence Transformers with its normal Hugging Face cache; model files are not tracked. Initial cold initialization includes download, warm initialization does not. The local model snapshot used for Phase 3 was `614241f622f53c4eeff9890bdc4f31cfecc418b3`; upgrades should use a fresh collection. The dependency lock pins the Python libraries, while the model revision is documented rather than enforced in code.

Considered `paraphrase-multilingual-MiniLM-L12-v2` (Apache 2.0, 384 dimensions, ~471 MB, 50 languages and a 128-token default) and `BAAI/bge-m3` (1024 dimensions and substantially larger). E5 offers a modest footprint and more headroom for English plus future Arabic documents. We evaluated two chunk settings with E5 instead of downloading a second model; the comparison measures this corpus, not broad model quality.

## Parsing and collection

UTF-8 Markdown and TXT and text-based PDFs are supported; PDF extraction uses pypdf, not OCR. Unsupported, blank, unreadable, malformed, and image-only inputs fail explicitly. Markdown headings delimit sections; TXT uses a document fallback and PDF preserves one-based page numbers. Whitespace is normalized gently; headings and punctuation survive. The two label-only lines in Markdown sources are not indexed as independent evidence.

Default target is 650 characters with 80 characters overlap for long sections. The heading and document title accompany each passage, making short sections retrievable; long sections split at a nearby paragraph, sentence, or word boundary. E5's 512-token maximum comfortably covers this corpus's short sections. A 300/40 alternative was evaluated. These sizes are initial corpus-specific settings, configurable by `RAG_CHUNK_TARGET_CHARS` and `RAG_CHUNK_OVERLAP_CHARS`.

Each Qdrant point uses a stable UUID based on document ID, source content hash, heading/page, position, chunk settings, and model name. Payload carries `document_id`, `document_name`, `document_type`, relative `source`, one-based `page` when available, `section`, `chunk_id`, raw-source SHA-256 `content_hash`, UTC `ingestion_timestamp`, `corpus`, embedding model/settings, and text. Source paths contain only corpus-relative components, not absolute private paths. Citation labels are assembled from this metadata.

A collection has cosine vectors of 384 dimensions. Dimension and the first point's model/chunk configuration are checked before ingest or retrieval. Changing embedding model or chunk settings requires a new `RAG_COLLECTION` and a full ingest; the tool gives an actionable error instead of serving a mismatched index. Repeating ingest skips identical IDs and reports avoided duplicates. Changed documents upsert new IDs before deleting obsolete points. Deletions need explicit `--prune`, scoped to that corpus; a failed parse suppresses pruning for the whole run. This is a small local lifecycle, not an atomic multi-document transaction: a process crash between upsert and delete can briefly leave both versions until the next successful ingest. On failed reads, old indexed evidence stays until repaired or explicitly pruned.

## Commands

Set local PostgreSQL credentials and `QDRANT_PORT=6333` in ignored `.env`, then:

```bash
docker compose up -d postgres qdrant
curl -fsS http://127.0.0.1:6333/readyz
.venv/bin/python -m app.rag.ingest data/policies/synthetic --prune
.venv/bin/python -m app.rag.ingest data/policies/synthetic
.venv/bin/python -m app.rag.evaluate --threshold 0.805
```

The CLI prints discovered/ingested/skipped documents, new chunks, avoided duplicates, failures, and model/ingestion timing. `RAG_COLLECTION`, `EMBEDDING_MODEL`, `RAG_MIN_SCORE`, chunk sizes, and `QDRANT_URL` override defaults. Retrieval returns at most ten ranked evidence chunks with text, score, citation object, and `insufficient_evidence`; no generated answer. The threshold is a heuristic calibrated against the eight no-answer cases in the evaluation set. Similar out-of-scope questions can still score highly; applications must avoid treating a score as a guarantee of support.

## Evaluation

`evaluation/rag_cases.json` contains 39 expected document-and-section queries (four Arabic) and eight no-answer queries (two Arabic). `app.rag.evaluate` compares the expected document **and section** against raw top-five ranks for Recall@1/3/5 and MRR, independently of threshold, and counts threshold-based negative rejection and positive acceptance. It times query embedding plus Qdrant search on this Mac; model initialization is separate. The same small hand-authored dataset informed the threshold, so the reported numbers are development-set measurements, not blind-test generalization. See `phase-3-checkpoint.md` for actual measurements and limitations.
