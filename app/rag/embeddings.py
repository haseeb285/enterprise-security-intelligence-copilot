"""One cached local multilingual embedding model; E5 requires asymmetric prefixes."""

from functools import lru_cache


class LocalEmbedder:
    def __init__(self, name: str = "intfloat/multilingual-e5-small") -> None:
        from sentence_transformers import SentenceTransformer

        self.name = name
        self.model = SentenceTransformer(name, device="cpu")
        self.dimension = self.model.get_embedding_dimension()

    def passages(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(
            [f"passage: {text}" for text in texts],
            normalize_embeddings=True,
            show_progress_bar=False,
        ).tolist()

    def query(self, text: str) -> list[float]:
        return self.model.encode(
            f"query: {text}", normalize_embeddings=True, show_progress_bar=False
        ).tolist()


@lru_cache(maxsize=2)
def get_embedder(name: str) -> LocalEmbedder:
    return LocalEmbedder(name)
