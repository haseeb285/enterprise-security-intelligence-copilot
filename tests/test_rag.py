"""Offline behavior tests plus optional live local Qdrant integration."""

import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from reportlab.pdfgen import canvas

from app.core.observability import OperationalMetrics, observability_scope
from app.core.settings import Settings
from app.rag.documents import chunk_document, load_document
from app.rag.service import RagService
from app.rag.store import VectorStore


class FakeEmbedder:
    name = "test-model"
    dimension = 3

    def passages(self, texts):
        return [[1.0, 0.0, 0.0] for _ in texts]

    def query(self, text):
        return [1.0, 0.0, 0.0]


class FakeStore:
    def __init__(self):
        self.points = {}

    def ready(self):
        pass

    def ensure_collection(self):
        pass

    def validate_configuration(self, model, target, overlap):
        pass

    def document_points(self, document_id):
        return [p for p in self.points.values() if p.payload["document_id"] == document_id]

    def upsert(self, chunks, vectors):
        for chunk in chunks:
            self.points[chunk.chunk_id] = SimpleNamespace(
                id=chunk.chunk_id, payload=chunk.payload, score=0.9
            )

    def delete_ids(self, ids):
        for point_id in ids:
            self.points.pop(point_id, None)

    def all_points(self):
        return list(self.points.values())

    def search(self, vector, limit):
        return list(self.points.values())[:limit]


def test_markdown_sections_ids_and_hash(tmp_path):
    path = tmp_path / "policy.md"
    path.write_text("# Policy\n## Access\nMFA required.\n## Backup\nThirty days.")
    document = load_document(path, tmp_path)
    assert [s.title for s in document.sections] == ["Access", "Backup"]
    first = chunk_document(document, model="test-model")
    assert first == chunk_document(document, model="test-model")
    assert first[0].payload["section"] == "Access"
    assert first[0].payload["source"] == f"{tmp_path.name}/policy.md"
    assert first[0].payload["content_hash"] == document.content_hash
    assert first[0].chunk_id != chunk_document(document, target=700, model="test-model")[0].chunk_id
    path.write_text(path.read_text() + "\nNew clause.")
    assert load_document(path, tmp_path).content_hash != document.content_hash


def test_demonstration_label_not_indexed(tmp_path):
    path = tmp_path / "policy.md"
    path.write_text(
        "# Fictional Policy\nSYNTHETIC DEMONSTRATION POLICY\n"
        "NOT AN ACTUAL ORGANIZATION POLICY\n## Rules\nUse MFA."
    )
    chunks = chunk_document(load_document(path, tmp_path), model="test-model")
    assert len(chunks) == 1
    assert chunks[0].payload["section"] == "Rules"


def test_txt_fallback_and_long_chunk(tmp_path):
    path = tmp_path / "a.txt"
    path.write_text("Paragraph. " * 120)
    document = load_document(path, tmp_path)
    chunks = chunk_document(document, 250, 30, "test-model")
    assert len(chunks) > 2
    assert all(c.payload["section"] == "Document" for c in chunks)


def test_pdf_extraction(tmp_path):
    path = tmp_path / "policy.pdf"
    pdf = canvas.Canvas(str(path))
    pdf.drawString(50, 750, "A fictional requirement on page one")
    pdf.showPage()
    pdf.drawString(50, 750, "Another fictional requirement")
    pdf.save()
    doc = load_document(path, tmp_path)
    assert len(doc.sections) == 2
    assert doc.sections[1].page == 2
    assert "fictional" in doc.sections[0].text


@pytest.mark.parametrize(
    "filename,content",
    [("empty.md", b""), ("blank.txt", b"  \n"), ("bad.pdf", b"not a pdf"), ("binary.txt", b"\xff")],
)
def test_invalid_documents(tmp_path, filename, content):
    path = tmp_path / filename
    path.write_bytes(content)
    with pytest.raises(ValueError):
        load_document(path, tmp_path)


def test_unsupported(tmp_path):
    path = tmp_path / "policy.docx"
    path.write_text("Test")
    with pytest.raises(ValueError, match="Unsupported"):
        load_document(path, tmp_path)


def test_unreadable_document(tmp_path, monkeypatch):
    path = tmp_path / "blocked.txt"
    path.write_text("Content")

    def deny_read(self):
        raise PermissionError("permission denied")

    monkeypatch.setattr(Path, "read_bytes", deny_read)
    with pytest.raises(ValueError, match="Cannot read"):
        load_document(path, tmp_path)


def test_ingest_replacement_prune_and_retrieval(tmp_path):
    path = tmp_path / "access.md"
    path.write_text("# Access\n## MFA\nUse security keys for admins.")
    store = FakeStore()
    service = RagService(store, FakeEmbedder(), threshold=0.82)
    one = service.ingest(tmp_path)
    assert (one.discovered, one.ingested, one.chunks) == (1, 1, 1)
    repeat = service.ingest(tmp_path)
    assert (repeat.skipped, repeat.duplicates_avoided, len(store.points)) == (1, 1, 1)
    old_id = next(iter(store.points))
    path.write_text("# Access\n## MFA\nUse two separate security keys for admins.")
    changed = service.ingest(tmp_path)
    assert changed.ingested == 1 and len(store.points) == 1
    assert old_id not in store.points
    result = service.retrieve("keys", 1)
    assert result.evidence[0].citation.label == "Access — MFA"
    assert result.evidence[0].citation.source == f"{tmp_path.name}/access.md"
    assert not result.insufficient_evidence
    service.threshold = 0.95
    assert service.retrieve("keys").insufficient_evidence
    assert service.retrieve("keys").evidence == ()
    for top_k in (0, 11):
        with pytest.raises(ValueError):
            service.retrieve("keys", top_k)
    with pytest.raises(ValueError):
        service.retrieve("  ")
    path.unlink()
    service.ingest(tmp_path, prune=True)
    assert not store.points


def test_retrieval_records_latency_and_insufficient_result(tmp_path):
    path = tmp_path / "policy.md"
    path.write_text("# Policy\n## Rule\nUse security keys.")
    service = RagService(FakeStore(), FakeEmbedder(), threshold=0.95)
    service.ingest(tmp_path)
    registry = OperationalMetrics()
    with observability_scope(registry=registry):
        assert service.retrieve("keys").insufficient_evidence
    snapshot = registry.snapshot()
    assert snapshot["counters"]["retrieval_calls_total"] == 1
    assert snapshot["counters"]["retrieval_insufficient_total"] == 1
    assert snapshot["latency_ms"]["retrieval_latency_ms"]["count"] == 1


def test_settings_constraints():
    with pytest.raises(ValueError):
        Settings(rag_top_k=11)
    with pytest.raises(ValueError):
        Settings(rag_min_score=1.1)


def test_live_qdrant(tmp_path):
    from qdrant_client import QdrantClient

    url = "http://127.0.0.1:6333"
    try:
        QdrantClient(url=url, timeout=2).get_collections()
    except Exception:
        pytest.skip("local Qdrant unavailable")
    collection = f"rag_test_{uuid.uuid4().hex}"
    store = VectorStore(url, collection, 3)
    path = tmp_path / "example.md"
    path.write_text("# Example\n## Guidance\nKeep a fictional security key secure.")
    try:
        service = RagService(store, FakeEmbedder(), threshold=0)
        assert service.ingest(tmp_path).chunks == 1
        assert service.ingest(tmp_path).duplicates_avoided == 1
        assert len(store.document_points(load_document(path, tmp_path).document_id)) == 1
        assert service.retrieve("security key", 1).evidence[0].citation.section == "Guidance"
        with pytest.raises(ValueError, match="new RAG_COLLECTION"):
            store.validate_configuration("another-model", 650, 80)
    finally:
        store.client.delete_collection(collection)
