from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.database import Base, get_db
from app.main import app
import app.models as orm_models  # noqa: F401 - registers ORM models before create_all
from app.services.embedding_service import get_embedding_service
from app.services.llm_gateway import get_gateway
from app.services.vector_store import get_vector_store
from app.schemas.chat import ChatResponse, Usage


@pytest.fixture
def client(tmp_path) -> Generator[TestClient, None, None]:
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    test_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db() -> Generator[Session, None, None]:
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    settings = get_settings()
    original_storage_path = settings.upload_storage_path
    settings.upload_storage_path = str(tmp_path / "uploads")
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        register_response = test_client.post(
            "/api/v1/auth/register",
            json={"email": "owner@example.com", "password": "password123", "full_name": "Workspace Owner"},
        )
        assert register_response.status_code == 201
        login_response = test_client.post(
            "/api/v1/auth/login",
            json={"email": "owner@example.com", "password": "password123"},
        )
        assert login_response.status_code == 200
        test_client.headers.update({"Authorization": f"Bearer {login_response.json()['access_token']}"})
        yield test_client
    app.dependency_overrides.clear()
    settings.upload_storage_path = original_storage_path
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


class FakeEmbeddingService:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text)), 1.0] for text in texts]


class FakeVectorStore:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def upsert_chunks(self, chunks, document_filename: str, embeddings) -> None:
        for chunk, embedding in zip(chunks, embeddings):
            self.items = [item for item in self.items if item["chunk_id"] != chunk.id]
            self.items.append(
                {
                    "workspace_id": chunk.workspace_id,
                    "document_id": chunk.document_id,
                    "chunk_id": chunk.id,
                    "document_filename": document_filename,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "embedding": embedding,
                }
            )

    def search(self, query_embedding, workspace_id: int, top_k: int, document_id: int | None = None, document_ids: list[int] | None = None):
        return [
            {
                "workspace_id": item["workspace_id"],
                "document_id": item["document_id"],
                "document_filename": item["document_filename"],
                "chunk_index": item["chunk_index"],
                "content": item["content"],
                "score": 0.9,
            }
            for item in self.items
            if item["workspace_id"] == workspace_id
            and (document_id is None or item["document_id"] == document_id)
            and (not document_ids or item["document_id"] in document_ids)
        ][:top_k]


@pytest.fixture
def vector_services(client: TestClient) -> Generator[FakeVectorStore, None, None]:
    vector_store = FakeVectorStore()
    app.dependency_overrides[get_embedding_service] = lambda: FakeEmbeddingService()
    app.dependency_overrides[get_vector_store] = lambda: vector_store
    yield vector_store
    app.dependency_overrides.pop(get_embedding_service, None)
    app.dependency_overrides.pop(get_vector_store, None)


class FakeLLMGateway:
    async def chat(self, request) -> ChatResponse:
        return ChatResponse(
            model="fake-rag-model",
            content="The candidate previously worked at ABC Ltd [1].",
            usage=Usage(prompt_tokens=10, completion_tokens=8, total_tokens=18),
            provider="fake",
        )


@pytest.fixture
def rag_services(vector_services: FakeVectorStore) -> Generator[FakeVectorStore, None, None]:
    app.dependency_overrides[get_gateway] = lambda: FakeLLMGateway()
    yield vector_services
    app.dependency_overrides.pop(get_gateway, None)


def create_workspace(client: TestClient) -> int:
    response = client.post("/api/v1/workspaces", json={"name": "HR Onboarding", "workspace_type": "HR"})
    assert response.status_code == 201
    return response.json()["id"]


def test_create_workspace(client: TestClient) -> None:
    workspace_id = create_workspace(client)
    response = client.get(f"/api/v1/workspaces/{workspace_id}")
    assert response.status_code == 200
    assert response.json()["workspace_type"] == "HR"


def test_list_workspaces(client: TestClient) -> None:
    create_workspace(client)
    response = client.get("/api/v1/workspaces")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_upload_document(client: TestClient) -> None:
    workspace_id = create_workspace(client)
    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/documents",
        files={"file": ("candidate.txt", b"Employment verified", "text/plain")},
    )
    assert response.status_code == 201
    document = response.json()
    assert document["original_filename"] == "candidate.txt"
    assert document["size_bytes"] == 19
    assert document["status"] == "uploaded"


def test_list_documents(client: TestClient) -> None:
    workspace_id = create_workspace(client)
    client.post(
        f"/api/v1/workspaces/{workspace_id}/documents",
        files={"file": ("audit.csv", b"invoice,total\nA-1,25\n", "text/csv")},
    )
    response = client.get(f"/api/v1/workspaces/{workspace_id}/documents")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["original_filename"] == "audit.csv"


def upload_document(client: TestClient, filename: str, content: bytes) -> int:
    workspace_id = create_workspace(client)
    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/documents",
        files={"file": (filename, content, "text/plain")},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_process_txt_document(client: TestClient) -> None:
    document_id = upload_document(client, "notes.txt", b"Candidate employment dates were verified.")
    response = client.post(f"/api/v1/documents/{document_id}/process")
    assert response.status_code == 200
    assert response.json()["status"] == "processed"
    assert response.json()["chunk_count"] == 1


def test_process_document_chunks_created(client: TestClient) -> None:
    document_id = upload_document(client, "long.txt", b"A" * 1500)
    process_response = client.post(f"/api/v1/documents/{document_id}/process")
    assert process_response.status_code == 200
    assert process_response.json()["chunk_count"] == 2
    chunks_response = client.get(f"/api/v1/documents/{document_id}/chunks")
    assert chunks_response.status_code == 200
    assert chunks_response.json()["total_chunks"] == 2
    assert [chunk["chunk_index"] for chunk in chunks_response.json()["chunks"]] == [0, 1]
    assert chunks_response.json()["chunks"][0]["char_count"] == 1000
    assert chunks_response.json()["chunks"][1]["char_count"] == 600


def test_unknown_document_returns_404(client: TestClient) -> None:
    response = client.post("/api/v1/documents/999999/process")
    assert response.status_code == 404


def test_unsupported_file_status_failed(client: TestClient) -> None:
    document_id = upload_document(client, "malware.exe", b"not an executable")
    response = client.post(f"/api/v1/documents/{document_id}/process")
    assert response.status_code == 422
    assert "Unsupported file type" in response.json()["detail"]
    document_response = client.get(f"/api/v1/documents/{document_id}")
    assert document_response.json()["status"] == "failed"


def test_index_requires_processed_document(client: TestClient, vector_services: FakeVectorStore) -> None:
    document_id = upload_document(client, "unprocessed.txt", b"Not processed yet")
    response = client.post(f"/api/v1/documents/{document_id}/index")
    assert response.status_code == 409
    assert "must be processed" in response.json()["detail"]


def test_index_updates_status(client: TestClient, vector_services: FakeVectorStore) -> None:
    document_id = upload_document(client, "indexed.txt", b"Background check completed")
    assert client.post(f"/api/v1/documents/{document_id}/process").status_code == 200
    response = client.post(f"/api/v1/documents/{document_id}/index")
    assert response.status_code == 200
    assert response.json()["status"] == "indexed"
    assert response.json()["chunks_indexed"] == 1


def test_search_returns_empty_for_unknown_workspace(client: TestClient, vector_services: FakeVectorStore) -> None:
    response = client.get("/api/v1/workspaces/999999/search", params={"q": "background check"})
    assert response.status_code == 200
    assert response.json()["results"] == []


def test_search_filters_by_workspace(client: TestClient, vector_services: FakeVectorStore) -> None:
    first_document_id = upload_document(client, "hr.txt", b"First workspace background check")
    assert client.post(f"/api/v1/documents/{first_document_id}/process").status_code == 200
    assert client.post(f"/api/v1/documents/{first_document_id}/index").status_code == 200

    second_workspace_id = create_workspace(client)
    second_upload = client.post(
        f"/api/v1/workspaces/{second_workspace_id}/documents",
        files={"file": ("finance.txt", b"Second workspace invoice", "text/plain")},
    )
    second_document_id = second_upload.json()["id"]
    assert client.post(f"/api/v1/documents/{second_document_id}/process").status_code == 200
    assert client.post(f"/api/v1/documents/{second_document_id}/index").status_code == 200

    first_workspace_id = client.get(f"/api/v1/documents/{first_document_id}").json()["workspace_id"]
    response = client.get(f"/api/v1/workspaces/{first_workspace_id}/search", params={"q": "background"})
    assert response.status_code == 200
    assert [result["document_id"] for result in response.json()["results"]] == [first_document_id]


def test_ask_returns_citations(client: TestClient, rag_services: FakeVectorStore) -> None:
    document_id = upload_document(client, "resume.txt", b"Employment history: ABC Ltd, 2020 to 2024.")
    assert client.post(f"/api/v1/documents/{document_id}/process").status_code == 200
    assert client.post(f"/api/v1/documents/{document_id}/index").status_code == 200
    workspace_id = client.get(f"/api/v1/documents/{document_id}").json()["workspace_id"]
    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/ask",
        json={"question": "What is the candidate's previous company?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "The candidate previously worked at ABC Ltd [1]."
    assert data["model"] == "fake-rag-model"
    assert data["citations"][0]["document_id"] == document_id
    assert data["citations"][0]["document_filename"] == "resume.txt"
    assert data["usage"]["total_tokens"] == 18


def test_ask_returns_not_found_when_no_chunks(client: TestClient, rag_services: FakeVectorStore) -> None:
    workspace_id = create_workspace(client)
    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/ask",
        json={"question": "What is the candidate's previous company?"},
    )
    assert response.status_code == 200
    assert response.json()["answer"] == "Information not found in the provided documents."
    assert response.json()["citations"] == []
    assert response.json()["model"] is None


def test_ask_unknown_workspace_returns_404(client: TestClient, rag_services: FakeVectorStore) -> None:
    response = client.post(
        "/api/v1/workspaces/999999/ask",
        json={"question": "What is the candidate's previous company?"},
    )
    assert response.status_code == 404


def test_register_user(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "hr@example.com", "password": "password123", "full_name": "HR User"},
    )
    assert response.status_code == 201
    assert response.json()["email"] == "hr@example.com"


def test_login_user(client: TestClient) -> None:
    response = client.post("/api/v1/auth/login", json={"email": "owner@example.com", "password": "password123"})
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_access_me_without_token_returns_401(client: TestClient) -> None:
    authorization = client.headers.pop("Authorization")
    response = client.get("/api/v1/auth/me")
    client.headers["Authorization"] = authorization
    assert response.status_code == 401


def test_create_workspace_requires_auth(client: TestClient) -> None:
    authorization = client.headers.pop("Authorization")
    response = client.post("/api/v1/workspaces", json={"name": "No Access", "workspace_type": "HR"})
    client.headers["Authorization"] = authorization
    assert response.status_code == 401


def test_workspace_creator_becomes_admin(client: TestClient) -> None:
    workspace_id = create_workspace(client)
    response = client.get(f"/api/v1/workspaces/{workspace_id}/members")
    assert response.status_code == 200
    assert response.json()[0]["role"] == "ADMIN"
    assert response.json()[0]["email"] == "owner@example.com"


def test_non_member_cannot_access_workspace(client: TestClient) -> None:
    workspace_id = create_workspace(client)
    client.post(
        "/api/v1/auth/register",
        json={"email": "outsider@example.com", "password": "password123", "full_name": "Outsider"},
    )
    login_response = client.post("/api/v1/auth/login", json={"email": "outsider@example.com", "password": "password123"})
    response = client.get(
        f"/api/v1/workspaces/{workspace_id}",
        headers={"Authorization": f"Bearer {login_response.json()['access_token']}"},
    )
    assert response.status_code == 403


def test_audit_log_created_on_workspace_create(client: TestClient) -> None:
    workspace_id = create_workspace(client)
    response = client.get("/api/v1/audit-logs", params={"workspace_id": workspace_id, "action": "workspace.create"})
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["action"] == "workspace.create"
