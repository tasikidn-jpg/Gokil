"""Base classes for the Gokil tool system.

Tools are simple callables described by a JSON schema. The registry exposes them
as OpenAI-style "function" tools so the LLM can invoke them via tool_calls.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


class ToolError(Exception):
    """Raised when a tool fails in a recoverable way (passed back to the LLM)."""


@dataclass
class ToolResult:
    """Structured result returned by a tool."""

    content: str
    is_error: bool = False
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_string(self, max_len: int = 8000) -> str:
        text = self.content if isinstance(self.content, str) else json.dumps(self.content)
        if len(text) > max_len:
            text = text[:max_len] + f"\n... [truncated {len(text) - max_len} chars]"
        return text


@dataclass
class Tool:
    """A tool the agent can call."""

    name: str
    description: str
    parameters: Dict[str, Any]  # JSON schema for arguments
    func: Callable[..., Any]
    danger: bool = False  # mark tools that touch the real filesystem/shell

    def to_openai_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def call(self, arguments: Dict[str, Any]) -> ToolResult:
        try:
            result = self.func(**(arguments or {}))
            if isinstance(result, ToolResult):
                return result
            if isinstance(result, str):
                return ToolResult(content=result)
            return ToolResult(content=json.dumps(result, default=str, ensure_ascii=False))
        except ToolError as e:
            return ToolResult(content=f"ToolError: {e}", is_error=True)
        except Exception as e:  # pragma: no cover - defensive
            return ToolResult(content=f"Unhandled error: {type(e).__name__}: {e}", is_error=True)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> Tool:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool
        return tool

    def add(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        func: Callable[..., Any],
        danger: bool = False,
    ) -> Tool:
        return self.register(Tool(name, description, parameters, func, danger))

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def names(self) -> List[str]:
        return list(self._tools.keys())

    def schemas(self) -> List[Dict[str, Any]]:
        return [t.to_openai_schema() for t in self._tools.values()]

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __iter__(self):
        return iter(self._tools.values())
