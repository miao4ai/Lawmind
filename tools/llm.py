"""LLM tool for text generation."""

from typing import Dict, Any, Optional
import json
import openai
from shared.config import get_settings


class LLMTool:
    """Tool for LLM-based text generation."""

    def __init__(self):
        self.settings = get_settings()
        openai.api_key = self.settings.openai_api_key

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        json_mode: bool = True,
    ) -> Dict[str, Any]:
        """Generate text using LLM.

        Args:
            prompt: Input prompt
            model: Model name (defaults to settings)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            json_mode: Whether to expect JSON response

        Returns:
            Generated text or parsed JSON
        """
        model = model or self.settings.default_llm

        response = await openai.ChatCompletion.acreate(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a legal AI assistant. Provide accurate, well-reasoned answers based on the given context.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=(
                {"type": "json_object"} if json_mode else {"type": "text"}
            ),
        )

        content = response["choices"][0]["message"]["content"]

        # Parse JSON if expected
        if json_mode:
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {"error": "Failed to parse JSON", "raw": content}

        return {"text": content}

    async def generate_stream(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ):
        """Generate text with streaming.

        Args:
            prompt: Input prompt
            model: Model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens

        Yields:
            Text chunks as they're generated
        """
        model = model or self.settings.default_llm

        response = await openai.ChatCompletion.acreate(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a legal AI assistant.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        async for chunk in response:
            if chunk["choices"][0]["delta"].get("content"):
                yield chunk["choices"][0]["delta"]["content"]
