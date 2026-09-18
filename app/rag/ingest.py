"""CLI: python -m app.rag.ingest data/policies/synthetic [--prune]."""

import argparse
import time
from pathlib import Path

from app.core.settings import get_settings
from app.rag.embeddings import get_embedder
from app.rag.service import RagService
from app.rag.store import VectorStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Index local policies into Qdrant")
    parser.add_argument("directory", type=Path)
    parser.add_argument(
        "--prune", action="store_true", help="Remove deleted documents in this corpus"
    )
    args = parser.parse_args()
    settings = get_settings()
    start = time.perf_counter()
    embedder = get_embedder(settings.embedding_model)
    load_seconds = time.perf_counter() - start
    store = VectorStore(str(settings.qdrant_url), settings.rag_collection, embedder.dimension)
    service = RagService(
        store,
        embedder,
        settings.rag_chunk_target_chars,
        settings.rag_chunk_overlap_chars,
        settings.rag_min_score,
    )
    stats = service.ingest(args.directory, args.prune)
    print(
        f"model_init_s={load_seconds:.3f} "
        f"ingestion_s={time.perf_counter() - start - load_seconds:.3f} "
        f"discovered={stats.discovered} ingested={stats.ingested} skipped={stats.skipped} "
        f"chunks_created={stats.chunks} duplicates_avoided={stats.duplicates_avoided} "
        f"failures={stats.failures}"
    )
    if stats.failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
