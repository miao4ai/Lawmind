"""Vector database abstraction layer."""

from .client import VectorDBClient, get_vector_db_client
from .schema import VectorPoint, SearchFilter, SearchResult

__all__ = [
    "VectorDBClient",
    "get_vector_db_client",
    "VectorPoint",
    "SearchFilter",
    "SearchResult",
]
