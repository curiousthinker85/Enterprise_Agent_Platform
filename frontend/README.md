# Enterprise AI Agent Portal — Frontend

React + Vite UI for the FastAPI backend in `../backend`.

## Prerequisites
- Node.js 18+ installed

## Setup (first time only)
```bash
cd frontend
npm install
```

## Run (two terminals)

Terminal 1 — start the backend:
```bash
cd backend
.venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload   # Windows
# .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload     # macOS/Linux
```

Terminal 2 — start the frontend:
```bash
cd frontend
npm run dev
```

Open **http://localhost:3000** — create an account, then use the portal.

The Vite dev server proxies `/api` requests to `http://localhost:8000`, so no CORS setup is needed.

## Features
- Register / Login (JWT stored in localStorage)
- Workspaces dashboard: create, browse, health + model status
- Workspace detail: upload → process → index documents, semantic search, RAG "Ask" with citations, member management
- Direct LLM chat page with model connection test
- Audit log viewer with workspace filter

## Production build
```bash
npm run build   # output in dist/
```
