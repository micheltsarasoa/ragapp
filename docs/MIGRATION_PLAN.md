# Migration Plan: Streamlit Monolith → React/Vite + FastAPI Monorepo

## Context

The current app is a working RAG assistant with **four already-running Docker services**:
- **Streamlit UI** (8501) — upload, ask, document management
- **FastAPI** (8000) — already has `/api/stream_query` and `/api/llm_config` + Inngest handlers
- **Inngest** (8288) — async event queue for ingestion/query observability
- **Qdrant** (6333) — hybrid dense+sparse vector search

The goal is to replace the Streamlit service with a React/Vite frontend, expand the FastAPI surface to cover all UI-driven logic, and reorganize the repo into a clean monorepo. Everything gets Dockerized.

---

## Target Monorepo Structure

```
ragapp/
├── docker-compose.yml               ← updated root orchestration
├── .env.example
├── .gitignore
│
├── apps/
│   ├── backend/                     ← FastAPI service (Python)
│   │   ├── Dockerfile
│   │   ├── requirements.txt         ← streamlit removed; ML deps unchanged
│   │   ├── app/
│   │   │   ├── main.py              ← app factory: creates FastAPI, mounts routers, registers Inngest
│   │   │   ├── core/
│   │   │   │   ├── config.py        ← centralised env-var loading
│   │   │   │   ├── db.py            ← moved from root db.py (unchanged logic)
│   │   │   │   ├── vector_db.py     ← moved from root vector_db.py (unchanged)
│   │   │   │   └── data_loader.py   ← moved from root data_loader.py (unchanged)
│   │   │   ├── models/
│   │   │   │   ├── auth.py          ← IdentityRequest / IdentityResponse schemas
│   │   │   │   ├── documents.py     ← DocumentRecord, UploadResponse, VisibilityUpdate
│   │   │   │   ├── llm.py           ← LLMConfig schema (extracted from root main.py)
│   │   │   │   └── rag.py           ← RAGChunkAndSrc, RAGSearchResult, RAGQueryResult
│   │   │   ├── routes/
│   │   │   │   ├── auth.py          ← POST /api/auth/identity
│   │   │   │   ├── documents.py     ← GET / POST /upload / PATCH /visibility / DELETE
│   │   │   │   ├── query.py         ← GET /api/stream_query (moved, unchanged)
│   │   │   │   └── llm_config.py    ← GET+POST /api/llm_config (moved, unchanged)
│   │   │   └── inngest_functions/
│   │   │       ├── client.py        ← inngest_client singleton (extracted)
│   │   │       ├── ingest_pdf.py    ← rag_ingest_pdf function (from root main.py)
│   │   │       └── query_pdf.py     ← rag_query_pdf_ai function (from root main.py)
│   │   └── data/
│   │       └── .gitkeep             ← runtime mount point for ragapp.db
│   │
│   └── frontend/                    ← React 18 + Vite + TypeScript + Tailwind
│       ├── Dockerfile               ← multi-stage: npm build → nginx:alpine
│       ├── nginx.conf               ← SPA fallback + /api proxy_pass to backend
│       ├── package.json
│       ├── tsconfig.json
│       ├── vite.config.ts           ← dev proxy: /api/* → http://localhost:8000
│       ├── tailwind.config.ts
│       ├── index.html
│       └── src/
│           ├── main.tsx
│           ├── App.tsx              ← React Router route definitions
│           ├── api/
│           │   ├── auth.ts          ← POST /api/auth/identity
│           │   ├── documents.ts     ← CRUD document calls
│           │   ├── query.ts         ← streaming fetch wrapper
│           │   └── llmConfig.ts     ← GET+POST llm_config
│           ├── hooks/
│           │   ├── useIdentity.ts   ← localStorage key → POST /api/auth/identity
│           │   ├── useDocuments.ts  ← list, delete, toggle
│           │   ├── useStreamQuery.ts← NDJSON ReadableStream consumer
│           │   └── useLlmConfig.ts
│           ├── components/
│           │   ├── layout/
│           │   │   ├── AppShell.tsx
│           │   │   ├── Sidebar.tsx  ← key management + nav + LLM preset switcher
│           │   │   └── NavLink.tsx
│           │   ├── upload/
│           │   │   ├── DropZone.tsx
│           │   │   └── VisibilityPicker.tsx
│           │   ├── query/
│           │   │   ├── QueryForm.tsx
│           │   │   ├── AnswerCard.tsx
│           │   │   └── SourceBadge.tsx
│           │   ├── documents/
│           │   │   ├── DocumentCard.tsx
│           │   │   ├── DocumentList.tsx
│           │   │   └── VisibilityBadge.tsx
│           │   └── shared/
│           │       ├── Button.tsx
│           │       ├── Input.tsx
│           │       └── Spinner.tsx
│           ├── pages/
│           │   ├── UploadPage.tsx   ← replaces Upload tab
│           │   ├── AskPage.tsx      ← replaces Ask tab
│           │   ├── DocumentsPage.tsx← replaces pages/1_Manage_Documents.py
│           │   └── SettingsPage.tsx ← replaces sidebar LLM config form
│           └── types/
│               └── api.ts           ← TypeScript interfaces mirroring Pydantic models
│
├── uploads/                         ← shared host volume (backend writes, reads via Inngest)
│   └── .gitkeep
├── qdrant_storage/                  ← existing Qdrant persistence volume
└── docs/                            ← existing docs, updated in place
```

---

## New REST Endpoints (backend expansion)

### `routes/auth.py`
| Method | Path | Replaces |
|--------|------|----------|
| POST | `/api/auth/identity` | `auth.py::resolve_identity()` + `apply_key()` |

Body: `{ access_key?: string }`. Returns `{ user_id, access_key, is_new }`. SHA-256 derivation stays server-side.

### `routes/documents.py`
| Method | Path | Replaces |
|--------|------|----------|
| GET | `/api/documents?user_id=` | `db.list_documents(user_id)` |
| POST | `/api/documents/upload` | `save_uploaded_file()` + `send_ingest_event()` |
| PATCH | `/api/documents/{source_id}/visibility` | `update_source_visibility()` + `db.update_visibility()` |
| DELETE | `/api/documents/{source_id}?user_id=` | `delete_by_source()` + `db.delete_document()` |

**Upload** accepts `multipart/form-data`: `file`, `visibility`, `user_id`. Saves to `/app/uploads/`, fires `rag/ingest_pdf` Inngest event. Returns `{ source_id, status: "queued" }`.

**Mutation ordering preserved**: Qdrant mutation always precedes SQLite write (existing invariant from `1_Manage_Documents.py`).

### Existing routes (moved, no behavioral change)
- `routes/query.py` ← `GET /api/stream_query` (NDJSON streaming)
- `routes/llm_config.py` ← `GET/POST /api/llm_config`

---

## Migration Steps

### Phase 0 — Repo Scaffold ✅

- [x] Create `apps/backend/` and `apps/frontend/` directory trees
- [x] Move all Python backend files into `apps/backend/` (flat layout preserved — imports unchanged)
- [x] Copy React/Vite frontend into `apps/frontend/` (from external repo); rename package to `@ragapp/frontend`
- [x] Set up pnpm workspace (`pnpm-workspace.yaml` + root `package.json`)
- [x] Update `docker-compose.yml` build contexts to `./apps/backend`
- [x] Update `.gitignore` for monorepo (node_modules, pnpm-store, qdrant_storage)
- [x] Restructure `apps/backend/` into `app/core/`, `app/models/`, `app/routes/`, `app/inngest_functions/` layout
- [x] Remove `streamlit` from `apps/backend/requirements.txt` / `pyproject.toml`

### Phase 1 — New Backend Endpoints ✅

- [x] Extract `inngest_client` singleton into `inngest_functions/client.py`
- [x] Implement `routes/auth.py` — `POST /api/auth/identity`
- [x] Implement `routes/documents.py` — all four document endpoints
- [x] Add CORS middleware (`http://localhost:5173` + production origin)
- [x] Smoke-test all endpoints — `smoke_test.py` covers 8 checks (all passing)
- [x] Pin Python to 3.12 via `.python-version` (3.14 crashes Rust ML extensions)
- [x] Fix BM25 sparse encoder startup crash (py_rust_stemmers segfault on Python 3.14)
- [x] Harden upload endpoint: Inngest send failure no longer returns 500
- [x] Add Qdrant health pre-check in smoke test (`[5b]`)
- [x] Write `download_models.py` — one-time model cache pre-download script
- [x] Update `docs/setup.md` and `README.md` for monorepo structure

### Phase 2 — React Frontend Scaffold ✅

- [x] Move `react` and `react-dom` from `peerDependencies` to `dependencies`; run `npm install`
- [x] Configure `vite.config.ts` dev proxy: `/api/*` → `http://localhost:8000`
- [x] Set up React Router v7 in `App.tsx`: layout route (`AppShell`) with `<Outlet>` + routes `/`, `/ask`, `/documents`, `/settings`
- [x] Implement `useIdentity` hook (`localStorage` → `POST /api/auth/identity` → `IdentityContext`)
- [x] Create `src/api/auth.ts` — `postIdentity()` wrapper
- [x] Create `src/context/IdentityContext.tsx` — `IdentityProvider` with `identity`, `loading`, `setAccessKey`
- [x] Wrap `main.tsx` with `IdentityProvider`

### Phase 3 — Feature-by-Feature UI Port ✅

- [x] **AppShell + Sidebar**: access key display/change (wired to `useIdentity`), nav links via `<Link>` (Ask / Upload / Documents / Settings), LLM preset button retained
- [x] **UploadPage**: drag-and-drop + file picker, visibility radio (private/public), success/error feedback → `POST /api/documents/upload`
- [x] **AskPage**: question input, NDJSON streaming with buffered line reader → live token display → source badges on completion
- [x] **DocumentsPage**: `useDocuments` hook → document table with inline visibility toggle and two-click delete confirmation
- [x] **SettingsPage**: `useLlmConfig` hook → editable model / base_url / api_key fields → `POST /api/llm_config`
- [x] API layer: `src/api/documents.ts`, `src/api/query.ts`, `src/api/llmConfig.ts`
- [x] Hooks: `src/hooks/useDocuments.ts`, `src/hooks/useLlmConfig.ts`
- [x] `App.tsx` updated: `/upload` route added, all routes point to real page components
- [x] Build verified: `vite build` passes with 0 errors

### Phase 4 — Docker Compose Replacement ✅

- [x] Write `apps/frontend/Dockerfile` (multi-stage: `node:20` build → `nginx:alpine` serve)
- [x] Write `apps/frontend/nginx.conf` (SPA fallback, `/api/` proxy, `proxy_buffering off` + `X-Accel-Buffering: no` on `/api/stream_query`)
- [x] Update `docker-compose.yml`: replaced `ui` (Streamlit) with `frontend` (nginx, port 80); renamed `api` → `backend`; updated Inngest target URL to `http://backend:8000/api/inngest`
- [ ] `docker compose up --build` — full stack smoke test (pending)

### Phase 5 — Cleanup

- [ ] Delete Streamlit files from `apps/backend/`: `streamlit_app.py`, `pages/`, `styles.py`, `auth.py` (Streamlit-specific), `.streamlit/`
- [ ] Update `docs/architecture.md`

---

## Docker Compose Target Services

| Service | Image | Port | Key change |
|---------|-------|------|------------|
| `qdrant` | `qdrant/qdrant` | 6333 | Unchanged |
| `backend` | `./apps/backend` | 8000 | Renamed from `api`; CORS added |
| `inngest` | `node:20-slim` (npx) | 8288 | Target URL updated to `backend` |
| `frontend` | `./apps/frontend` (nginx) | **80** | Replaces `ui` (Streamlit, 8501) |

Only `backend` mounts `./uploads` and `app_data` volumes. `frontend` has no volume mounts.

---

## Architectural Risks & Decisions

| Risk | Decision |
|------|----------|
| **Nginx buffers NDJSON stream** | Add `proxy_buffering off` + `X-Accel-Buffering: no` on `/api/stream_query` location |
| **`VITE_*` vars baked at build time** | Use relative `/api/` paths everywhere; let nginx proxy resolve backend — no per-env rebuilds |
| **`source_id` collision across users** | Prefix `source_id` with `user_id` in `POST /api/documents/upload` to prevent cross-user overwrites |
| **`user_id` sent as plain query param** | Accepted for current threat model (matches Streamlit behavior); document as known limitation |
| **Qdrant-first mutation ordering** | Preserve explicitly in `routes/documents.py`; document the partial-failure risk |
| **`uploads/` path resolution** | Route handler must normalize to container-internal `UPLOAD_DIR` path before firing Inngest event |
| **Python 3.14 / Rust extension crashes** | Pin venv to Python 3.12 via `.python-version`; `py_rust_stemmers` and other pyo3 extensions are stable on 3.12 |

---

## Verification

1. **Backend only**: `cd apps\backend && uv run uvicorn app.main:app` → `uv run python smoke_test.py` (all 8 checks green)
2. **Frontend only**: `pnpm dev:frontend` from repo root → verify proxy, all pages render, streaming works
3. **Full stack**: `docker compose up --build` → upload a PDF → check Inngest dashboard (8288) for successful `rag_ingest_pdf` run → ask a question → verify streaming tokens → manage documents page → delete doc
4. **Access key round-trip**: clear localStorage → reload → verify new key generated → copy key → open new tab → restore key → verify same documents visible
