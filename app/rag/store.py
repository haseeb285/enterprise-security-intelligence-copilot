"""Qdrant boundary: collection management, scoped document replacement, vector queries."""

from qdrant_client import QdrantClient, models


class VectorStore:
    def __init__(
        self, url: str, collection: str, dimension: int, client: QdrantClient | None = None
    ):
        self.client = client or QdrantClient(url=url, timeout=15)
        self.collection = collection
        self.dimension = dimension

    def ready(self) -> None:
        self.client.get_collections()

    def ensure_collection(self) -> None:
        collections = {item.name for item in self.client.get_collections().collections}
        if self.collection not in collections:
            self.client.create_collection(
                self.collection,
                vectors_config=models.VectorParams(
                    size=self.dimension, distance=models.Distance.COSINE
                ),
            )
        elif (
            self.client.get_collection(self.collection).config.params.vectors.size != self.dimension
        ):
            raise ValueError("Embedding dimension changed; configure a new RAG_COLLECTION")

    def document_points(self, document_id: str) -> list:
        points = []
        offset = None
        while True:
            batch, offset = self.client.scroll(
                self.collection,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id", match=models.MatchValue(value=document_id)
                        )
                    ]
                ),
                limit=256,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            points.extend(batch)
            if offset is None:
                return points

    def upsert(self, chunks: list, vectors: list[list[float]]) -> None:
        self.client.upsert(
            self.collection,
            points=[
                models.PointStruct(id=chunk.chunk_id, vector=vector, payload=chunk.payload)
                for chunk, vector in zip(chunks, vectors, strict=True)
            ],
            wait=True,
        )

    def delete_ids(self, ids: list[str]) -> None:
        if ids:
            self.client.delete(
                self.collection, points_selector=models.PointIdsList(points=ids), wait=True
            )

    def search(self, vector: list[float], limit: int) -> list:
        return self.client.query_points(
            self.collection, query=vector, limit=limit, with_payload=True
        ).points

    def all_points(self) -> list:
        points = []
        offset = None
        while True:
            batch, offset = self.client.scroll(
                self.collection, limit=256, offset=offset, with_payload=True, with_vectors=False
            )
            points.extend(batch)
            if offset is None:
                return points

    def validate_configuration(self, model: str, target: int, overlap: int) -> None:
        points, _ = self.client.scroll(
            self.collection, limit=1, with_payload=True, with_vectors=False
        )
        if points and any(
            (
                points[0].payload.get("embedding_model") != model,
                points[0].payload.get("target_chars") != target,
                points[0].payload.get("overlap_chars") != overlap,
            )
        ):
            raise ValueError(
                "Collection uses another embedding/chunk configuration; "
                "configure a new RAG_COLLECTION"
            )
