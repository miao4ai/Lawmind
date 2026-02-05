"""
Cloud Function handler for RAG query.

Deployment:
    gcloud functions deploy rag-query \
        --runtime python311 \
        --trigger-http \
        --allow-unauthenticated \
        --entry-point handle_query
"""

import functions_framework
from flask import Request, jsonify
import asyncio
from typing import Dict, Any

# Import from shared modules (deployed with function)
import sys
sys.path.insert(0, "/workspace")

from agents.legal_reasoning_agent import LegalReasoningAgent
from agents.runtime import AgentRuntime
from shared.config import get_settings
from observability.tracing import init_tracing


# Initialize
settings = get_settings()
init_tracing()
agent_runtime = AgentRuntime()


@functions_framework.http
def handle_query(request: Request):
    """HTTP Cloud Function for RAG queries.

    Request body:
        {
            "query": "What are the termination conditions?",
            "user_id": "user123",
            "doc_ids": ["doc1", "doc2"],  // optional
            "top_k": 5  // optional
        }

    Response:
        {
            "status": "success",
            "data": {
                "answer": "...",
                "citations": [...],
                "confidence": 0.85
            }
        }
    """
    # Parse request
    try:
        request_json = request.get_json(silent=True)
        if not request_json:
            return jsonify({"error": "Invalid JSON"}), 400

        query = request_json.get("query")
        user_id = request_json.get("user_id")

        if not query or not user_id:
            return jsonify({"error": "Missing required fields"}), 400

        # Prepare input
        input_data = {
            "query": query,
            "user_id": user_id,
            "doc_ids": request_json.get("doc_ids"),
            "top_k": request_json.get("top_k", 5),
        }

        # Run agent
        agent = LegalReasoningAgent()
        result = asyncio.run(
            agent_runtime.run(
                agent=agent,
                input_data=input_data,
                user_id=user_id,
            )
        )

        # Return response
        if result.status == "success":
            return jsonify({"status": "success", "data": result.output}), 200
        else:
            return (
                jsonify(
                    {
                        "status": "error",
                        "error": result.error,
                        "metadata": result.metadata,
                    }
                ),
                500,
            )

    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500
