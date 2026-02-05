"""Metadata database (Firestore) abstraction."""

from .repository import DocumentRepository, get_document_repository

__all__ = ["DocumentRepository", "get_document_repository"]
