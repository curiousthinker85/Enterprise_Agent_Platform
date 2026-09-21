from collections.abc import Sequence

MODEL_NAME = "BAAI/bge-small-en-v1.5"


class EmbeddingService:
    """Local FastEmbed encoder, loaded only when an embedding is requested."""

    def __init__(self) -> None:
        self._model = None

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self._model is None:
            from fastembed import TextEmbedding

            self._model = TextEmbedding(model_name=MODEL_NAME)
        vectors: Sequence = list(self._model.embed(texts))
        return [[float(value) for value in vector] for vector in vectors]


_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Convenience function required by the embedding service contract."""
    return get_embedding_service().embed_texts(texts)
