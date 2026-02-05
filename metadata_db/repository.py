"""Document repository for Firestore operations."""

from typing import Optional, List
from functools import lru_cache
from datetime import datetime

from google.cloud import firestore

from shared.config import get_settings
from shared.models import Document, DocumentStatus


class DocumentRepository:
    """Repository for document metadata operations."""

    def __init__(self, firestore_client: firestore.Client):
        self.client = firestore_client
        self.settings = get_settings()
        self.collection = self.settings.firestore_collection_docs

    async def create(self, document: Document) -> None:
        """Create a new document record."""
        doc_dict = document.dict()
        self.client.collection(self.collection).document(
            document.doc_id
        ).set(doc_dict)

    async def get(self, doc_id: str) -> Optional[Document]:
        """Get document by ID."""
        doc_ref = self.client.collection(self.collection).document(doc_id)
        doc = doc_ref.get()

        if doc.exists:
            return Document(**doc.to_dict())
        return None

    async def update_status(
        self, doc_id: str, status: DocumentStatus, error: Optional[str] = None
    ) -> None:
        """Update document status."""
        doc_ref = self.client.collection(self.collection).document(doc_id)

        update_data = {
            "status": status.value,
            "updated_at": datetime.utcnow(),
        }

        if error:
            update_data["error_message"] = error

        doc_ref.update(update_data)

    async def list_by_user(
        self, user_id: str, limit: int = 100
    ) -> List[Document]:
        """List documents for a user."""
        docs_ref = (
            self.client.collection(self.collection)
            .where("user_id", "==", user_id)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
        )

        documents = []
        for doc in docs_ref.stream():
            documents.append(Document(**doc.to_dict()))

        return documents

    async def delete(self, doc_id: str) -> None:
        """Delete document."""
        self.client.collection(self.collection).document(doc_id).delete()


@lru_cache()
def get_document_repository() -> DocumentRepository:
    """Get cached document repository instance."""
    client = firestore.Client()
    return DocumentRepository(client)
