"""Thin wrapper around an OpenAI-compatible Chat Completions endpoint.

Supports any provider that speaks the OpenAI API: OpenAI, OpenRouter, Groq,
Together, Ollama (`/v1`), LM Studio, vLLM, etc.
"""

from __future__ import annotations

from typing import Any, Iterable, List, Optional

from openai import OpenAI

from .config import GokilConfig


class LLMClient:
    def __init__(self, config: GokilConfig):
        self.config = config
        self.client = OpenAI(api_key=config.api_key, base_url=config.base_url)

    def chat(
        self,
        messages: List[dict],
        tools: Optional[List[dict]] = None,
        stream: bool = False,
        **kwargs: Any,
    ):
        """Call chat.completions. Returns the full message or a stream iterator."""
        params = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"
        params.update(kwargs)

        if stream:
            params["stream"] = True
            return self.client.chat.completions.create(**params)

        resp = self.client.chat.completions.create(**params)
        return resp.choices[0].message

    def stream_text(self, messages: List[dict], **kwargs: Any) -> Iterable[str]:
        """Yield text chunks (no tool calls) — handy for plain Q&A streaming."""
        for chunk in self.chat(messages, stream=True, **kwargs):
            delta = chunk.choices[0].delta
            content = getattr(delta, "content", None)
            if content:
                yield content
