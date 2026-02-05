"""Chunk data models."""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    """Metadata for a document chunk."""

    doc_id: str
    chunk_index: int
    page_number: Optional[int] = None
    section_type: Optional[str] = None  # e.g., "clause", "header", "footer"

    # Layout information
    bbox: Optional[List[float]] = None  # [x1, y1, x2, y2]
    confidence: Optional[float] = None

    # Semantic information
    clause_number: Optional[str] = None
    parent_section: Optional[str] = None

    custom_metadata: Dict[str, Any] = Field(default_factory=dict)


class Chunk(BaseModel):
    """Document chunk model."""

    chunk_id: str = Field(..., description="Unique chunk ID")
    doc_id: str
    text: str = Field(..., description="Chunk text content")
    metadata: ChunkMetadata

    # Embedding
    embedding: Optional[List[float]] = None
    embedding_model: Optional[str] = None

    # Relationships
    prev_chunk_id: Optional[str] = None
    next_chunk_id: Optional[str] = None
