# Testing

## Smoke tests

`apps/backend/smoke_test.py` covers all Phase 1 API endpoints. Run it while uvicorn is up:

```bash
# terminal 1
cd apps/backend
uv run uvicorn app.main:app --reload

# terminal 2
cd apps/backend
uv run python smoke_test.py
```

Custom base URL (e.g. staging):
```bash
uv run python smoke_test.py --base-url http://your-server:8000
```

Exit code is `0` on full pass, `1` on any failure — safe to use in CI.

---

## What each check verifies

| # | Endpoint | What is checked |
|---|----------|-----------------|
| 1 | `GET /api/llm_config` | Server is reachable; response contains `model` and `api_key_set` |
| 2 | `POST /api/auth/identity` — no key | Generates an 8-char access key; `is_new=true`; returns `user_id` |
| 3 | `POST /api/auth/identity` — known key | Same key always maps to same `user_id`; `is_new=false`; key normalised to uppercase |
| 4 | `GET /api/documents` | Returns a list (empty is fine); no 500 |
| 5 | `POST /api/documents/upload` | Accepts a `.txt` file via multipart; returns `source_id` prefixed with `user_id` and `status=queued` |
| 6 | `PATCH /api/documents/{source_id}/visibility` | Updates visibility of the uploaded doc; returns `status=ok` |
| 7 | `DELETE /api/documents/{source_id}` | Deletes the uploaded doc; returns `status=ok` |
| 8 | `GET /api/inngest` | Inngest handler is mounted and reachable (not 404) |

> Checks 6 and 7 are skipped automatically if check 5 failed (no `source_id` to work with).

---

## Notes

- The `/api/stream_query` endpoint is **not** covered here — it requires Qdrant running and at least one ingested document. Test it manually via the Swagger UI at `http://localhost:8000/docs` after a successful upload.
- Checks 6 and 7 call Qdrant internally. If Qdrant is not running they will return a 500 — start it with `docker compose up qdrant` before running the suite.
