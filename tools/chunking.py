"""Chunking tool for splitting documents into semantic chunks."""

from typing import List, Dict, Any
import re


class ChunkingTool:
    """Tool for clause-aware document chunking.

    Splits legal documents while respecting clause boundaries.
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        respect_clauses: bool = True,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.respect_clauses = respect_clauses

    def chunk_document(
        self, text: str, metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Chunk document into semantic pieces.

        Args:
            text: Full document text
            metadata: Document metadata

        Returns:
            List of chunks with metadata
        """
        if self.respect_clauses:
            return self._chunk_by_clauses(text, metadata or {})
        else:
            return self._chunk_by_size(text, metadata or {})

    def _chunk_by_clauses(
        self, text: str, metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Chunk by legal clauses."""
        chunks = []

        # Detect clause boundaries
        # Common patterns: "1.", "1.1", "Article 1", "Section 1", etc.
        clause_pattern = r"(\n\s*(?:\d+\.(?:\d+\.?)*|\(?[a-z]\)|Article\s+\d+|Section\s+\d+))"

        parts = re.split(clause_pattern, text)

        current_chunk = ""
        chunk_index = 0

        for i, part in enumerate(parts):
            # Check if adding this part exceeds chunk size
            if len(current_chunk) + len(part) > self.chunk_size:
                if current_chunk:
                    chunks.append(
                        {
                            "chunk_id": f"{metadata.get('doc_id', 'unknown')}_{chunk_index}",
                            "text": current_chunk.strip(),
                            "chunk_index": chunk_index,
                            "metadata": metadata,
                        }
                    )
                    chunk_index += 1

                current_chunk = part
            else:
                current_chunk += part

        # Add final chunk
        if current_chunk.strip():
            chunks.append(
                {
                    "chunk_id": f"{metadata.get('doc_id', 'unknown')}_{chunk_index}",
                    "text": current_chunk.strip(),
                    "chunk_index": chunk_index,
                    "metadata": metadata,
                }
            )

        return chunks

    def _chunk_by_size(
        self, text: str, metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Simple size-based chunking with overlap."""
        chunks = []
        chunk_index = 0
        start = 0

        while start < len(text):
            end = start + self.chunk_size

            # Find nearest sentence boundary
            if end < len(text):
                # Look for period, newline, or question mark
                boundary = max(
                    text.rfind(".", start, end),
                    text.rfind("\n", start, end),
                    text.rfind("?", start, end),
                )
                if boundary != -1:
                    end = boundary + 1

            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append(
                    {
                        "chunk_id": f"{metadata.get('doc_id', 'unknown')}_{chunk_index}",
                        "text": chunk_text,
                        "chunk_index": chunk_index,
                        "metadata": metadata,
                    }
                )
                chunk_index += 1

            # Move start with overlap
            start = end - self.chunk_overlap

        return chunks
