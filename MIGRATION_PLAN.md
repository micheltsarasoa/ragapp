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

### Phase 0 — Repo Scaffold (no functional change)
1. Create `apps/backend/` and `apps/frontend/` directory trees
2. Copy existing Python files into `apps/backend/app/` per the target layout — **do not delete originals yet**
3. Create new `apps/backend/app/main.py` as app factory; verify all existing endpoints respond identically via `uvicorn`
4. Update `apps/backend/requirements.txt`: remove `streamlit`; keep all ML/embedding deps

### Phase 1 — New Backend Endpoints
5. Extract `inngest_client` singleton into `inngest_functions/client.py` (resolves circular import risk)
6. Implement `routes/auth.py` — `POST /api/auth/identity`
7. Implement `routes/documents.py` — all four document endpoints, wired to existing `core/db.py` and `core/vector_db.py`
8. Add CORS middleware in `main.py` allowing `http://localhost:5173` (Vite dev) and production origin
9. Smoke-test all new endpoints with curl/httpie against the running backend

### Phase 2 — React Frontend Scaffold
10. `npm create vite@latest apps/frontend -- --template react-ts`
11. Install: `tailwindcss`, `react-router-dom`, `@types/react`
12. Configure `vite.config.ts` dev proxy: `/api/*` → `http://localhost:8000`
13. Set up React Router in `App.tsx`: `/`, `/ask`, `/documents`, `/settings`
14. Implement `useIdentity` hook: reads `localStorage`, calls `POST /api/auth/identity` on first load, exposes `user_id` and `access_key` via React context

### Phase 3 — Feature-by-Feature UI Port
15. **AppShell + Sidebar**: access key display/change, nav links, LLM preset switcher
16. **UploadPage**: `DropZone` + `VisibilityPicker` → `POST /api/documents/upload`
17. **AskPage**: `QueryForm` + `useStreamQuery` consuming NDJSON stream → `AnswerCard` + `SourceBadge` list
18. **DocumentsPage**: `useDocuments` → `DocumentList` with per-card visibility toggle and two-click delete
19. **SettingsPage**: `useLlmConfig` → provider preset form → `POST /api/llm_config`

### Phase 4 — Docker Compose Replacement
20. Write `apps/frontend/Dockerfile`: stage 1 `node:20` runs `npm run build`, stage 2 `nginx:alpine` copies `dist/`
21. Write `apps/frontend/nginx.conf`: SPA fallback (`try_files`), `/api/` proxy to `backend:8000`, **`proxy_buffering off`** on the `/api/stream_query` location (critical for NDJSON streaming)
22. Update root `docker-compose.yml`: replace `ui` service with `frontend` (nginx, port 80); rename `api` → `backend`; update Inngest `command` target URL to `http://backend:8000/api/inngest`
23. `docker compose up --build` — full stack smoke test

### Phase 5 — Cleanup
24. Delete root-level Streamlit files: `streamlit_app.py`, `pages/`, `styles.py`, `auth.py`, `.streamlit/`
25. Delete old root-level flat Python files (now living under `apps/backend/`)
26. Update `docs/architecture.md`, `docs/setup.md`, `README.md`

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

## Critical Files to Modify

| File | Action |
|------|--------|
| `main.py` | Source for all route logic and Inngest registration to split up |
| `db.py` | Move to `core/db.py`; drives the 4 document endpoints + auth |
| `pages/1_Manage_Documents.py` | Source of truth for list/toggle/delete flows → `DocumentsPage.tsx` |
| `auth.py` | SHA-256 derivation → `routes/auth.py` (server-side) + `useIdentity.ts` (client) |
| `docker-compose.yml` | Full replacement; service names, volumes, Inngest command all change |

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

---

## Verification

1. **Backend only**: `uvicorn apps.backend.app.main:app --reload` → hit all endpoints via curl
2. **Frontend only**: `npm run dev` in `apps/frontend` → verify proxy, all pages render, streaming works
3. **Full stack**: `docker compose up --build` → upload a PDF → check Inngest dashboard (8288) for successful `rag_ingest_pdf` run → ask a question → verify streaming tokens → manage documents page → delete doc
4. **Access key round-trip**: clear localStorage → reload → verify new key generated → copy key → open new tab → restore key → verify same documents visible
