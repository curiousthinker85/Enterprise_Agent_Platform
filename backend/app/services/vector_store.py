from typing import Any

from app.core.config import get_settings

COLLECTION_NAME = "document_chunks"


class VectorStore:
    """Persistent ChromaDB store for extracted document chunks."""

    def __init__(self, storage_path: str | None = None) -> None:
        import chromadb

        self.client = chromadb.PersistentClient(path=storage_path or get_settings().vector_storage_path)
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert_chunks(self, chunks: list[Any], document_filename: str, embeddings: list[list[float]]) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("Each document chunk must have one embedding")
        self.collection.upsert(
            ids=[str(chunk.id) for chunk in chunks],
            embeddings=embeddings,
            documents=[chunk.content for chunk in chunks],
            metadatas=[
                {
                    "workspace_id": chunk.workspace_id,
                    "document_id": chunk.document_id,
                    "chunk_id": chunk.id,
                    "chunk_index": chunk.chunk_index,
                    "document_filename": document_filename,
                    "char_count": chunk.char_count,
                }
                for chunk in chunks
            ],
        )

    def search(
        self,
        query_embedding: list[float],
        workspace_id: int,
        top_k: int,
        document_id: int | None = None,
        document_ids: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        if document_id is not None and document_ids is not None:
            raise ValueError("Provide document_id or document_ids, not both")
        where: dict[str, Any] = {"workspace_id": workspace_id}
        if document_id is not None:
            where = {"$and": [{"workspace_id": workspace_id}, {"document_id": document_id}]}
        elif document_ids:
            where = {"$and": [{"workspace_id": workspace_id}, {"document_id": {"$in": document_ids}}]}
        response = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        documents = response.get("documents", [[]])[0] or []
        metadata = response.get("metadatas", [[]])[0] or []
        distances = response.get("distances", [[]])[0] or []
        return [
            {
                "document_id": item_metadata["document_id"],
                "workspace_id": item_metadata["workspace_id"],
                "document_filename": item_metadata["document_filename"],
                "chunk_index": item_metadata["chunk_index"],
                "content": content,
                "score": 1 - float(distance),
            }
            for content, item_metadata, distance in zip(documents, metadata, distances)
        ]


_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
