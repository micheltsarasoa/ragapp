"""Smoke tests for the RAG backend API.

Usage (while uvicorn is running):
    uv run python smoke_test.py
    uv run python smoke_test.py --base-url http://localhost:8000
"""

import argparse
import json
import os
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _request(method, url, data=None, headers=None, timeout=10) -> tuple[int, dict | list]:
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read())
        except Exception:
            body = {}
        return e.code, body
    except TimeoutError:
        print(f"\n{YELLOW}Upload timed out — is Inngest running? (`npx inngest-cli@latest dev`){RESET}")
        return -1, {}
    except urllib.error.URLError as e:
        if isinstance(e.reason, OSError) and "timed out" in str(e.reason).lower():
            print(f"\n{YELLOW}Upload timed out — is Inngest running? (`npx inngest-cli@latest dev`){RESET}")
            return -1, {}
        print(f"\n{RED}{BOLD}Cannot connect to {url}{RESET}")
        print(f"{YELLOW}Make sure uvicorn is running:{RESET}")
        print("  cd apps/backend")
        print("  uv run uvicorn app.main:app --reload\n")
        sys.exit(1)
    except ConnectionRefusedError:
        print(f"\n{RED}{BOLD}Cannot connect to {url}{RESET}")
        print(f"{YELLOW}Make sure uvicorn is running:{RESET}")
        print("  cd apps/backend")
        print("  uv run uvicorn app.main:app --reload\n")
        sys.exit(1)


def get(url):
    return _request("GET", url)


def post_json(url, payload):
    return _request("POST", url, json.dumps(payload).encode(), {"Content-Type": "application/json"})


def patch_json(url, payload):
    return _request("PATCH", url, json.dumps(payload).encode(), {"Content-Type": "application/json"})


def delete(url):
    return _request("DELETE", url)


def post_multipart(url, fields: dict, file_path: Path, timeout=10) -> tuple[int, dict]:
    boundary = "SmokeTestBoundary7MA4YWxkTrZu0gW"
    body = b""
    for k, v in fields.items():
        body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
    body += (
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"file\"; filename=\"{file_path.name}\"\r\n"
        f"Content-Type: text/plain\r\n\r\n"
    ).encode() + file_path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    return _request("POST", url, body, {"Content-Type": f"multipart/form-data; boundary={boundary}"}, timeout=timeout)


# ── assertion helper ──────────────────────────────────────────────────────────

_failures = 0

def check(label, passed, reason=""):
    global _failures
    if passed:
        print(f"  {GREEN}✓{RESET} {label}")
    else:
        print(f"  {RED}✗{RESET} {label}  {YELLOW}→ {reason}{RESET}")
        _failures += 1


# ── tests ─────────────────────────────────────────────────────────────────────

def run(base: str) -> int:
    global _failures
    _failures = 0

    # 1. LLM config ─────────────────────────────────────────────────────────
    print(f"\n{BOLD}[1] GET /api/llm_config{RESET}")
    status, body = get(f"{base}/api/llm_config")
    check("status 200",              status == 200,          f"got {status}")
    check("has 'model'",             "model" in body,        str(body))
    check("has 'api_key_set'",       "api_key_set" in body,  str(body))

    # 2. Auth — new identity ─────────────────────────────────────────────────
    print(f"\n{BOLD}[2] POST /api/auth/identity — new key{RESET}")
    status, body = post_json(f"{base}/api/auth/identity", {})
    check("status 200",              status == 200,                        f"got {status}")
    check("has user_id",             "user_id" in body,                    str(body))
    check("has access_key",          "access_key" in body,                 str(body))
    check("is_new=True",             body.get("is_new") is True,           str(body))
    check("access_key is 8 chars",   len(body.get("access_key", "")) == 8, str(body))

    generated_key = body.get("access_key", "TESTKEY1")
    generated_uid = body.get("user_id", "")

    # 3. Auth — restore known key ────────────────────────────────────────────
    print(f"\n{BOLD}[3] POST /api/auth/identity — existing key{RESET}")
    status, body = post_json(f"{base}/api/auth/identity", {"access_key": generated_key})
    check("status 200",              status == 200,                                   f"got {status}")
    check("is_new=False",            body.get("is_new") is False,                    str(body))
    check("same user_id for same key", body.get("user_id") == generated_uid,         f"{body.get('user_id')} ≠ {generated_uid}")

    _, body_upper = post_json(f"{base}/api/auth/identity", {"access_key": "ABCD1234"})
    _, body_lower = post_json(f"{base}/api/auth/identity", {"access_key": "abcd1234"})
    check("key normalised to uppercase", body_upper.get("user_id") == body_lower.get("user_id"), "case mismatch")

    # 4. Documents list ──────────────────────────────────────────────────────
    print(f"\n{BOLD}[4] GET /api/documents{RESET}")
    status, body = get(f"{base}/api/documents?user_id=anonymous")
    check("status 200",              status == 200,             f"got {status}")
    check("returns a list",          isinstance(body, list),    type(body).__name__)

    # 5. Upload ──────────────────────────────────────────────────────────────
    print(f"\n{BOLD}[5] POST /api/documents/upload{RESET}")
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".txt")
    try:
        os.write(tmp_fd, b"Smoke test document.\nSecond sentence for chunking.")
    finally:
        os.close(tmp_fd)
    tmp = Path(tmp_path)
    source_id = ""
    try:
        status, body = post_multipart(
            f"{base}/api/documents/upload",
            {"visibility": "private", "user_id": "smoketest"},
            tmp,
            timeout=30,
        )
        check("status 200",              status == 200,                                        f"got {status}")
        check("returns source_id",       "source_id" in body,                                  str(body))
        check("status=queued",           body.get("status") == "queued",                       str(body))
        check("source_id prefixed",      body.get("source_id", "").startswith("smoketest:"),   str(body))
        source_id = body.get("source_id", "")
    finally:
        tmp.unlink(missing_ok=True)

    # 5b. Qdrant health ─────────────────────────────────────────────────────
    print(f"\n{BOLD}[5b] Qdrant health{RESET}")
    qdrant_up = False
    try:
        req = urllib.request.Request("http://localhost:6333/healthz")
        with urllib.request.urlopen(req, timeout=3) as r:
            qdrant_up = r.status == 200
    except Exception:
        pass
    if qdrant_up:
        print(f"  {GREEN}✓{RESET} Qdrant is reachable")
    else:
        print(f"  {YELLOW}⚠ Qdrant is not running — checks 6 and 7 will fail{RESET}")
        print(f"  {YELLOW}  Start it: docker run -d --name qdrantRagDb -p 6333:6333 qdrant/qdrant{RESET}")

    # 6. Visibility update ───────────────────────────────────────────────────
    print(f"\n{BOLD}[6] PATCH /api/documents/{{source_id}}/visibility{RESET}")
    if source_id:
        encoded = urllib.parse.quote(source_id, safe="")
        status, body = patch_json(
            f"{base}/api/documents/{encoded}/visibility",
            {"visibility": "public", "user_id": "smoketest"},
        )
        check("status 200",          status == 200,             f"got {status}")
        check("returns status=ok",   body.get("status") == "ok", str(body))
    else:
        print(f"  {YELLOW}⚠ skipped — upload failed{RESET}")

    # 7. Delete ──────────────────────────────────────────────────────────────
    print(f"\n{BOLD}[7] DELETE /api/documents/{{source_id}}{RESET}")
    if source_id:
        encoded = urllib.parse.quote(source_id, safe="")
        status, body = delete(f"{base}/api/documents/{encoded}?user_id=smoketest")
        check("status 200",          status == 200,              f"got {status}")
        check("returns status=ok",   body.get("status") == "ok", str(body))
    else:
        print(f"  {YELLOW}⚠ skipped — upload failed{RESET}")

    # 8. Inngest endpoint ────────────────────────────────────────────────────
    print(f"\n{BOLD}[8] Inngest endpoint{RESET}")
    status, _ = get(f"{base}/api/inngest")
    check("not 404",                 status != 404,             f"got {status}")

    # Summary ────────────────────────────────────────────────────────────────
    print()
    if _failures == 0:
        print(f"{BOLD}{GREEN}All tests passed.{RESET}\n")
    else:
        print(f"{BOLD}{RED}{_failures} test(s) failed.{RESET}\n")
    return _failures


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RAG backend smoke tests")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    args = parser.parse_args()
    sys.exit(run(args.base_url))
