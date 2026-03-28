# Lawmind

AI-powered legal document intelligence platform. Upload PDFs, ask questions in natural language, get answers with citations back to source passages.

---

## What it does

1. User uploads a legal PDF
2. Documents are OCR'd, chunked clause-by-clause, and embedded into a vector database
3. User asks a natural language question
4. System retrieves the most relevant passages and uses GPT-4 to generate an answer with citations

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Frontend (Next.js)  —  Cloud Run                        │
│  /upload  /search                                        │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP
        ┌──────────────┴──────────────┐
        │                             │
   upload_doc                    rag_query
  (Cloud Function)           (Cloud Function)
        │                             │
        ▼                             ▼
   Cloud Storage              LegalReasoningAgent
   + Firestore                 → Qdrant (vector search)
        │                       → GPT-4 (answer + citations)
        ▼
   [Data Pipeline]
   Cloud Functions + Pub/Sub   (current)
   Spark + Airflow + GKE       (planned)
```

### Layers

| Layer | What it does | Key files |
|-------|-------------|-----------|
| **Frontend** | Upload UI, search UI, citation display | `frontend/pages/`, `frontend/components/` |
| **AI Search** | Embed query → Qdrant → GPT-4 → answer | `agents/legal_reasoning_agent/`, `tools/vector_search.py` |
| **Data Pipeline** | PDF → OCR → chunk → embed → Qdrant | `services/`, `jobs/`, `agents/ocr_agent/` |
| **Agent Framework** | Retry, timeout, tracing for all agents | `agents/base.py`, `agents/runtime.py` |
| **Infrastructure** | GCS, Firestore, Pub/Sub, GKE | `infra/gcp/main.tf`, `docker-compose.yml` |

---

## Tech stack

| | Technology |
|-|-----------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, Zustand |
| LLM | GPT-4 Turbo (answers), text-embedding-3-small (embeddings) |
| Vector DB | Qdrant |
| Metadata | Firestore |
| Storage | Google Cloud Storage |
| OCR | Google Cloud Vision API / pytesseract (local) |
| Data pipeline | Cloud Functions + Pub/Sub (production), Spark + docker-compose (local) |
| Infrastructure | Terraform, GKE, Cloud Run |
| Observability | OpenTelemetry, Cloud Trace, structlog |

---

## Local development

### Prerequisites

- Docker + Docker Compose
- Python 3.11+
- Node.js 18+
- An OpenAI API key

### 1. Start the local Spark cluster

The local stack runs Spark (master + 2 workers) and Qdrant via Docker Compose.

```bash
cp .env.example .env
# Fill in OPENAI_API_KEY at minimum

docker-compose up -d --build
```

| Service | URL |
|---------|-----|
| Spark master UI | http://localhost:8081 |
| Spark worker 1 | http://localhost:8082 |
| Spark worker 2 | http://localhost:8083 |
| Qdrant dashboard | http://localhost:6333/dashboard |

### 2. Download sample PDFs (optional)

```bash
python data/download_legal_pdfs.py --target 50 --dest storage/raw/demo_user/
```

### 3. Run the document processing pipeline

```bash
# Full pipeline: OCR + embed + index into Qdrant
bash scripts/run_spark_pipeline.sh

# Stage 1 only (OCR, no OpenAI calls)
bash scripts/run_spark_pipeline.sh --ocr-only

# Stage 2 only (embed + index, reads from storage/processed/ocr/)
bash scripts/run_spark_pipeline.sh --embed-only
```

Pipeline stages:

```
storage/raw/**/*.pdf
  ↓  jobs/ocr_job.py   — pytesseract OCR, parallel across Spark executors
storage/processed/ocr/*.json
  ↓  jobs/embed_job.py — clause-aware chunking + OpenAI embeddings + Qdrant upsert
Qdrant collection: mamimind_docs
```

### 4. Run the frontend

```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

### 5. Run the backend locally

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python scripts/dev_server.py   # http://localhost:8000
```

---

## GCS + GKE (cloud mode)

### Connect local Spark to GCS

Place a GCP service account key at `credentials/service-account.json` (gitignored).
See [credentials/README.md](credentials/README.md) for setup instructions.

```bash
# Run pipeline reading from / writing to GCS
bash scripts/run_spark_pipeline.sh --gcs
```

### Submit Spark jobs to GKE

```bash
# Get GKE credentials
gcloud container clusters get-credentials your-cluster --region us-central1

# Submit to GKE (uses Workload Identity — no key file needed on cloud)
bash scripts/run_spark_pipeline.sh --gcs --gke --gke-image gcr.io/your-project/spark-lawmind:latest
```

---

## Cloud deployment

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
terraform init && terraform apply
```

---

## Project structure

```
Lawmind/
├── frontend/               Next.js app (Cloud Run)
│   ├── pages/              / , /upload, /search
│   └── components/         UploadBox, SearchBox, AnswerPanel, CitationList
│
├── agents/                 Agent framework
│   ├── base.py             Agent interface (ABC)
│   ├── runtime.py          Execution engine (retry, timeout, tracing)
│   ├── ocr_agent/          PDF OCR + layout analysis
│   └── legal_reasoning_agent/  RAG Q&A with citations
│
├── tools/                  Reusable tools used by agents
│   ├── ocr.py              Cloud Vision API wrapper
│   ├── chunking.py         Clause-aware text splitting
│   ├── embeddings.py       OpenAI embeddings
│   ├── vector_search.py    Qdrant search + indexing
│   └── llm.py              GPT-4 wrapper
│
├── services/               Cloud Function handlers
│   ├── upload_doc/         Signed URL generation + Firestore record
│   ├── ocr_process/        Pub/Sub-triggered OCR
│   └── rag_query/          HTTP query endpoint
│
├── jobs/                   Spark jobs (local cluster or GKE)
│   ├── ocr_job.py          Stage 1: PDF → text (pytesseract)
│   └── embed_job.py        Stage 2: text → embeddings → Qdrant
│
├── shared/                 Shared config + Pydantic models
├── vector_db/              Qdrant client abstraction
├── metadata_db/            Firestore repository
├── observability/          OpenTelemetry tracing + structlog
│
├── data/                   Data utilities
│   ├── download_legal_pdfs.py   Bulk PDF downloader (GovInfo.gov)
│   └── upload_to_gcs.py         GCS uploader
│
├── storage/                Local file storage (mirrors GCS layout)
│   ├── raw/                raw/{user_id}/{doc_id}/{filename}.pdf
│   └── processed/          processed/ocr/  processed/embeddings/
│
├── credentials/            GCP service account keys (gitignored)
├── spark/                  Spark config + Docker image deps
├── infra/gcp/              Terraform (GCS, Firestore, Pub/Sub, GKE)
├── deployment/             Cloud Function deploy scripts
├── scripts/                Dev utilities + pipeline runner
├── docs/                   Architecture + data infra design docs
│
├── docker-compose.yml      Local Spark cluster + Qdrant
├── Dockerfile.spark        Custom Spark image (tesseract + OCR deps + GCS connector)
└── CLAUDE.md               Project reference for Claude / contributors
```

---

## Environment variables

Copy `.env.example` to `.env` and fill in:

```bash
# Required
OPENAI_API_KEY=sk-...
GCP_PROJECT_ID=your-project
GCP_STORAGE_BUCKET=your-bucket

# Vector DB (defaults work with docker-compose)
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=mamimind_docs

# Frontend
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# GKE (only needed for --gke mode)
GKE_SPARK_IMAGE=gcr.io/your-project/spark-lawmind:latest
```

---

## Known issues

| File | Issue |
|------|-------|
| `services/ocr_process/handler.py:70` | OCR results are not saved to GCS (TODO) |
| `services/` | `index_doc` Cloud Function handler is missing — Pub/Sub message is published but never consumed |
| `tools/llm.py` | Uses old OpenAI API style (`ChatCompletion.acreate`) — needs update to `openai>=1.0` |

---

## Docs

- [System architecture](docs/architecture.md)
- [Data pipeline design (Spark + Airflow + GKE)](docs/data_infra.md)
- [Agent framework](docs/agents.md)
- [GCP credentials setup](credentials/README.md)
