"""Vector search tool for retrieving relevant chunks."""

from typing import List, Dict, Any, Optional
from shared.config import get_settings
from vector_db.client import get_vector_db_client
from .embeddings import EmbeddingTool


class VectorSearchTool:
    """Tool for semantic search over document chunks."""

    def __init__(self):
        self.settings = get_settings()
        self.vector_db = get_vector_db_client()
        self.embedding_tool = EmbeddingTool()

    async def search(
        self,
        query: str,
        user_id: str,
        doc_ids: Optional[List[str]] = None,
        top_k: int = 5,
        score_threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """Search for relevant chunks.

        Args:
            query: Search query
            user_id: User ID for filtering
            doc_ids: Optional list of document IDs to filter
            top_k: Number of results to return
            score_threshold: Minimum similarity score

        Returns:
            List of relevant chunks with metadata and scores
        """
        # Generate query embedding
        query_embedding = await self.embedding_tool.embed_text(query)

        # Build filters
        filters = {"user_id": user_id}
        if doc_ids:
            filters["doc_id"] = {"$in": doc_ids}

        # Search vector database
        results = await self.vector_db.search(
            collection=self.settings.qdrant_collection,
            query_vector=query_embedding,
            filters=filters,
            limit=top_k,
            score_threshold=score_threshold,
        )

        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append(
                {
                    "chunk_id": result["id"],
                    "text": result["payload"]["text"],
                    "score": result["score"],
                    "metadata": result["payload"]["metadata"],
                }
            )

        return formatted_results

    async def index_chunks(
        self, chunks: List[Dict[str, Any]], user_id: str
    ) -> None:
        """Index chunks into vector database.

        Args:
            chunks: List of chunks to index
            user_id: User ID for the chunks
        """
        # Generate embeddings
        texts = [chunk["text"] for chunk in chunks]
        embeddings = await self.embedding_tool.embed_batch(texts)

        # Prepare points for indexing
        points = []
        for chunk, embedding in zip(chunks, embeddings):
            points.append(
                {
                    "id": chunk["chunk_id"],
                    "vector": embedding,
                    "payload": {
                        "text": chunk["text"],
                        "user_id": user_id,
                        "metadata": chunk["metadata"],
                    },
                }
            )

        # Index into vector DB
        await self.vector_db.upsert(
            collection=self.settings.qdrant_collection, points=points
        )
