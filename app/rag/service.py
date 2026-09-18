"""Idempotent ingestion and evidence-only retrieval, independent of future agents."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.rag.documents import SUPPORTED, chunk_document, load_document


@dataclass(frozen=True)
class Citation:
    document: str
    source: str
    section: str
    page: int | None

    @property
    def label(self) -> str:
        page = f" — Page {self.page}" if self.page is not None else ""
        return f"{self.document}{page} — {self.section}"


@dataclass(frozen=True)
class Evidence:
    text: str
    score: float
    chunk_id: str
    citation: Citation


@dataclass(frozen=True)
class Retrieval:
    evidence: tuple[Evidence, ...]
    insufficient_evidence: bool


@dataclass
class IngestStats:
    discovered: int = 0
    ingested: int = 0
    skipped: int = 0
    chunks: int = 0
    duplicates_avoided: int = 0
    failures: int = 0


class RagService:
    def __init__(
        self, store, embedder, target: int = 650, overlap: int = 80, threshold: float = 0.805
    ):
        self.store = store
        self.embedder = embedder
        self.target = target
        self.overlap = overlap
        self.threshold = threshold

    def ingest(self, root: Path, prune: bool = False) -> IngestStats:
        if not root.is_dir():
            raise ValueError(f"Not a directory: {root}")
        self.store.ready()
        self.store.ensure_collection()
        self.store.validate_configuration(self.embedder.name, self.target, self.overlap)
        stats = IngestStats()
        paths = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED)
        stats.discovered = len(paths)
        seen: set[str] = set()
        for path in paths:
            try:
                document = load_document(path, root)
                seen.add(document.document_id)
                chunks = chunk_document(document, self.target, self.overlap, self.embedder.name)
                old = self.store.document_points(document.document_id)
                desired = {chunk.chunk_id for chunk in chunks}
                existing = {str(point.id) for point in old}
                if desired == existing:
                    stats.skipped += 1
                    stats.duplicates_avoided += len(existing)
                    continue
                timestamp = datetime.now(UTC).isoformat()
                new = [chunk for chunk in chunks if chunk.chunk_id not in existing]
                if new:
                    for chunk in new:
                        chunk.payload["ingestion_timestamp"] = timestamp
                        chunk.payload["corpus"] = root.name
                    self.store.upsert(new, self.embedder.passages([chunk.text for chunk in new]))
                self.store.delete_ids(list(existing - desired))
                stats.ingested += 1
                stats.chunks += len(new)
                stats.duplicates_avoided += len(existing & desired)
            except Exception as exc:
                stats.failures += 1
                print(f"Failed {path.relative_to(root)}: {type(exc).__name__}: {exc}")
        if prune and not stats.failures:
            # Explicit deletion only within this corpus, never other private/public corpora.
            stale = [
                str(point.id)
                for point in self.store.all_points()
                if point.payload.get("corpus") == root.name
                and point.payload.get("document_id") not in seen
            ]
            self.store.delete_ids(stale)
        return stats

    def retrieve(self, query: str, top_k: int = 5) -> Retrieval:
        if not query.strip() or len(query) > 4000:
            raise ValueError("Query must have 1–4000 characters")
        if not 1 <= top_k <= 10:
            raise ValueError("top_k must be between 1 and 10")
        self.store.ready()
        self.store.validate_configuration(self.embedder.name, self.target, self.overlap)
        points = self.store.search(self.embedder.query(query), top_k)
        evidence = tuple(
            Evidence(
                text=point.payload["text"],
                score=point.score,
                chunk_id=point.payload["chunk_id"],
                citation=Citation(
                    point.payload["document_name"],
                    point.payload["source"],
                    point.payload["section"],
                    point.payload.get("page"),
                ),
            )
            for point in points
            if point.score >= self.threshold
        )
        return Retrieval(evidence, not bool(evidence))
