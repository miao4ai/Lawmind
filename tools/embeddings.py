"""Embedding tool for generating text embeddings."""

from typing import List
import openai
from shared.config import get_settings


class EmbeddingTool:
    """Tool for generating text embeddings."""

    def __init__(self):
        self.settings = get_settings()
        openai.api_key = self.settings.openai_api_key
        self.model = self.settings.embedding_model

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        response = await openai.Embedding.acreate(
            model=self.model, input=text
        )
        return response["data"][0]["embedding"]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for batch of texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        # OpenAI has limit of 2048 texts per batch
        batch_size = 2048
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = await openai.Embedding.acreate(
                model=self.model, input=batch
            )
            embeddings = [item["embedding"] for item in response["data"]]
            all_embeddings.extend(embeddings)

        return all_embeddings
