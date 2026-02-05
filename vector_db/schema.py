"""Vector database schemas."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class VectorPoint(BaseModel):
    """A vector point to be stored in the database."""

    id: str
    vector: List[float]
    payload: Dict[str, Any]


class SearchFilter(BaseModel):
    """Filter for vector search."""

    field: str
    operator: str  # eq, in, gt, lt, etc.
    value: Any


class SearchResult(BaseModel):
    """Result from vector search."""

    id: str
    score: float
    payload: Dict[str, Any]
