"""Gokil CLI — interactive REPL or one-shot mode."""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from . import __version__
from .agent import GokilAgent
from .config import GokilConfig
from .tools import default_registry
from .ui import (
    console,
    print_assistant,
    print_banner,
    print_error,
    print_help,
    print_thought,
    print_tool_call,
    print_tool_list,
    print_tool_result,
    prompt_user,
)


def _build_agent(args: argparse.Namespace) -> GokilAgent:
    config = GokilConfig.from_env(
        model=args.model,
        lang=args.lang,
        base_url=args.base_url,
        max_steps=args.max_steps,
    )
    err = config.validate()
    if err:
        print_error(err)
        sys.exit(2)

    registry = default_registry(enable_dangerous=not args.safe)

    return GokilAgent(
        config=config,
        registry=registry,
        on_thought=print_thought,
        on_tool_call=print_tool_call,
        on_tool_result=print_tool_result,
        on_assistant=print_assistant,
    )


def _handle_command(agent: GokilAgent, line: str) -> bool:
    """Return True if the line was a /command; False if it should be sent to the LLM."""
    if not line.startswith("/"):
        return False
    parts = line.strip().split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if cmd in ("/exit", "/quit", "/q"):
        console.print("[dim]bye! 👋[/]")
        sys.exit(0)
    elif cmd == "/help":
        print_help()
    elif cmd == "/tools":
        print_tool_list(agent.registry)
    elif cmd == "/clear":
        agent.reset()
        console.print("[dim]conversation cleared.[/]")
    elif cmd == "/model":
        if not arg:
            console.print(f"[dim]current model:[/] [bold]{agent.config.model}[/]")
        else:
            agent.set_model(arg)
            console.print(f"[dim]model →[/] [bold]{arg}[/]")
    elif cmd == "/lang":
        if arg not in ("id", "en", "mix"):
            print_error("usage: /lang id|en|mix")
        else:
            agent.set_lang(arg)
            console.print(f"[dim]lang →[/] [bold]{arg}[/]")
    else:
        print_error(f"unknown command: {cmd}. ketik /help")
    return True


def _repl(agent: GokilAgent) -> None:
    print_banner(agent.config.model, agent.config.base_url)
    while True:
        try:
            line = prompt_user()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]bye! 👋[/]")
            return
        if not line.strip():
            continue
        if _handle_command(agent, line):
            continue
        try:
            agent.chat(line)
        except KeyboardInterrupt:
            console.print("[yellow]interrupted.[/]")
        except Exception as e:  # pragma: no cover - defensive
            print_error(f"{type(e).__name__}: {e}")


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        prog="gokil",
        description="Gokil — an autonomous, tool-using AI agent.",
    )
    parser.add_argument("prompt", nargs="*", help="One-shot prompt. Omit to start interactive REPL.")
    parser.add_argument("--model", default=None, help="Override model name.")
    parser.add_argument("--base-url", default=None, help="Override OpenAI-compatible base URL.")
    parser.add_argument("--lang", default=None, choices=["id", "en", "mix"], help="Persona language.")
    parser.add_argument("--max-steps", type=int, default=None, help="Max ReAct steps per turn.")
    parser.add_argument("--safe", action="store_true", help="Disable dangerous tools (shell, write_file, python_exec).")
    parser.add_argument("--version", action="version", version=f"gokil {__version__}")
    args = parser.parse_args(argv)

    agent = _build_agent(args)

    if args.prompt:
        prompt = " ".join(args.prompt)
        print_banner(agent.config.model, agent.config.base_url)
        try:
            agent.chat(prompt)
        except Exception as e:  # pragma: no cover
            print_error(f"{type(e).__name__}: {e}")
            sys.exit(1)
    else:
        _repl(agent)


if __name__ == "__main__":  # pragma: no cover
    main()
