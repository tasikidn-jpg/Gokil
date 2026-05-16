"""Configuration loader for Gokil agent."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover
    pass


@dataclass
class GokilConfig:
    """Runtime configuration for the Gokil agent."""

    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 2048
    max_steps: int = 12
    lang: str = "mix"  # id | en | mix
    workdir: Path = Path(".gokil")

    @classmethod
    def from_env(cls, **overrides) -> "GokilConfig":
        cfg = cls(
            base_url=os.getenv("GOKIL_BASE_URL", cls.base_url),
            api_key=os.getenv("GOKIL_API_KEY", ""),
            model=os.getenv("GOKIL_MODEL", cls.model),
            temperature=float(os.getenv("GOKIL_TEMPERATURE", cls.temperature)),
            max_tokens=int(os.getenv("GOKIL_MAX_TOKENS", cls.max_tokens)),
            max_steps=int(os.getenv("GOKIL_MAX_STEPS", cls.max_steps)),
            lang=os.getenv("GOKIL_LANG", cls.lang),
        )
        for k, v in overrides.items():
            if v is not None and hasattr(cfg, k):
                setattr(cfg, k, v)
        cfg.workdir = Path(cfg.workdir)
        cfg.workdir.mkdir(parents=True, exist_ok=True)
        return cfg

    def validate(self) -> Optional[str]:
        if not self.api_key:
            return (
                "GOKIL_API_KEY belum di-set. Copy `.env.example` ke `.env` dan isi "
                "API key lo (atau export GOKIL_API_KEY)."
            )
        return None
