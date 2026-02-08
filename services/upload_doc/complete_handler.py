"""
Cloud Function handler for completing document upload.

Called by the frontend after the file is uploaded to GCS via signed URL.
Triggers OCR processing by publishing to Pub/Sub.
"""

import functions_framework
from flask import Request, jsonify
import json

from google.cloud import firestore
from google.cloud import pubsub_v1

import sys
sys.path.insert(0, "/workspace")

from shared.config import get_settings
from shared.models import DocumentStatus


settings = get_settings()
firestore_client = firestore.Client()
pubsub_publisher = pubsub_v1.PublisherClient()


@functions_framework.http
def handle_complete(request: Request):
    """Complete upload and trigger OCR processing.

    URL pattern: POST /complete/{doc_id}
    The doc_id is extracted from the URL path.

    Response:
        {
            "status": "processing",
            "doc_id": "doc_abc123"
        }
    """
    try:
        # Extract doc_id from path
        path = request.path.rstrip("/")
        doc_id = path.split("/")[-1]

        if not doc_id or not doc_id.startswith("doc_"):
            return jsonify({"error": "Invalid document ID"}), 400

        # Look up document in Firestore
        doc_ref = firestore_client.collection(
            settings.firestore_collection_docs
        ).document(doc_id)
        doc_snapshot = doc_ref.get()

        if not doc_snapshot.exists:
            return jsonify({"error": f"Document {doc_id} not found"}), 404

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

        # Update status to OCR_PROCESSING
        doc_ref.update({"status": DocumentStatus.OCR_PROCESSING.value})

        return jsonify({"status": "processing", "doc_id": doc_id}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
