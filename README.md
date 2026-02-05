# Mamimind - Agentic AI Legal Document Intelligence System

## 🎯 Product Overview

Mamimind is an intelligent legal document processing platform that combines OCR, RAG (Retrieval-Augmented Generation), and agentic AI to provide accurate answers to legal questions based on uploaded documents.

### Key Features
- 📄 Multi-format document upload (PDF, images)
- 🔍 Advanced OCR with layout analysis
- 🧠 Clause-aware chunking for legal documents
- 💬 Intelligent Q&A with citation
- 🤖 Agentic AI architecture for reasoning
- ☁️  Cloud-native deployment on GCP

## 🏗️ Architecture

### High-Level Flow
```
User Upload → OCR Processing → Indexing → Vector DB
                                              ↓
User Query → RAG Agent → Legal Reasoning → Answer + Citations
```

### Technology Stack
- **Frontend**: Next.js + React + TypeScript
- **Backend**: Python 3.11+ with Cloud Functions/Cloud Run
- **Agent Framework**: Custom agent runtime with tracing
- **Vector DB**: Qdrant / Vertex AI Vector Search
- **Metadata DB**: Firestore
- **Storage**: Cloud Storage
- **Orchestration**: Cloud Pub/Sub
- **Observability**: Cloud Logging + Cloud Trace

## 📁 Project Structure

See [docs/architecture.md](docs/architecture.md) for detailed architecture.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- GCP account with billing enabled
- gcloud CLI installed

### Local Development

```bash
# Backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
npm run dev

# Run local dev server
python scripts/dev_server.py
```

### Deployment

```bash
# Deploy all services
./deployment/deploy.sh

# Deploy specific service
./deployment/deploy_function.sh rag_query
```

## 📚 Documentation

- [Architecture Overview](docs/architecture.md)
- [Agent Design](docs/agents.md)
- [API Specification](docs/api_spec.md)
- [Deployment Guide](docs/deployment.md)
- [Demo Walkthrough](docs/demo.md)

## 🧪 Testing

```bash
# Unit tests
pytest tests/unit

# Integration tests
pytest tests/integration

# E2E tests
pytest tests/e2e
```

## 📝 License

MIT

## 👥 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)
