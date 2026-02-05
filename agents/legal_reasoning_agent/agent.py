"""Legal Reasoning Agent implementation."""

from typing import Dict, Any
from datetime import datetime

from agents.base import Agent, AgentContext, AgentResult, AgentStatus
from agents.registry import register_agent
from tools.vector_search import VectorSearchTool
from tools.llm import LLMTool
from shared.models import Query, QueryResult, Citation
from .prompts import LEGAL_REASONING_PROMPT


@register_agent("legal_reasoning")
class LegalReasoningAgent(Agent):
    """Agent for legal document reasoning and Q&A.

    Input:
        - query: User query
        - user_id: User ID
        - doc_ids: Optional list of document IDs to search
        - top_k: Number of relevant chunks to retrieve

    Output:
        - answer: Generated answer
        - citations: List of citations
        - reasoning: Reasoning trace
        - confidence: Confidence score
    """

    def __init__(self):
        super().__init__(name="legal_reasoning", version="1.0.0")
        self.vector_search = VectorSearchTool()
        self.llm = LLMTool()

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input has required fields."""
        return "query" in input_data and "user_id" in input_data

    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute legal reasoning pipeline."""
        start_time = datetime.utcnow()

        try:
            query_text = context.input_data["query"]
            user_id = context.input_data["user_id"]
            doc_ids = context.input_data.get("doc_ids")
            top_k = context.input_data.get("top_k", 5)

            # Step 1: Retrieve relevant chunks
            search_results = await self.vector_search.search(
                query=query_text,
                user_id=user_id,
                doc_ids=doc_ids,
                top_k=top_k,
            )

            # Step 2: Build context from retrieved chunks
            context_text = self._build_context(search_results)

            # Step 3: Generate answer with reasoning
            prompt = LEGAL_REASONING_PROMPT.format(
                context=context_text, query=query_text
            )

            llm_response = await self.llm.generate(
                prompt=prompt,
                model="gpt-4-turbo-preview",
                temperature=0.3,
            )

            # Step 4: Parse response and build citations
            answer = llm_response["answer"]
            reasoning = llm_response.get("reasoning", "")
            citations = self._build_citations(search_results)

            # Calculate confidence based on retrieval scores
            confidence = self._calculate_confidence(search_results)

            output = {
                "query": query_text,
                "answer": answer,
                "citations": [c.dict() for c in citations],
                "reasoning": reasoning,
                "confidence": confidence,
                "metadata": {
                    "chunks_retrieved": len(search_results),
                    "model": "gpt-4-turbo-preview",
                },
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
                    {"tool": "vector_search", "status": "success"},
                    {"tool": "llm", "status": "success"},
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

    def _build_context(self, search_results: list) -> str:
        """Build context string from search results."""
        context_parts = []
        for i, result in enumerate(search_results, 1):
            context_parts.append(
                f"[Document {i}]\n{result['text']}\n"
                f"Source: {result['metadata']['doc_id']}, "
                f"Page: {result['metadata'].get('page_number', 'N/A')}\n"
            )
        return "\n".join(context_parts)

    def _build_citations(self, search_results: list) -> list:
        """Build citations from search results."""
        citations = []
        for result in search_results:
            citation = Citation(
                doc_id=result["metadata"]["doc_id"],
                chunk_id=result["chunk_id"],
                text=result["text"][:200] + "...",  # Truncate
                page_number=result["metadata"].get("page_number"),
                confidence=result["score"],
            )
            citations.append(citation)
        return citations

    def _calculate_confidence(self, search_results: list) -> float:
        """Calculate overall confidence score."""
        if not search_results:
            return 0.0

        # Average of top-k scores
        scores = [r["score"] for r in search_results]
        return sum(scores) / len(scores)
