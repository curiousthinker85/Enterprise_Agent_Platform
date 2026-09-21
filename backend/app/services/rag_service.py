from app.schemas.chat import ChatMessage, ChatRequest
from app.schemas.rag import AskResponse, Citation
from app.services.embedding_service import EmbeddingService
from app.services.llm_gateway import LLMGateway
from app.services.vector_store import VectorStore

NOT_FOUND_ANSWER = "Information not found in the provided documents."


class RAGService:
    """Retrieval-only-grounded question answering over one workspace."""

    def __init__(self, embeddings: EmbeddingService, vector_store: VectorStore, gateway: LLMGateway) -> None:
        self.embeddings = embeddings
        self.vector_store = vector_store
        self.gateway = gateway

    async def ask(self, workspace_id: int, question: str, top_k: int, document_ids: list[int]) -> AskResponse:
        query_embedding = self.embeddings.embed_texts([question])[0]
        results = self.vector_store.search(
            query_embedding,
            workspace_id=workspace_id,
            top_k=top_k,
            document_ids=document_ids or None,
        )
        # Defense in depth: the store filter is mandatory, and results are checked
        # again before being placed in the LLM prompt or returned to the caller.
        results = [item for item in results if item.get("workspace_id") == workspace_id]
        if document_ids:
            permitted = set(document_ids)
            results = [item for item in results if item["document_id"] in permitted]

        citations = [
            Citation(
                citation_index=index,
                document_id=result["document_id"],
                document_filename=result["document_filename"],
                chunk_index=result["chunk_index"],
                content=result["content"],
                score=result["score"],
            )
            for index, result in enumerate(results, start=1)
        ]
        if not citations:
            return AskResponse(
                workspace_id=workspace_id,
                question=question,
                answer=NOT_FOUND_ANSWER,
                model=None,
                citations=[],
                usage=None,
            )

        context = "\n\n".join(
            f"[{citation.citation_index}] Document: {citation.document_filename}, "
            f"Chunk: {citation.chunk_index}\n{citation.content}"
            for citation in citations
        )
        system_prompt = f"""You are an enterprise document assistant for HR and Finance teams.
Answer only using the provided context.
If the answer is not present in the context, say: \"{NOT_FOUND_ANSWER}\"
Do not invent facts.
Cite sources using [1], [2], [3].
Keep answers concise and factual.

Context:
{context}"""
        response = await self.gateway.chat(
            ChatRequest(
                messages=[
                    ChatMessage(role="system", content=system_prompt),
                    ChatMessage(role="user", content=question),
                ]
            )
        )
        return AskResponse(
            workspace_id=workspace_id,
            question=question,
            answer=response.content,
            model=response.model,
            citations=citations,
            usage=response.usage,
        )
