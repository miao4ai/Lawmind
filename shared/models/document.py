"""Document data models."""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    """Document processing status."""

    UPLOADED = "uploaded"
    OCR_PROCESSING = "ocr_processing"
    OCR_COMPLETED = "ocr_completed"
    OCR_FAILED = "ocr_failed"
    INDEXING = "indexing"
    INDEXED = "indexed"
    INDEX_FAILED = "index_failed"
    READY = "ready"
    FAILED = "failed"


class DocumentMetadata(BaseModel):
    """Document metadata."""

    filename: str
    file_size: int
    mime_type: str
    upload_time: datetime
    page_count: Optional[int] = None
    language: Optional[str] = None
    custom_metadata: Dict[str, Any] = Field(default_factory=dict)


class Document(BaseModel):
    """Document model."""

    doc_id: str = Field(..., description="Unique document ID")
    user_id: str = Field(..., description="User who uploaded the document")
    status: DocumentStatus = Field(default=DocumentStatus.UPLOADED)
    metadata: DocumentMetadata
    storage_path: str = Field(..., description="Path in Cloud Storage")

    # Processing results
    ocr_result_path: Optional[str] = None
    layout_result_path: Optional[str] = None
    chunks_path: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Error tracking
    error_message: Optional[str] = None
    retry_count: int = 0

    class Config:
        use_enum_values = True
