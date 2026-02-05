#!/usr/bin/env python3
"""
Local development server for Mamimind.

Runs a FastAPI server that mimics Cloud Functions locally.
"""

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import asyncio

# Add parent directory to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.legal_reasoning_agent import LegalReasoningAgent
from agents.ocr_agent import OCRAgent
from agents.runtime import AgentRuntime
from shared.config import get_settings

# Initialize
app = FastAPI(title="Mamimind Dev Server")
settings = get_settings()
agent_runtime = AgentRuntime()

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
            "query": "POST /query",
            "upload": "POST /upload",
            "status": "GET /status/{doc_id}",
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
    """Upload document endpoint."""
    # TODO: Implement upload logic
    return {
        "doc_id": "dev_doc_123",
        "upload_url": "http://localhost:8000/upload/dev_doc_123",
        "storage_path": f"raw/{request.user_id}/dev_doc_123/{request.filename}",
    }


@app.get("/status/{doc_id}")
async def status_endpoint(doc_id: str):
    """Get document status."""
    # TODO: Implement status check
    return {
        "doc_id": doc_id,
        "status": "ready",
        "metadata": {
            "filename": "example.pdf",
            "page_count": 10,
        },
    }


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
