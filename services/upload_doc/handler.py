"""
Cloud Function handler for document upload.

Generates signed URL for client-side upload to Cloud Storage.
"""

import functions_framework
from flask import Request, jsonify
from datetime import timedelta
import uuid

from google.cloud import storage
from google.cloud import firestore

import sys
sys.path.insert(0, "/workspace")

from shared.config import get_settings
from shared.models import Document, DocumentMetadata, DocumentStatus


settings = get_settings()
storage_client = storage.Client()
firestore_client = firestore.Client()


@functions_framework.http
def handle_upload(request: Request):
    """Generate signed upload URL.

    Request body:
        {
            "user_id": "user123",
            "filename": "contract.pdf",
            "file_size": 1024000,
            "mime_type": "application/pdf"
        }

    Response:
        {
            "doc_id": "doc_abc123",
            "upload_url": "https://storage.googleapis.com/...",
            "storage_path": "raw/user123/doc_abc123/contract.pdf"
        }
    """
    try:
        request_json = request.get_json(silent=True)
        if not request_json:
            return jsonify({"error": "Invalid JSON"}), 400

        user_id = request_json.get("user_id")
        filename = request_json.get("filename")
        file_size = request_json.get("file_size")
        mime_type = request_json.get("mime_type", "application/pdf")

        if not all([user_id, filename, file_size]):
            return jsonify({"error": "Missing required fields"}), 400

        # Generate document ID
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"

        # Storage path
        storage_path = f"raw/{user_id}/{doc_id}/{filename}"

        # Generate signed URL
        bucket = storage_client.bucket(settings.gcp_storage_bucket)
        blob = bucket.blob(storage_path)

        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=15),
            method="PUT",
            content_type=mime_type,
        )

        # Create document record in Firestore
        document = Document(
            doc_id=doc_id,
            user_id=user_id,
            status=DocumentStatus.UPLOADED,
            metadata=DocumentMetadata(
                filename=filename,
                file_size=file_size,
                mime_type=mime_type,
                upload_time=firestore.SERVER_TIMESTAMP,
            ),
            storage_path=storage_path,
        )

        firestore_client.collection(
            settings.firestore_collection_docs
        ).document(doc_id).set(document.dict())

        return (
            jsonify(
                {
                    "doc_id": doc_id,
                    "upload_url": signed_url,
                    "storage_path": storage_path,
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500
