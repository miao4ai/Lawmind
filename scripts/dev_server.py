#!/usr/bin/env python3
"""
Local development server for Mamimind.

Runs a FastAPI server that mimics Cloud Functions locally.
"""

import uuid
import json
from datetime import datetime, timedelta

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

# Add parent directory to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from google.cloud import storage
from google.cloud import firestore
from google.cloud import pubsub_v1

from agents.legal_reasoning_agent import LegalReasoningAgent
from agents.ocr_agent import OCRAgent
from agents.runtime import AgentRuntime
from shared.config import get_settings
from shared.models import Document, DocumentMetadata, DocumentStatus

# Initialize
app = FastAPI(title="Mamimind Dev Server")
settings = get_settings()
agent_runtime = AgentRuntime()
storage_client = storage.Client()
firestore_client = firestore.Client()
pubsub_publisher = pubsub_v1.PublisherClient()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request models
class QueryRequest(BaseModel):
    query: str
    user_id: str
    doc_ids: Optional[List[str]] = None
    top_k: int = 5


class UploadRequest(BaseModel):
    user_id: str
    filename: str
    file_size: int
    mime_type: str = "application/pdf"


# Routes
@app.get("/")
async def root():
    return {
        "service": "Mamimind Dev Server",
        "environment": settings.environment,
        "endpoints": {
            "upload": "POST /upload",
            "complete": "POST /complete/{doc_id}",
            "query": "POST /query",
            "status": "GET /status/{doc_id}",
            "documents": "GET /documents?user_id=xxx",
        },
    }


@app.post("/query")
async def query_endpoint(request: QueryRequest):
    """RAG query endpoint."""
    try:
        agent = LegalReasoningAgent()
        result = await agent_runtime.run(
            agent=agent,
            input_data=request.dict(),
            user_id=request.user_id,
        )

        if result.status == "success":
            return {"status": "success", "data": result.output}
        else:
            raise HTTPException(status_code=500, detail=result.error)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload")
async def upload_endpoint(request: UploadRequest):
    """Generate signed URL for client-side upload to GCS."""
    try:
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        storage_path = f"raw/{request.user_id}/{doc_id}/{request.filename}"

        # Generate signed URL
        bucket = storage_client.bucket(settings.gcp_storage_bucket)
        blob = bucket.blob(storage_path)
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=15),
            method="PUT",
            content_type=request.mime_type,
        )

        # Create document record in Firestore
        doc_data = {
            "doc_id": doc_id,
            "user_id": request.user_id,
            "status": DocumentStatus.UPLOADED.value,
            "metadata": {
                "filename": request.filename,
                "file_size": request.file_size,
                "mime_type": request.mime_type,
            },
            "storage_path": storage_path,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        firestore_client.collection(
            settings.firestore_collection_docs
        ).document(doc_id).set(doc_data)

        return {
            "doc_id": doc_id,
            "upload_url": signed_url,
            "storage_path": storage_path,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/complete/{doc_id}")
async def complete_upload_endpoint(doc_id: str):
    """Trigger OCR processing after client uploads file to GCS."""
    try:
        # Look up document in Firestore
        doc_ref = firestore_client.collection(
            settings.firestore_collection_docs
        ).document(doc_id)
        doc_snapshot = doc_ref.get()

        if not doc_snapshot.exists:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")

        doc_data = doc_snapshot.to_dict()

        # Publish to Pub/Sub to trigger OCR
        topic_path = pubsub_publisher.topic_path(
            settings.gcp_project_id, settings.pubsub_topic_ocr
        )
        message = json.dumps({
            "doc_id": doc_id,
            "user_id": doc_data["user_id"],
            "storage_path": doc_data["storage_path"],
        }).encode()
        pubsub_publisher.publish(topic_path, message)

        # Update status
        doc_ref.update({
            "status": DocumentStatus.OCR_PROCESSING.value,
            "updated_at": datetime.utcnow().isoformat(),
        })

        return {"status": "processing", "doc_id": doc_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status/{doc_id}")
async def status_endpoint(doc_id: str):
    """Get document status from Firestore."""
    try:
        doc_ref = firestore_client.collection(
            settings.firestore_collection_docs
        ).document(doc_id)
        doc_snapshot = doc_ref.get()

        if not doc_snapshot.exists:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")

        return doc_snapshot.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents")
async def list_documents_endpoint(user_id: str):
    """List documents for a user."""
    try:
        docs_ref = firestore_client.collection(
            settings.firestore_collection_docs
        ).where("user_id", "==", user_id)
        docs = docs_ref.stream()

        documents = [doc.to_dict() for doc in docs]
        return {"documents": documents}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    print("🚀 Starting Mamimind Dev Server...")
    print(f"📍 Environment: {settings.environment}")
    print(f"🌐 Server: http://localhost:8000")
    print(f"📚 Docs: http://localhost:8000/docs")

    uvicorn.run(
        "dev_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
