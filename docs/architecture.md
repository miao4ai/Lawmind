# Mamimind Architecture

## Overview

Mamimind is a cloud-native agentic AI system for legal document intelligence, designed to run on Google Cloud Platform (GCP).

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js)                       │
│                     Cloud Run / Vercel                           │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTPS
┌────────────────────────┴────────────────────────────────────────┐
│                    API Gateway / Load Balancer                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  upload_doc │  │  rag_query  │  │ doc_status  │
│Cloud Function│  │Cloud Function│  │Cloud Function│
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │
       │                │                │
       ▼                │                ▼
┌─────────────┐         │         ┌─────────────┐
│Cloud Storage│         │         │  Firestore  │
│   (Docs)    │         │         │ (Metadata)  │
└──────┬──────┘         │         └─────────────┘
       │                │
       │ Pub/Sub        │
       ▼                │
┌─────────────┐         │
│ocr_process  │         │
│Cloud Function│         │
└──────┬──────┘         │
       │                │
       │ Pub/Sub        │
       ▼                │
┌─────────────┐         │
│ index_doc   │         │
│Cloud Function│         │
└──────┬──────┘         │
       │                │
       ▼                ▼
┌──────────────────────────┐
│   Vector DB (Qdrant)     │
│  Vertex AI Vector Search │
└──────────────────────────┘
```

## Component Design

### 1. Frontend Layer

**Technology**: Next.js + React + TypeScript

**Responsibilities**:
- User interface for document upload
- Query interface with citation display
- Real-time status updates
- Authentication (Firebase Auth / OAuth)

**Deployment**: Cloud Run or Vercel

### 2. Services Layer (Cloud Functions)

#### a. upload_doc
- **Type**: HTTP-triggered
- **Purpose**: Generate signed upload URL
- **Flow**:
  1. Validate user request
  2. Create document record in Firestore
  3. Generate signed URL for Cloud Storage
  4. Return URL to client

#### b. ocr_process
- **Type**: Pub/Sub-triggered (on upload complete)
- **Purpose**: OCR and layout analysis
- **Agent**: OCRAgent
- **Flow**:
  1. Download document from Cloud Storage
  2. Run OCR (Google Cloud Vision API)
  3. Extract layout structure
  4. Save results to Cloud Storage
  5. Publish to indexing topic

#### c. index_doc
- **Type**: Pub/Sub-triggered (after OCR)
- **Purpose**: Chunk and index document
- **Agent**: IndexingAgent
- **Flow**:
  1. Load OCR results
  2. Clause-aware chunking
  3. Generate embeddings
  4. Store in vector database
  5. Update document status to READY

#### d. rag_query
- **Type**: HTTP-triggered
- **Purpose**: Answer user queries
- **Agent**: LegalReasoningAgent
- **Flow**:
  1. Generate query embedding
  2. Search vector database
  3. Retrieve relevant chunks
  4. LLM-based reasoning
  5. Return answer + citations

#### e. doc_status
- **Type**: HTTP-triggered
- **Purpose**: Get document processing status
- **Flow**:
  1. Query Firestore for document
  2. Return status and metadata

### 3. Agent Layer

**Architecture**: Custom agent framework with strong contracts

**Key Components**:
- `Agent` base class: Interface for all agents
- `AgentRuntime`: Execution with retry, timeout, tracing
- `AgentRegistry`: Dynamic agent discovery

**Agents**:
1. **OCRAgent**: Document text extraction
2. **IndexingAgent**: Chunking and embedding
3. **LegalReasoningAgent**: Q&A with reasoning

**Features**:
- Structured input/output (Pydantic models)
- Automatic retry with exponential backoff
- Distributed tracing (OpenTelemetry)
- Tool composition

### 4. Tools Layer

Reusable tools that agents can call:

- **OCRTool**: Google Cloud Vision API wrapper
- **ChunkingTool**: Clause-aware text splitting
- **EmbeddingTool**: OpenAI embeddings
- **VectorSearchTool**: Vector database search
- **LLMTool**: LLM generation (GPT-4, Claude)

### 5. Data Layer

#### Cloud Storage
- **Purpose**: Store raw and processed documents
- **Structure**:
  ```
  {bucket}/
    raw/{user_id}/{doc_id}/original.pdf
    processed/{doc_id}/
      ocr_result.json
      layout.json
      chunks.json
  ```

#### Firestore
- **Purpose**: Document metadata and status tracking
- **Collections**:
  - `documents`: Document records with status
  - `users`: User information

#### Vector Database (Qdrant)
- **Purpose**: Semantic search over document chunks
- **Schema**:
  - Vector: 1536-dim (OpenAI embedding)
  - Payload: chunk text, metadata, doc_id

#### Alternative: Vertex AI Vector Search
- Fully managed by GCP
- Integrated with Vertex AI

### 6. Observability

- **Logging**: Cloud Logging + structlog
- **Tracing**: Cloud Trace + OpenTelemetry
- **Metrics**: Cloud Monitoring
- **Alerting**: Cloud Monitoring alerts

## Key Design Decisions

### Why Cloud Functions?

**Pros**:
- Zero server management
- Auto-scaling
- Pay-per-invocation
- Integrated with GCP services

**Cons**:
- Cold start latency (mitigated by min instances)
- Execution time limit (9 min for 2nd gen)
- Request size limits

**Alternative: Cloud Run**
- More flexible (WebSocket, long-running)
- Container-based
- Better for complex services

**Recommendation**: Use Cloud Run for `rag_query` (low latency), Cloud Functions for background tasks.

### Why Pub/Sub?

- Decouples services
- Reliable message delivery
- Easy to add new consumers
- Built-in retry and dead-letter queues

### Why Qdrant?

- High-performance vector search
- Self-hosted or cloud
- Good Python client
- Cost-effective

**Alternative**: Vertex AI Vector Search (fully managed)

### Agent Architecture Benefits

1. **Composability**: Agents can call tools and other agents
2. **Testability**: Strong contracts make unit testing easy
3. **Observability**: Built-in tracing for every agent execution
4. **Reliability**: Automatic retry and error handling
5. **Scalability**: Stateless agents can scale horizontally

## Deployment Strategy

### Development
- Local development with emulators
- Docker Compose for dependencies (Qdrant, etc.)

### Staging
- Separate GCP project
- Full cloud deployment
- Integrated testing

### Production
- Blue-green deployment
- Canary releases for critical services
- Automated rollback on errors

## Security

- **Authentication**: Firebase Auth / OAuth 2.0
- **Authorization**: Firestore security rules
- **Data encryption**: At rest (Cloud Storage) and in transit (HTTPS)
- **Secrets management**: Secret Manager
- **Network**: VPC for private resources

## Cost Optimization

- Use Cloud Functions for bursty workloads
- Set min/max instances based on usage
- Use Cloud Storage lifecycle policies
- Monitor and set budget alerts
- Use Vertex AI for embeddings (cheaper at scale)

## Scalability

- **Horizontal**: All services are stateless
- **Vertical**: Adjust Cloud Function memory/CPU
- **Database**: Firestore auto-scales, Qdrant can cluster
- **Caching**: Cloud CDN for frontend, Cloud Memorystore for hot data

## Future Enhancements

1. **Real-time collaboration**: Multiple users querying same docs
2. **Document comparison**: Side-by-side clause analysis
3. **Workflow automation**: Contract review workflows
4. **Multi-modal**: Support for images, tables
5. **Fine-tuned models**: Domain-specific LLMs
