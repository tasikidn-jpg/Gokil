"""GokilAgent — a ReAct-style tool-using agent."""

from __future__ import annotations

import json
from typing import Callable, Dict, List, Optional

from .config import GokilConfig
from .llm import LLMClient
from .persona import system_prompt
from .tools import ToolRegistry, default_registry


class GokilAgent:
    """Tool-using agent that loops: reason → call tools → observe → respond."""

    def __init__(
        self,
        config: Optional[GokilConfig] = None,
        registry: Optional[ToolRegistry] = None,
        on_thought: Optional[Callable[[str], None]] = None,
        on_tool_call: Optional[Callable[[str, dict], None]] = None,
        on_tool_result: Optional[Callable[[str, str, bool], None]] = None,
        on_assistant: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.config = config or GokilConfig.from_env()
        self.registry = registry or default_registry()
        self.llm = LLMClient(self.config)
        self.history: List[Dict] = []
        self.mode: str = "calm"  # "calm" | "wild"
        self._base_temperature: float = self.config.temperature

        self.on_thought = on_thought or (lambda s: None)
        self.on_tool_call = on_tool_call or (lambda n, a: None)
        self.on_tool_result = on_tool_result or (lambda n, c, e: None)
        self.on_assistant = on_assistant or (lambda s: None)

        self._init_system()

    # ---------- conversation management ----------

    def _tools_summary(self) -> str:
        return "\n".join(f"- `{t.name}` — {t.description}" for t in self.registry)

    def _init_system(self) -> None:
        self.history = [
            {
                "role": "system",
                "content": system_prompt(
                    self.config.lang, self._tools_summary(), mode=self.mode
                ),
            }
        ]

    def reset(self) -> None:
        self._init_system()

    def set_lang(self, lang: str) -> None:
        self.config.lang = lang
        self._refresh_system_prompt()

    def set_model(self, model: str) -> None:
        self.config.model = model

    def set_mode(self, mode: str) -> None:
        """Switch between 'calm' (default) and 'wild' (divergent thinking on)."""
        if mode not in ("calm", "wild"):
            raise ValueError("mode must be 'calm' or 'wild'")
        self.mode = mode
        # Bump temperature in wild mode to encourage divergent sampling.
        if mode == "wild":
            self.config.temperature = min(1.2, self._base_temperature + 0.4)
        else:
            self.config.temperature = self._base_temperature
        self._refresh_system_prompt()

    def _refresh_system_prompt(self) -> None:
        """Rebuild the system prompt while keeping conversation history intact."""
        rest = [m for m in self.history if m.get("role") != "system"]
        self._init_system()
        self.history.extend(rest)

    # ---------- the ReAct loop ----------

    def chat(self, user_input: str) -> str:
        """Send a user message and run the tool-using loop until a final reply."""
        self.history.append({"role": "user", "content": user_input})
        tools_schema = self.registry.schemas()

        for _ in range(self.config.max_steps):
            message = self.llm.chat(self.history, tools=tools_schema)

            assistant_msg: Dict = {"role": "assistant", "content": message.content or ""}
            tool_calls = getattr(message, "tool_calls", None)

            if tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ]

            self.history.append(assistant_msg)

            # surface thinking text (some models put it in `content` alongside tool calls)
            if message.content:
                if tool_calls:
                    self.on_thought(message.content)
                else:
                    self.on_assistant(message.content)

            if not tool_calls:
                return message.content or ""

            # execute each tool call and append a `tool` message
            for tc in tool_calls:
                name = tc.function.name
                raw_args = tc.function.arguments or "{}"
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                except json.JSONDecodeError:
                    args = {}

                self.on_tool_call(name, args)

                tool = self.registry.get(name)
                if tool is None:
                    result_text = f"ToolError: unknown tool '{name}'"
                    is_error = True
                else:
                    result = tool.call(args)
                    result_text = result.to_string()
                    is_error = result.is_error

                self.on_tool_result(name, result_text, is_error)

                self.history.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": name,
                        "content": result_text,
                    }
                )

        # if we hit max steps, ask for a final summary
        self.history.append(
            {
                "role": "user",
                "content": (
                    "Lo udah pakai banyak step. Berikan jawaban final ringkas berdasarkan "
                    "info yang udah dikumpulin, tanpa manggil tool lagi."
                ),
            }
        )
        message = self.llm.chat(self.history)
        final = message.content or "(no response)"
        self.history.append({"role": "assistant", "content": final})
        self.on_assistant(final)
        return final
