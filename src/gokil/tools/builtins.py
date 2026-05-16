"""Built-in tools shipped with Gokil.

Includes: web_search, fetch_url, shell_exec, read_file, write_file, list_dir,
python_exec, calculator, datetime_now, remember, recall, forget.
"""

from __future__ import annotations

import ast
import datetime as _dt
import json
import operator as op
import os
import shlex
import subprocess
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import ToolError, ToolRegistry, ToolResult

# ---------- helpers ----------

_MEMORY_FILE = Path(".gokil") / "memory.json"


def _load_memory() -> Dict[str, str]:
    if _MEMORY_FILE.exists():
        try:
            return json.loads(_MEMORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_memory(mem: Dict[str, str]) -> None:
    _MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    _MEMORY_FILE.write_text(json.dumps(mem, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------- web ----------


def _tool_web_search(query: str, max_results: int = 5) -> ToolResult:
    try:
        from duckduckgo_search import DDGS
    except ImportError as e:
        raise ToolError(f"duckduckgo_search not installed: {e}")

    results: List[Dict[str, Any]] = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append(
                {
                    "title": r.get("title"),
                    "url": r.get("href") or r.get("url"),
                    "snippet": r.get("body"),
                }
            )
    if not results:
        return ToolResult(content="No results.")
    return ToolResult(content=json.dumps(results, ensure_ascii=False, indent=2))


def _tool_fetch_url(url: str, max_chars: int = 6000) -> ToolResult:
    import httpx
    from bs4 import BeautifulSoup

    try:
        with httpx.Client(follow_redirects=True, timeout=20.0) as client:
            resp = client.get(url, headers={"User-Agent": "GokilAgent/0.1"})
            resp.raise_for_status()
            ctype = resp.headers.get("content-type", "")
            if "html" in ctype:
                soup = BeautifulSoup(resp.text, "html.parser")
                for tag in soup(["script", "style", "noscript"]):
                    tag.decompose()
                text = "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())
            else:
                text = resp.text
    except Exception as e:
        raise ToolError(f"fetch failed: {e}")

    if len(text) > max_chars:
        text = text[:max_chars] + f"\n... [truncated {len(text) - max_chars} chars]"
    return ToolResult(content=text, meta={"url": url, "status": resp.status_code})


# ---------- shell + files ----------


def _tool_shell_exec(command: str, timeout: int = 30) -> ToolResult:
    try:
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise ToolError(f"command timed out after {timeout}s")
    out = (proc.stdout or "") + (("\n[stderr]\n" + proc.stderr) if proc.stderr else "")
    return ToolResult(
        content=out.strip() or "(no output)",
        is_error=proc.returncode != 0,
        meta={"returncode": proc.returncode, "command": command},
    )


def _tool_read_file(path: str, max_chars: int = 20000) -> ToolResult:
    p = Path(path)
    if not p.exists():
        raise ToolError(f"file not found: {path}")
    if not p.is_file():
        raise ToolError(f"not a file: {path}")
    text = p.read_text(encoding="utf-8", errors="replace")
    if len(text) > max_chars:
        text = text[:max_chars] + f"\n... [truncated {len(text) - max_chars} chars]"
    return ToolResult(content=text)


def _tool_write_file(path: str, content: str, append: bool = False) -> ToolResult:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with p.open(mode, encoding="utf-8") as f:
        f.write(content)
    return ToolResult(content=f"OK: wrote {len(content)} chars to {path}")


def _tool_list_dir(path: str = ".", show_hidden: bool = False) -> ToolResult:
    p = Path(path)
    if not p.exists():
        raise ToolError(f"path not found: {path}")
    if not p.is_dir():
        raise ToolError(f"not a directory: {path}")
    entries = []
    for entry in sorted(p.iterdir()):
        if not show_hidden and entry.name.startswith("."):
            continue
        kind = "dir" if entry.is_dir() else "file"
        size = entry.stat().st_size if entry.is_file() else "-"
        entries.append(f"{kind:4}  {size:>10}  {entry.name}")
    return ToolResult(content="\n".join(entries) or "(empty)")


# ---------- python ----------


def _tool_python_exec(code: str, timeout: int = 15) -> ToolResult:
    """Execute a short Python snippet in a subprocess and return stdout/stderr."""
    wrapped = textwrap.dedent(code)
    try:
        proc = subprocess.run(
            ["python", "-c", wrapped],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise ToolError(f"python_exec timed out after {timeout}s")
    out = (proc.stdout or "") + (("\n[stderr]\n" + proc.stderr) if proc.stderr else "")
    return ToolResult(
        content=out.strip() or "(no output)",
        is_error=proc.returncode != 0,
        meta={"returncode": proc.returncode},
    )


# ---------- calculator (safe AST) ----------

_ALLOWED_OPS = {
    ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv, ast.Mod: op.mod, ast.Pow: op.pow,
    ast.USub: op.neg, ast.UAdd: op.pos,
}


def _safe_eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_safe_eval(node.operand))
    raise ToolError("unsupported expression")


def _tool_calculator(expression: str) -> ToolResult:
    try:
        tree = ast.parse(expression, mode="eval")
        value = _safe_eval(tree.body)
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"invalid expression: {e}")
    return ToolResult(content=str(value))


# ---------- datetime ----------


def _tool_datetime_now(tz_offset_hours: float = 0.0) -> ToolResult:
    tz = _dt.timezone(_dt.timedelta(hours=tz_offset_hours))
    now = _dt.datetime.now(tz)
    return ToolResult(
        content=json.dumps(
            {
                "iso": now.isoformat(),
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "weekday": now.strftime("%A"),
                "tz_offset_hours": tz_offset_hours,
            },
            ensure_ascii=False,
        )
    )


# ---------- memory ----------


def _tool_remember(key: str, value: str) -> ToolResult:
    mem = _load_memory()
    mem[key] = value
    _save_memory(mem)
    return ToolResult(content=f"OK: remembered '{key}'")


def _tool_recall(key: Optional[str] = None) -> ToolResult:
    mem = _load_memory()
    if key:
        if key not in mem:
            return ToolResult(content=f"(no note for '{key}')")
        return ToolResult(content=mem[key])
    if not mem:
        return ToolResult(content="(memory is empty)")
    return ToolResult(content=json.dumps(mem, ensure_ascii=False, indent=2))


def _tool_forget(key: str) -> ToolResult:
    mem = _load_memory()
    if key not in mem:
        return ToolResult(content=f"(no note for '{key}')")
    del mem[key]
    _save_memory(mem)
    return ToolResult(content=f"OK: forgot '{key}'")


# ---------- registry ----------


def default_registry(enable_dangerous: bool = True) -> ToolRegistry:
    """Return a registry populated with the built-in tools.

    `enable_dangerous=False` disables shell_exec, write_file, and python_exec.
    """
    r = ToolRegistry()

    r.add(
        "web_search",
        "Search the web via DuckDuckGo. Returns top results with title, url, snippet.",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query."},
                "max_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 15},
            },
            "required": ["query"],
        },
        _tool_web_search,
    )

    r.add(
        "fetch_url",
        "Fetch a URL and return cleaned text content. Use after web_search to read pages.",
        {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "max_chars": {"type": "integer", "default": 6000},
            },
            "required": ["url"],
        },
        _tool_fetch_url,
    )

    r.add(
        "read_file",
        "Read a UTF-8 text file from the local workspace.",
        {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "max_chars": {"type": "integer", "default": 20000},
            },
            "required": ["path"],
        },
        _tool_read_file,
    )

    r.add(
        "list_dir",
        "List files in a directory (non-recursive).",
        {
            "type": "object",
            "properties": {
                "path": {"type": "string", "default": "."},
                "show_hidden": {"type": "boolean", "default": False},
            },
        },
        _tool_list_dir,
    )

    r.add(
        "calculator",
        "Evaluate an arithmetic expression safely (supports + - * / // % **).",
        {
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"],
        },
        _tool_calculator,
    )

    r.add(
        "datetime_now",
        "Get the current date/time. Optional timezone offset in hours.",
        {
            "type": "object",
            "properties": {"tz_offset_hours": {"type": "number", "default": 0}},
        },
        _tool_datetime_now,
    )

    r.add(
        "remember",
        "Save a note to persistent memory under a key (overwrites existing).",
        {
            "type": "object",
            "properties": {"key": {"type": "string"}, "value": {"type": "string"}},
            "required": ["key", "value"],
        },
        _tool_remember,
    )

    r.add(
        "recall",
        "Retrieve a saved note by key, or list all if no key is given.",
        {
            "type": "object",
            "properties": {"key": {"type": "string"}},
        },
        _tool_recall,
    )

    r.add(
        "forget",
        "Delete a saved note by key.",
        {
            "type": "object",
            "properties": {"key": {"type": "string"}},
            "required": ["key"],
        },
        _tool_forget,
    )

    if enable_dangerous:
        r.add(
            "shell_exec",
            "Run a shell command and return its stdout/stderr. Use carefully.",
            {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "timeout": {"type": "integer", "default": 30},
                },
                "required": ["command"],
            },
            _tool_shell_exec,
            danger=True,
        )

        r.add(
            "write_file",
            "Write text to a file (creates parents). Set append=true to append.",
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                    "append": {"type": "boolean", "default": False},
                },
                "required": ["path", "content"],
            },
            _tool_write_file,
            danger=True,
        )

        r.add(
            "python_exec",
            "Execute a short Python snippet in a fresh subprocess and return its output.",
            {
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "timeout": {"type": "integer", "default": 15},
                },
                "required": ["code"],
            },
            _tool_python_exec,
            danger=True,
        )

    return r
