"""OCR Agent implementation."""

from typing import Dict, Any
from datetime import datetime

from agents.base import Agent, AgentContext, AgentResult, AgentStatus
from agents.registry import register_agent
from tools.ocr import OCRTool
from tools.layout import LayoutAnalysisTool
from shared.models import Document, DocumentStatus


@register_agent("ocr")
class OCRAgent(Agent):
    """Agent for OCR and layout analysis.

    Input:
        - doc_id: Document ID
        - storage_path: Path to document in Cloud Storage

    Output:
        - ocr_text: Extracted text
        - layout: Layout analysis result
        - page_count: Number of pages
    """

    def __init__(self):
        super().__init__(name="ocr", version="1.0.0")
        self.ocr_tool = OCRTool()
        self.layout_tool = LayoutAnalysisTool()

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input has required fields."""
        return "doc_id" in input_data and "storage_path" in input_data

    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute OCR and layout analysis."""
        start_time = datetime.utcnow()

        try:
            doc_id = context.input_data["doc_id"]
            storage_path = context.input_data["storage_path"]

            # Step 1: OCR extraction
            ocr_result = await self.ocr_tool.extract_text(storage_path)

            # Step 2: Layout analysis
            layout_result = await self.layout_tool.analyze(
                storage_path, ocr_result
            )

            # Prepare output
            output = {
                "doc_id": doc_id,
                "ocr_text": ocr_result["text"],
                "layout": layout_result,
                "page_count": ocr_result.get("page_count", 1),
                "language": ocr_result.get("language", "en"),
            }

            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds() * 1000

            return AgentResult(
                status=AgentStatus.SUCCESS,
                output=output,
                start_time=start_time,
                end_time=end_time,
                duration_ms=duration,
                tool_calls=[
                    {"tool": "ocr", "status": "success"},
                    {"tool": "layout", "status": "success"},
                ],
            )

        except Exception as e:
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds() * 1000

            return AgentResult(
                status=AgentStatus.FAILED,
                error=str(e),
                start_time=start_time,
                end_time=end_time,
                duration_ms=duration,
            )
