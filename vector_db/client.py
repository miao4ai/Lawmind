"""Vector database client implementation."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter

from shared.config import get_settings
from .schema import VectorPoint, SearchFilter, SearchResult


class VectorDBClient(ABC):
    """Abstract base class for vector database clients."""

    @abstractmethod
    async def search(
        self,
        collection: str,
        query_vector: List[float],
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        score_threshold: float = 0.0,
    ) -> List[SearchResult]:
        """Search for similar vectors."""
        pass

    @abstractmethod
    async def upsert(
        self, collection: str, points: List[VectorPoint]
    ) -> None:
        """Insert or update vectors."""
        pass

    @abstractmethod
    async def delete(
        self, collection: str, point_ids: List[str]
    ) -> None:
        """Delete vectors by IDs."""
        pass

    @abstractmethod
    async def create_collection(
        self, collection: str, vector_size: int, distance: str = "cosine"
    ) -> None:
        """Create a new collection."""
        pass


class QdrantVectorDB(VectorDBClient):
    """Qdrant vector database implementation."""

    def __init__(self, url: str, api_key: Optional[str] = None):
        self.client = QdrantClient(url=url, api_key=api_key)

    async def search(
        self,
        collection: str,
        query_vector: List[float],
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        score_threshold: float = 0.0,
    ) -> List[SearchResult]:
        """Search for similar vectors in Qdrant."""

        # Convert filters to Qdrant format
        qdrant_filter = None
        if filters:
            # Simple implementation - can be extended
            must_conditions = []
            for key, value in filters.items():
                if isinstance(value, dict) and "$in" in value:
                    # Handle $in operator
                    must_conditions.append(
                        {"key": key, "match": {"any": value["$in"]}}
                    )
                else:
                    must_conditions.append(
                        {"key": key, "match": {"value": value}}
                    )

            if must_conditions:
                qdrant_filter = Filter(must=must_conditions)

        # Search
        results = self.client.search(
            collection_name=collection,
            query_vector=query_vector,
            query_filter=qdrant_filter,
            limit=limit,
            score_threshold=score_threshold,
        )

        # Convert to SearchResult
        search_results = []
        for result in results:
            search_results.append(
                SearchResult(
                    id=result.id,
                    score=result.score,
                    payload=result.payload,
                )
            )

        return search_results

    async def upsert(
        self, collection: str, points: List[VectorPoint]
    ) -> None:
        """Upsert points into Qdrant."""

        qdrant_points = [
            PointStruct(
                id=point.id, vector=point.vector, payload=point.payload
            )
            for point in points
        ]

        self.client.upsert(
            collection_name=collection, points=qdrant_points
        )

    async def delete(
        self, collection: str, point_ids: List[str]
    ) -> None:
        """Delete points from Qdrant."""
        self.client.delete(collection_name=collection, points_selector=point_ids)

    async def create_collection(
        self, collection: str, vector_size: int, distance: str = "cosine"
    ) -> None:
        """Create collection in Qdrant."""

        distance_map = {
            "cosine": Distance.COSINE,
            "euclidean": Distance.EUCLID,
            "dot": Distance.DOT,
        }

        self.client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(
                size=vector_size, distance=distance_map.get(distance, Distance.COSINE)
            ),
        )


@lru_cache()
def get_vector_db_client() -> VectorDBClient:
    """Get cached vector DB client instance."""
    settings = get_settings()

    if settings.vector_db_type == "qdrant":
        return QdrantVectorDB(
            url=settings.qdrant_url, api_key=settings.qdrant_api_key
        )
    else:
        raise ValueError(f"Unsupported vector DB type: {settings.vector_db_type}")
