# Data Flow Diagram — RAG Monorepo

> Covers: ingestion, query/RAG, document management, auth, LLM config, and the proposed **folder classification** feature (`🆕`).

```mermaid
flowchart TD
    USER([👤 User])
    LLM_API([🤖 LLM Provider\nGroq · Ollama · Custom\nOpenAI-compatible])

    %% ─────────────────────────────────────────
    subgraph FE ["🖥️  Frontend — React / Vite / Nginx  :80"]
        FE_AUTH["useIdentity\nlocalStorage → access_key · user_id"]
        FE_UP["UploadPage\nDropZone · VisibilityPicker\n🆕 FolderPicker"]
        FE_ASK["AskPage\nQueryForm · useStreamQuery\nAnswerCard · SourceBadge"]
        FE_DOCS["DocumentsPage\nDocumentList\n🆕 FolderSidebar"]
        FE_SET["SettingsPage\nLLM Provider Form"]
    end

    %% ─────────────────────────────────────────
    subgraph BE ["⚙️  Backend — FastAPI / Uvicorn  :8000"]

        R_AUTH["POST /api/auth/identity"]
        R_UP["POST /api/documents/upload\nmultipart: file · visibility · user_id\n🆕 folder_id"]
        R_DOCS["GET  /api/documents\nPATCH  /{id}/visibility\nDELETE /{id}"]
        R_FOLD["🆕  GET  /api/folders\n🆕  POST /api/folders"]
        R_QRY["GET /api/stream_query\n?question · ?top_k · ?user_id\n🆕 ?folder_id"]
        R_LLM["GET · POST /api/llm_config"]

        subgraph RAG ["RAG Core"]
            CHUNK["load_and_chunk\nSentenceSplitter\n1 000 chars · 200 overlap"]
            EMB_D["embed_dense\nBAAI/bge-small-en-v1.5\n384-dim"]
            EMB_S["embed_sparse\nQdrant/bm25"]
            FILTER["build_access_filter\nvisibility=public\nOR user_id=current\n🆕 AND folder_id=?"]
            PROMPT["_build_rag_messages\n_truncate_contexts\n16 384 char budget"]
            LLM_C["LLM Client\nstream=True · temp=0.2"]
        end
    end

    %% ─────────────────────────────────────────
    subgraph ING ["📋  Inngest  :8288"]
        EV_IN["Event  rag/ingest_pdf\npdf_path · source_id\nuser_id · visibility\n🆕 folder_id"]
        FN_IN["rag_ingest_pdf\nthrottle 2 req/min\nrate-limit 1/4 h per source"]
        EV_QR["Event  rag/query_pdf_ai"]
        FN_QR["rag_query_pdf_ai\nrate-limit 10 req/min/user"]
    end

    %% ─────────────────────────────────────────
    subgraph STORE ["🗄️  Storage Layer"]
        FS[/"📁  /app/uploads/\ntemporary file buffer"/]

        QD[("🔍  Qdrant  :6333\ncollection: docs\n─────────────────\ndense  384-dim · COSINE\nsparse BM25 · on-disk\nfusion: RRF\n─────────────────\nKEYWORD indexes:\nuser_id · visibility\nsource\n🆕 folder_id")]

        SQ[("🗃️  SQLite\n─────────────────\ntable: documents\nsource_id · user_id\nvisibility · chunk_count\ningested_at\n🆕 folder_id\n─────────────────\n🆕 table: folders\nfolder_id · name\nuser_id · created_at\n─────────────────\ntable: llm_config\nkey · value")]
    end

    %% ══════════════════════════════════════════
    %% FLOW 1 — Auth
    %% ══════════════════════════════════════════
    USER -->|"visit · restore key"| FE_AUTH
    FE_AUTH -->|"POST  { access_key? }"| R_AUTH
    R_AUTH -->|"SHA-256 key → user_id\n{ user_id, access_key, is_new }"| FE_AUTH

    %% ══════════════════════════════════════════
    %% FLOW 2 — LLM Config
    %% ══════════════════════════════════════════
    USER -->|"switch provider / model"| FE_SET
    FE_SET -->|"POST { base_url, model, api_key }"| R_LLM
    R_LLM -->|"set_llm_config"| SQ

    %% ══════════════════════════════════════════
    %% FLOW 3 — Document Upload
    %% ══════════════════════════════════════════
    USER -->|"drop file\npick visibility\n🆕 pick folder"| FE_UP
    FE_UP -->|"FormData: file · visibility\nuser_id 🆕 · folder_id"| R_UP
    R_UP -->|"save to disk"| FS
    R_UP -->|"fire event"| EV_IN
    R_UP -->|"{ source_id, status: queued }"| FE_UP

    %% ══════════════════════════════════════════
    %% FLOW 4 — Ingestion Pipeline  (Inngest)
    %% ══════════════════════════════════════════
    EV_IN --> FN_IN
    FN_IN -->|"read file"| FS
    FN_IN --> CHUNK
    CHUNK -->|"chunks[ ]"| EMB_D
    CHUNK -->|"chunks[ ]"| EMB_S
    EMB_D -->|"dense vectors  384-dim"| FN_IN
    EMB_S -->|"sparse BM25 vectors"| FN_IN
    FN_IN -->|"upsert points\ndense · sparse · payload\nsource · text · user_id\nvisibility 🆕 · folder_id\nUUID-v5 IDs"| QD
    FN_IN -->|"upsert_document\nchunk_count 🆕 · folder_id"| SQ
    FN_IN -->|"delete file after ingest"| FS

    %% ══════════════════════════════════════════
    %% FLOW 5 — 🆕 Folder Management
    %% ══════════════════════════════════════════
    USER -->|"🆕 create · browse folders"| FE_DOCS
    FE_DOCS -->|"🆕 POST { name, user_id }"| R_FOLD
    FE_DOCS -->|"🆕 GET ?user_id="| R_FOLD
    R_FOLD -->|"🆕 INSERT · SELECT folders"| SQ

    %% ══════════════════════════════════════════
    %% FLOW 6 — Document Management
    %% ══════════════════════════════════════════
    FE_DOCS -->|"GET ?user_id= 🆕 &folder_id="| R_DOCS
    R_DOCS -->|"list_documents"| SQ
    SQ -->|"rows"| R_DOCS
    R_DOCS -->|"document list"| FE_DOCS

    FE_DOCS -->|"PATCH { visibility }"| R_DOCS
    R_DOCS -->|"update_source_visibility"| QD
    R_DOCS -->|"update_visibility"| SQ

    FE_DOCS -->|"DELETE ?user_id="| R_DOCS
    R_DOCS -->|"delete_by_source"| QD
    R_DOCS -->|"delete_document"| SQ

    %% ══════════════════════════════════════════
    %% FLOW 7 — Query / RAG  (streaming path)
    %% ══════════════════════════════════════════
    USER -->|"type question"| FE_ASK
    FE_ASK -->|"GET ?question=\n?top_k= · ?user_id=\n🆕 ?folder_id="| R_QRY
    R_QRY -->|"question text"| EMB_D
    R_QRY -->|"question text"| EMB_S
    EMB_D -->|"question vector 384-dim"| FILTER
    EMB_S -->|"question sparse vec"| FILTER
    FILTER -->|"hybrid search\nprefetch dense × top_k×2\nprefetch sparse × top_k×2\nRRF fusion\naccess + 🆕 folder filter"| QD
    QD -->|"top-k chunks\nsources · scores"| PROMPT
    PROMPT -->|"system + user messages\ncontext injected"| LLM_C
    LLM_C -->|"completion request\nstream=True"| LLM_API
    LLM_API -->|"token stream"| LLM_C
    LLM_C -->|"NDJSON\ntype:token · type:done\ntype:error"| FE_ASK
    FE_ASK -->|"render tokens\nsource badges · scores"| USER

    %% ── Optional observable path (Inngest) ──
    FE_ASK -.->|"optional:\nobservable path"| EV_QR
    EV_QR --> FN_QR
    FN_QR -->|"same embed + filter + prompt"| FILTER
    FN_QR -.->|"{ answer, sources, scores }"| FE_ASK
```

---

## 🆕 Folder Classification — Schema Delta

### What changes in each layer

| Layer | Change |
|-------|--------|
| **SQLite** | New `folders` table: `folder_id TEXT PK · name TEXT · user_id TEXT · created_at TEXT`. Add `folder_id TEXT` FK column to `documents` table. |
| **Qdrant** | Add `folder_id` to point payload. Add a KEYWORD index on `folder_id`. |
| **`build_access_filter()`** | Accept optional `folder_id`; append `FieldCondition(key="folder_id", match=MatchValue(value=folder_id))` as a `must` clause. |
| **Ingest event** | Add `folder_id` field to the Inngest event payload. |
| **`POST /api/documents/upload`** | Accept optional `folder_id` in the form data. |
| **`GET /api/documents`** | Accept optional `?folder_id=` query param. |
| **`GET /api/stream_query`** | Accept optional `?folder_id=` query param; pass to `build_access_filter`. |
| **Frontend** | `FolderPicker` on upload; `FolderSidebar` on DocumentsPage to filter the list; folder selector on AskPage to scope the search. |

### Folder visibility rule
A folder inherits the visibility of its documents — there is no separate folder-level visibility flag. A user sees a folder if they own at least one document in it or if any document in it is public.
