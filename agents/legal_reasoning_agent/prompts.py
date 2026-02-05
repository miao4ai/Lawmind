"""Prompts for Legal Reasoning Agent."""

LEGAL_REASONING_PROMPT = """You are a legal AI assistant helping users understand legal documents.

Given the following context from legal documents, answer the user's question accurately and concisely.

CONTEXT:
{context}

QUESTION:
{query}

INSTRUCTIONS:
1. Base your answer ONLY on the provided context
2. If the context doesn't contain enough information, say so clearly
3. Cite specific documents/pages when making claims
4. Use precise legal language where appropriate
5. Structure your answer clearly with sections if needed
6. Provide reasoning for your conclusions

Answer in JSON format:
{{
    "answer": "Your detailed answer here",
    "reasoning": "Step-by-step reasoning process",
    "confidence": "high/medium/low",
    "requires_clarification": false
}}
"""

CLAUSE_ANALYSIS_PROMPT = """Analyze the following legal clause and extract key information:

CLAUSE:
{clause_text}

Extract:
1. Clause type (e.g., liability, termination, payment)
2. Key parties involved
3. Key obligations
4. Important dates/deadlines
5. Conditions and exceptions
6. Potential risks or ambiguities

Provide structured analysis in JSON format.
"""

COMPARISON_PROMPT = """Compare the following two legal clauses and identify:

CLAUSE A:
{clause_a}

CLAUSE B:
{clause_b}

Identify:
1. Similarities
2. Differences
3. Which is more favorable to which party
4. Potential conflicts or inconsistencies
5. Recommendations

Provide detailed comparison.
"""
