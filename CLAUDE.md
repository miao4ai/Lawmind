# CLAUDE.md — Lawmind Project Reference

This file gives Claude (and future contributors) the full context needed to work effectively in this repo.

---

## What This Project Is

**Lawmind** (internal name: Mamimind) is an AI-powered legal document intelligence platform.

Core capability: users upload legal documents (PDFs), the system processes them, and users can ask natural language questions and get answers with citations back to source passages.

---

## Architecture Layers

### 1. Frontend
- **Next.js 14** + TypeScript + Tailwind CSS
- Pages: `/` (landing), `/upload` (drag-drop upload), `/search` (Q&A interface)
- State: Zustand (`frontend/lib/store.ts`)
- API client: Axios (`frontend/lib/api.ts`) → points to `NEXT_PUBLIC_API_BASE_URL`
- Deployed to: Cloud Run

### 2. AI Search Layer (core business logic)
- User query → OpenAI embedding → Qdrant vector search → GPT-4 answer + citations
- Entry point: `services/rag_query/handler.py` → `LegalReasoningAgent`
- Tools: `tools/vector_search.py`, `tools/llm.py`, `tools/embeddings.py`
- **This is the most important layer** — everything else exists to feed data into it

### 3. Data Engineering Layer
- Handles document ingestion at scale: OCR → chunking → embedding → indexing
- **Current implementation**: Cloud Functions triggered by Pub/Sub
- **Planned implementation**: Apache Spark + Apache Airflow + GKE (see `docs/data_infra.md`)
- The data engineering layer is intentionally separate from AI search — it's a data pipeline that produces embeddings; the AI layer consumes them

### 4. Agent Framework
- Custom Python agent base class in `agents/base.py`
- `AgentRuntime` (`agents/runtime.py`): handles retry (max 3), timeout (300s), OpenTelemetry tracing
- Agents: `OCRAgent`, `LegalReasoningAgent`, `IndexingAgent` (planned)
- Each agent has `validate_input()` and `execute()` — strong I/O contracts via Pydantic

### 5. Infrastructure
- GCP: Cloud Storage (docs), Firestore (metadata), Pub/Sub (async triggers), Cloud Functions (services)
- IaC: Terraform in `infra/gcp/main.tf`
- Planned addition: GKE cluster for Spark workloads (see `docs/data_infra.md`)

---

## Known Issues / TODOs

| File | Issue |
|------|-------|
| `services/ocr_process/handler.py:70` | `# TODO: Save result.output to Cloud Storage` — OCR results are not actually persisted |
| `services/` | `index_doc` handler file does not exist — Pub/Sub publishes to `index-doc` topic but nothing consumes it |
| `tools/llm.py:38` | Uses old OpenAI API (`ChatCompletion.acreate`) — must be updated to `openai>=1.0` style (`client.chat.completions.create`) |

---

## Data Flow

### Document ingestion (current)
```
User uploads PDF
  → POST /upload → signed GCS URL → PUT file to GCS
  → POST /complete → Pub/Sub (ocr-process topic)
  → ocr_process Cloud Function → OCRAgent (Cloud Vision OCR)
  → Pub/Sub (index-doc topic)
  → [index_doc handler — NOT YET IMPLEMENTED]
  → Qdrant (vector embeddings)
```

### Document ingestion (planned — Spark + Airflow)
```
User uploads PDF → GCS
  → Airflow GCS sensor detects new file
  → Spark OCR job (parallel PDF text extraction)
  → Spark embed job (chunking + OpenAI embeddings)
  → KubernetesPodOperator → index into Qdrant
```
See `docs/data_infra.md` for full details.

### AI Search query
```
User asks question
  → POST /query → LegalReasoningAgent
  → embed query (OpenAI text-embedding-3-small)
  → Qdrant vector search (filter by user_id, optional doc_ids)
  → GPT-4 generates answer from retrieved chunks
  → return {answer, citations, confidence}
```

---

## Tech Stack Quick Reference

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, TypeScript, Tailwind, Zustand |
| AI / LLM | GPT-4 Turbo (answers), text-embedding-3-small (embeddings) |
| Vector DB | Qdrant (local + cloud) |
| Metadata DB | Firestore |
| Storage | Google Cloud Storage |
| OCR | Google Cloud Vision API (primary), Tesseract (fallback) |
| Data pipeline (current) | Cloud Functions + Pub/Sub |
| Data pipeline (planned) | Apache Spark + Apache Airflow + GKE |
| Orchestration (planned) | Airflow DAGs in `dags/` |
| Observability | OpenTelemetry + Cloud Trace + structlog |
| IaC | Terraform |

---

## Key Files

```
frontend/lib/api.ts                       API client
frontend/lib/store.ts                     Global state (Zustand)
frontend/pages/search.tsx                 Search UI
frontend/pages/upload.tsx                 Upload UI

agents/base.py                            Agent interface
agents/runtime.py                         Execution engine (retry/trace/timeout)
agents/legal_reasoning_agent/agent.py     Core AI search agent
agents/ocr_agent/agent.py                 OCR + layout agent

tools/vector_search.py                    Qdrant search + indexing
tools/llm.py                              OpenAI GPT-4 wrapper (needs API update)
tools/embeddings.py                       OpenAI embeddings
tools/chunking.py                         Clause-aware text splitting

services/rag_query/handler.py             HTTP endpoint for AI search
services/upload_doc/handler.py            Signed URL generation
services/ocr_process/handler.py           Pub/Sub OCR handler

shared/config/settings.py                 Pydantic settings (loads from .env)
shared/models/document.py                 Document + status models

dags/document_pipeline.py                 Airflow DAG (to be created)
jobs/ocr_job.py                           Spark OCR job (to be created)
jobs/embed_job.py                         Spark embedding job (to be created)

infra/gcp/main.tf                         Terraform (GCP resources + GKE)
docker-compose.yml                        Local dev infra
docs/architecture.md                      System architecture
docs/data_infra.md                        Spark + Airflow + GKE data pipeline plan
```

---

## Environment Variables

See `.env.example` for the full list. Key ones:

```bash
# GCP
GCP_PROJECT_ID=
GCP_REGION=us-central1
GCP_STORAGE_BUCKET=

# AI APIs
OPENAI_API_KEY=           # required for embeddings + GPT-4
ANTHROPIC_API_KEY=        # optional alternative LLM

# Vector DB
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=mamimind_docs

# Frontend
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

---

## Local Development

### Start full local stack
```bash
docker-compose up
# Airflow UI: http://localhost:8080
# Spark UI:   http://localhost:8081
# MinIO UI:   http://localhost:9001
# Qdrant UI:  http://localhost:6333/dashboard
```

### Run frontend
```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

### Run backend (Cloud Functions locally)
```bash
pip install -r requirements.txt
python scripts/dev_server.py
```

---

## Deployment

### Backend (Cloud Functions)
```bash
bash deployment/deploy.sh
```

### Frontend (Cloud Run)
```bash
cd frontend
bash deploy-cloudrun.sh
```

### Infrastructure (Terraform)
```bash
cd infra/gcp
terraform init
terraform plan
terraform apply
```

---

## Design Decisions

- **OCR/Pub/Sub/Terraform are intentional** — they are the data engineering layer. Not over-engineering: large-scale document processing requires a proper data pipeline separate from AI search.
- **Spark chosen for OCR at scale** — parallelizes PDF processing across executors; much faster than single-threaded Cloud Functions for bulk ingestion.
- **Airflow chosen for orchestration** — replaces ad-hoc Pub/Sub chaining with explicit, visible DAGs. Easier to debug, retry, and extend.
- **GKE as the bridge** — local Spark jobs can be submitted to GKE without code changes (only connection config changes). Enables local dev → cloud prod without divergence.
- **GCS as shared data layer** — both local (via MinIO emulation) and cloud (real GCS) use the same path conventions. Switching environments = one env var change.
- **Agent framework** — provides consistent retry, timeout, tracing across all AI tasks. Overhead is justified by observability needs in a production legal AI system.

---

## What NOT to Change Without Thinking Carefully

1. **Document status state machine** (`shared/models/document.py`) — frontend, backend, and Airflow DAGs all depend on these exact status strings.
2. **GCS path conventions** (`raw/{user_id}/{doc_id}/`, `processed/{doc_id}/`) — changing these breaks existing documents.
3. **Qdrant payload schema** — changing `user_id`, `doc_id`, `text` field names in payloads requires re-indexing all documents.
4. **Airflow DAG IDs** — once in production, changing a DAG ID orphans its run history.
