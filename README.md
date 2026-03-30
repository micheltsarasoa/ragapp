# ragapp

A Retrieval-Augmented Generation (RAG) application. Upload PDF, DOCX, TXT, or MD documents and ask questions — the AI answers using only the content of your documents.

**Stack:** FastAPI · Inngest · Qdrant · Streamlit · Groq LLM · fastembed (local embeddings)

---

## Table of contents

1. [How it works](#how-it-works)
2. [Prerequisites](#prerequisites)
3. [Quick start (development)](#quick-start-development)
4. [Windows Server deployment](#windows-server-deployment)
5. [Docker Compose (recommended for servers)](#docker-compose-recommended-for-servers)
6. [Environment variables](#environment-variables)
7. [Project structure](#project-structure)
8. [Resetting the database](#resetting-the-database)

---

## How it works

```
Upload document → Qdrant (hybrid vector store) ← Groq LLM → Answer
                       ↑                              ↑
              fastembed (local)           context chunks retrieved
              dense + BM25 sparse         by dense + BM25 hybrid search
```

- **Ingest:** documents are chunked, embedded (locally, no API cost), and stored in Qdrant with `user_id` and `visibility` (`private` / `public`) metadata.
- **Query:** your question is embedded the same way, hybrid search retrieves the most relevant chunks, and Groq generates a grounded answer.
- **Access control:** queries are filtered — you see your own documents plus all public documents.
- **Streaming:** answers stream token-by-token in the UI, or run through Inngest for full observability.

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11+ | [python.org](https://www.python.org/downloads/) |
| uv | latest | `pip install uv` |
| Docker Desktop | latest | [docker.com](https://www.docker.com/products/docker-desktop/) — for Qdrant |
| Node.js | 18+ | [nodejs.org](https://nodejs.org/) — for Inngest CLI |
| Groq API key | — | Free at [console.groq.com](https://console.groq.com) |

---

## Quick start (development)

### 1. Clone and install

```bash
git clone https://github.com/micheltsarasoa/ragapp.git
cd ragapp
pip install uv
uv venv
uv pip install -r requirements.txt
```

### 2. Configure environment

Create a `.env` file:

```env
GROQ_API_KEY=your_groq_api_key_here
```

### 3. Start Qdrant

```bash
docker run -d --name qdrantRagDb -p 6333:6333 -v "%cd%\qdrant_storage:/qdrant/storage" qdrant/qdrant
```

> On PowerShell use `${PWD}` instead of `%cd%`:
> ```powershell
> docker run -d --name qdrantRagDb -p 6333:6333 -v "${PWD}\qdrant_storage:/qdrant/storage" qdrant/qdrant
> ```

### 4. Start all services (3 terminals)

**Terminal 1 — FastAPI backend**
```bash
uv run uvicorn main:app
```

**Terminal 2 — Inngest dev server**
```bash
npx inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest --no-discovery
```

**Terminal 3 — Streamlit UI**
```bash
uv run streamlit run streamlit_app.py
```

Open http://localhost:8501 in your browser.

---

## Windows Server deployment

This section covers a production-grade setup on **Windows Server 2019 / 2022** without Docker (optional Docker path is in the next section).

### Step 1 — Install prerequisites

Run in an elevated PowerShell:

```powershell
# Install Chocolatey (package manager) if not present
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install Python, Node.js, Git, Docker Desktop
choco install python nodejs git docker-desktop -y
```

Then install `uv`:
```powershell
pip install uv
```

Restart the session so PATH changes take effect.

### Step 2 — Clone and set up the project

```powershell
git clone https://github.com/micheltsarasoa/ragapp.git
cd ragapp
uv venv .venv
.venv\Scripts\activate
uv pip install -r requirements.txt
```

### Step 3 — Create the `.env` file

```powershell
@"
GROQ_API_KEY=your_groq_api_key_here
LLM_MODEL=llama3-8b-8192
API_BASE=http://127.0.0.1:8000
INNGEST_API_BASE=http://127.0.0.1:8288/v1
"@ | Out-File -Encoding utf8 .env
```

### Step 4 — Start Qdrant

```powershell
docker run -d --name qdrantRagDb -p 6333:6333 `
  -v "${PWD}\qdrant_storage:/qdrant/storage" `
  --restart unless-stopped `
  qdrant/qdrant
```

### Step 5 — Run services as Windows Services (NSSM)

Using **NSSM** (Non-Sucking Service Manager) to run each component as a Windows Service that starts automatically and restarts on failure.

```powershell
# Install NSSM
choco install nssm -y
```

**Register FastAPI backend:**
```powershell
$appDir = "C:\ragapp"   # adjust to your actual path
$uvPath = "$appDir\.venv\Scripts\uvicorn.exe"

nssm install ragapp-api $uvPath
nssm set ragapp-api AppParameters "main:app --host 0.0.0.0 --port 8000"
nssm set ragapp-api AppDirectory $appDir
nssm set ragapp-api AppEnvironmentExtra "PYTHONPATH=$appDir"
nssm set ragapp-api Start SERVICE_AUTO_START
nssm set ragapp-api AppStdout "$appDir\logs\api.log"
nssm set ragapp-api AppStderr "$appDir\logs\api-err.log"
New-Item -ItemType Directory -Force "$appDir\logs"
nssm start ragapp-api
```

**Register Streamlit UI:**
```powershell
$streamlitPath = "$appDir\.venv\Scripts\streamlit.exe"

nssm install ragapp-ui $streamlitPath
nssm set ragapp-ui AppParameters "run streamlit_app.py --server.port 8501 --server.address 0.0.0.0"
nssm set ragapp-ui AppDirectory $appDir
nssm set ragapp-ui AppEnvironmentExtra "PYTHONPATH=$appDir"
nssm set ragapp-ui Start SERVICE_AUTO_START
nssm set ragapp-ui AppStdout "$appDir\logs\ui.log"
nssm set ragapp-ui AppStderr "$appDir\logs\ui-err.log"
nssm start ragapp-ui
```

**Register Inngest dev server:**
```powershell
$nodePath = (Get-Command node).Source

nssm install ragapp-inngest $nodePath
nssm set ragapp-inngest AppParameters `
  "$(npm root -g)\inngest-cli\bin\inngest dev -u http://127.0.0.1:8000/api/inngest --no-discovery"
nssm set ragapp-inngest AppDirectory $appDir
nssm set ragapp-inngest Start SERVICE_AUTO_START
nssm set ragapp-inngest AppStdout "$appDir\logs\inngest.log"
nssm set ragapp-inngest AppStderr "$appDir\logs\inngest-err.log"
nssm start ragapp-inngest
```

> **Alternative for Inngest:** for a true production setup, deploy Inngest Cloud and remove the local dev server entirely. See https://www.inngest.com/docs/deploy.

### Step 6 — Open Windows Firewall ports

```powershell
# Allow Streamlit UI from the network
New-NetFirewallRule -DisplayName "RAG App UI" -Direction Inbound `
  -Protocol TCP -LocalPort 8501 -Action Allow

# Allow FastAPI (only if you need direct external API access)
New-NetFirewallRule -DisplayName "RAG App API" -Direction Inbound `
  -Protocol TCP -LocalPort 8000 -Action Allow
```

### Step 7 — (Optional) Reverse proxy with IIS

To serve the Streamlit app on port 80/443 through IIS, install **Application Request Routing**:

1. Install IIS + ARR + URL Rewrite via Server Manager
2. In IIS Manager, create a new site pointing to port 8501
3. Enable **Reverse Proxy** in ARR settings
4. Add a URL Rewrite rule:
   - Pattern: `(.*)`
   - Rewrite URL: `http://127.0.0.1:8501/{R:1}`

For HTTPS, use a certificate from Let's Encrypt via [win-acme](https://www.win-acme.com/).

### Step 8 — Verify everything is running

```powershell
# Check service status
nssm status ragapp-api
nssm status ragapp-ui
nssm status ragapp-inngest

# Check Qdrant
Invoke-WebRequest -Uri http://localhost:6333/healthz -UseBasicParsing
```

---

## Docker Compose (recommended for servers)

The simplest server deployment. Requires Docker Desktop or Docker Engine on the host.

```powershell
# Clone and configure
git clone https://github.com/micheltsarasoa/ragapp.git
cd ragapp

# Create .env
@"
GROQ_API_KEY=your_groq_api_key_here
"@ | Out-File -Encoding utf8 .env

# Build and start (Qdrant + API + UI)
docker compose up --build -d
```

Services:
| Service | URL |
|---------|-----|
| Streamlit UI | http://localhost:8501 |
| FastAPI API | http://localhost:8000 |
| Qdrant | http://localhost:6333 |

> The Inngest dev server is **not** included in Docker Compose.
> Run it on the host: `npx inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest --no-discovery`
> Or deploy to Inngest Cloud for production: https://www.inngest.com/docs/deploy

**Stop all services:**
```powershell
docker compose down
```

**Update the app:**
```powershell
git pull
docker compose up --build -d
```

---

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | Yes | — | Groq API key for LLM inference |
| `LLM_MODEL` | No | `llama3-8b-8192` | Groq model to use |
| `API_BASE` | No | `http://127.0.0.1:8000` | FastAPI base URL (used by Streamlit for streaming) |
| `INNGEST_API_BASE` | No | `http://127.0.0.1:8288/v1` | Inngest dev server API URL |

---

## Project structure

```
ragapp/
├── main.py                    # FastAPI app + Inngest functions + streaming endpoint
├── streamlit_app.py           # Main UI (upload + query)
├── pages/
│   └── 1_Manage_Documents.py  # Document management (list, toggle visibility, delete)
├── data_loader.py             # Document loading (PDF/DOCX/TXT/MD) + fastembed
├── vector_db.py               # Qdrant client (hybrid search, access filter, dedup)
├── custom_types.py            # Pydantic models
├── db.py                      # SQLite metadata (ragapp.db)
├── Dockerfile                 # Container image for API and UI
├── docker-compose.yml         # Multi-service Docker setup
├── requirements.txt           # Python dependencies
├── tuto.md                    # Step-by-step tutorial
└── docs/
    ├── architecture.md        # System diagram + config reference
    ├── setup.md               # Detailed setup guide
    ├── access-control.md      # Public/private document design
    └── improvements.md        # Implemented improvements
```

---

## Resetting the database

Required if upgrading from the original version (Qdrant collection schema changed):

**Local:**
```bash
docker stop qdrantRagDb && docker rm qdrantRagDb
rm -rf qdrant_storage ragapp.db   # Linux/macOS
```
```powershell
docker stop qdrantRagDb; docker rm qdrantRagDb
Remove-Item -Recurse -Force qdrant_storage, ragapp.db   # Windows
```

**Docker Compose:**
```bash
docker compose down -v
rm -rf qdrant_storage ragapp.db
```
