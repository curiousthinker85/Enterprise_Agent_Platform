# Enterprise Agent Platform

Initial BYOM (bring your own model) gateway for a secure HR and finance document-intelligence platform.

## Run locally

In PowerShell:

```powershell
cd backend
Copy-Item .env.example .env
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

Set an OpenAI-compatible API key or configure an Ollama model in `.env` before calling the model endpoints. The health endpoint does not require a model.

Open API documentation at `http://localhost:8000/docs`.

## Verify

```powershell
cd backend
.\.venv\Scripts\python -m pytest
```

Endpoints:

- `GET /api/v1/health`
- `GET /api/v1/models/config` — never returns the API key
- `POST /api/v1/models/test`
- `POST /api/v1/models/chat`
- `POST`, `GET /api/v1/workspaces`
- `GET /api/v1/workspaces/{workspace_id}`
- `POST`, `GET /api/v1/workspaces/{workspace_id}/documents`
- `GET /api/v1/documents/{document_id}`

## Storage (Step 2)

SQLite metadata is stored in `app.db`. Uploads are compartmentalized under
`storage/uploads/{workspace_id}/{document_id}/{original_filename}`. Tables are
created automatically when the application starts.

## Text extraction (Step 3)

Supported uploads can be processed explicitly with `POST /api/v1/documents/{document_id}/process`:
`.pdf`, `.docx`, `.txt`, `.md`, and `.csv`. Extracted text is stored in
overlapping 1,000-character chunks in SQLite and is available from
`GET /api/v1/documents/{document_id}/chunks`.

## Grounded answers (Step 5)

`POST /api/v1/workspaces/{workspace_id}/ask` retrieves workspace-scoped chunks,
sends only those chunks to the configured model, and returns a concise answer
with numbered citations. It returns `Information not found in the provided documents.`
without calling the model when retrieval has no results.
