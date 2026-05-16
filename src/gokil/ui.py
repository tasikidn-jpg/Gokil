"""Rich-based terminal UI helpers for Gokil."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

console = Console()


BANNER = r"""
   ______      __    _ __
  / ____/___  / /__ (_) /
 / / __/ __ \/ //_// / / 
/ /_/ / /_/ / ,<  / / /  
\____/\____/_/|_|/_/_/   
"""


def print_banner(model: str, base_url: str) -> None:
    console.print(Text(BANNER, style="bold magenta"))
    console.print(
        Panel.fit(
            Text.assemble(
                ("AI Agent yang gokil — siap bantuin lo. ", "italic"),
                ("Ketik ", "dim"), ("/help", "bold cyan"), (" buat liat command.\n", "dim"),
                ("Model: ", "dim"), (model, "bold green"),
                ("   Endpoint: ", "dim"), (base_url, "green"),
            ),
            border_style="magenta",
        )
    )


def print_help() -> None:
    body = (
        "[bold cyan]/help[/]    — show this help\n"
        "[bold cyan]/tools[/]   — list available tools\n"
        "[bold cyan]/clear[/]   — clear conversation history\n"
        "[bold cyan]/model[/] [italic]<name>[/]  — switch model\n"
        "[bold cyan]/lang[/] [italic]id|en|mix[/] — switch persona language\n"
        "[bold magenta]/wild[/]    — enable wild mode (divergent thinking, temp boost)\n"
        "[bold cyan]/calm[/]    — back to calm mode (balanced explorer)\n"
        "[bold cyan]/mode[/]    — show current mode\n"
        "[bold cyan]/exit[/]    — quit"
    )
    console.print(Panel(body, title="Commands", border_style="cyan"))


def print_tool_list(registry) -> None:
    lines = []
    for t in registry:
        flag = " [red](danger)[/]" if t.danger else ""
        lines.append(f"[bold yellow]{t.name}[/]{flag}\n  [dim]{t.description}[/]")
    console.print(Panel("\n\n".join(lines), title="Tools", border_style="yellow"))


def print_thought(text: str) -> None:
    if not text.strip():
        return
    console.print(Panel(Markdown(text), title="[dim]thinking[/]", border_style="dim"))


def print_tool_call(name: str, args: Dict[str, Any]) -> None:
    pretty = json.dumps(args, ensure_ascii=False, indent=2) if args else "{}"
    console.print(
        Panel(
            Syntax(pretty, "json", theme="ansi_dark", word_wrap=True),
            title=f"[bold cyan]→ tool[/] [bold]{name}[/]",
            border_style="cyan",
        )
    )


def print_tool_result(name: str, content: str, is_error: bool = False) -> None:
    style = "red" if is_error else "green"
    title = f"[bold {style}]← {name}[/]" + (" [red](error)[/]" if is_error else "")
    console.print(Panel(content, title=title, border_style=style))


def print_assistant(text: str) -> None:
    if not text.strip():
        return
    console.print(Panel(Markdown(text), title="[bold magenta]Gokil[/]", border_style="magenta"))


def print_error(msg: str) -> None:
    console.print(Panel(msg, title="[bold red]error[/]", border_style="red"))


def prompt_user() -> str:
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.formatted_text import HTML

        session = getattr(prompt_user, "_session", None)
        if session is None:
            session = PromptSession()
            prompt_user._session = session  # type: ignore[attr-defined]
        return session.prompt(HTML("<ansicyan><b>you ▸ </b></ansicyan>"))
    except (ImportError, Exception):
        return console.input("[bold cyan]you ▸ [/] ")
