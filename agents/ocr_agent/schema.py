"""Input/output schemas for OCR Agent."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class OCRAgentInput(BaseModel):
    """Input schema for OCR Agent."""

    doc_id: str = Field(..., description="Document ID")
    storage_path: str = Field(..., description="Path in Cloud Storage")
    language: Optional[str] = Field(
        default="en", description="Expected language"
    )
    extract_layout: bool = Field(
        default=True, description="Whether to extract layout"
    )


class LayoutBlock(BaseModel):
    """Layout block (paragraph, header, table, etc.)."""

    block_type: str  # text, header, footer, table, image
    text: str
    bbox: List[float]  # [x1, y1, x2, y2]
    confidence: float
    page_number: int


class OCRAgentOutput(BaseModel):
    """Output schema for OCR Agent."""

    doc_id: str
    ocr_text: str = Field(..., description="Full extracted text")
    layout: List[LayoutBlock] = Field(
        default_factory=list, description="Layout blocks"
    )
    page_count: int
    language: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
