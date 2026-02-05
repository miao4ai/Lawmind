"""Query and result models."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Citation(BaseModel):
    """Citation for a piece of information."""

    doc_id: str
    chunk_id: str
    text: str
    page_number: Optional[int] = None
    confidence: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class QueryResult(BaseModel):
    """Result of a query."""

    query: str
    answer: str
    citations: List[Citation] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Query(BaseModel):
    """Query model."""

    query_text: str = Field(..., min_length=1)
    user_id: str
    doc_ids: Optional[List[str]] = None  # Limit search to specific documents
    filters: Dict[str, Any] = Field(default_factory=dict)
    top_k: int = Field(default=5, ge=1, le=20)
