"""
Cloud Function handler for OCR processing.

Triggered by Pub/Sub when document is uploaded.
"""

import functions_framework
from google.cloud import firestore
from google.cloud import pubsub_v1
import base64
import json

import sys
sys.path.insert(0, "/workspace")

from agents.ocr_agent import OCRAgent
from agents.runtime import AgentRuntime
from shared.config import get_settings
from shared.models import DocumentStatus


settings = get_settings()
firestore_client = firestore.Client()
pubsub_publisher = pubsub_v1.PublisherClient()
agent_runtime = AgentRuntime()


@functions_framework.cloud_event
def handle_ocr(cloud_event):
    """Process OCR on uploaded document.

    Pub/Sub message:
        {
            "doc_id": "doc_abc123",
            "user_id": "user123",
            "storage_path": "raw/user123/doc_abc123/file.pdf"
        }
    """
    try:
        # Parse Pub/Sub message
        pubsub_message = base64.b64decode(
            cloud_event.data["message"]["data"]
        ).decode()
        message_data = json.loads(pubsub_message)

        doc_id = message_data["doc_id"]
        user_id = message_data["user_id"]
        storage_path = message_data["storage_path"]

        # Update status
        doc_ref = firestore_client.collection(
            settings.firestore_collection_docs
        ).document(doc_id)
        doc_ref.update({"status": DocumentStatus.OCR_PROCESSING})

        # Run OCR agent
        agent = OCRAgent()
        result = agent_runtime.run(
            agent=agent,
            input_data={
                "doc_id": doc_id,
                "storage_path": storage_path,
            },
            user_id=user_id,
        )

        if result.status == "success":
            # Save OCR results to storage
            ocr_path = f"processed/{doc_id}/ocr_result.json"
            # TODO: Save result.output to Cloud Storage

            # Update document status
            doc_ref.update(
                {
                    "status": DocumentStatus.OCR_COMPLETED,
                    "ocr_result_path": ocr_path,
                    "metadata.page_count": result.output.get(
                        "page_count", 1
                    ),
                }
            )

            # Trigger indexing
            topic_path = pubsub_publisher.topic_path(
                settings.gcp_project_id, settings.pubsub_topic_index
            )
            pubsub_publisher.publish(
                topic_path,
                json.dumps(
                    {
                        "doc_id": doc_id,
                        "user_id": user_id,
                        "ocr_result_path": ocr_path,
                    }
                ).encode(),
            )

        else:
            # Mark as failed
            doc_ref.update(
                {
                    "status": DocumentStatus.OCR_FAILED,
                    "error_message": result.error,
                }
            )

    except Exception as e:
        print(f"Error processing OCR: {e}")
        # Update document status to failed
        if "doc_id" in locals():
            firestore_client.collection(
                settings.firestore_collection_docs
            ).document(doc_id).update(
                {
                    "status": DocumentStatus.OCR_FAILED,
                    "error_message": str(e),
                }
            )
