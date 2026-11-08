from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from pathlib import Path

from dotenv import load_dotenv

from arl import prompts
from arl.errors import ConfigurationError

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    supplier: str = "ollama"
    model: str = "qwen3:1.7b"
    ollama_url: str = "http://localhost:11434"
    max_step: int = 6
    instruction: str = prompts.DEFAULT_VERSION
    context_budget: int = 6000
    notes_dir: Path = ROOT / "data" / "notes"
    traces_dir: Path = Path("traces")
    api_key: str | None = field(default=None, repr=False)  # secret : jamais dans repr()

    def description(self) -> dict:
        """Version affichable : le secret est masqué."""
        d = {f.name: str(getattr(self, f.name)) for f in fields(self) if f.name != "api_key"}
        d["api_key"] = "définie" if self.api_key else "absente"
        return d


def _integer(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        raise ConfigurationError(f"{name} doit être un entier (reçu : {raw!r})") from None


def load() -> Settings:
    load_dotenv(ROOT / ".env")  # n'écrase pas les variables déjà définies dans le shell
    instruction = os.getenv("ARL_CONSIGNE", prompts.DEFAULT_VERSION)
    if instruction not in prompts.VERSIONS:
        raise ConfigurationError(f"ARL_CONSIGNE inconnue : {instruction} ({', '.join(prompts.VERSIONS)})")
    notes_dir = Path(os.getenv("ARL_DOSSIER_NOTES", ROOT / "data" / "notes")).resolve()
    if not notes_dir.is_dir():
        raise ConfigurationError(f"dossier de notes introuvable : {notes_dir}")
    return Settings(
        supplier=os.getenv("ARL_FOURNISSEUR", "ollama"),
        model=os.getenv("ARL_MODELE", "qwen3:1.7b"),
        ollama_url=os.getenv("ARL_OLLAMA_URL", "http://localhost:11434"),
        max_step=_integer("ARL_MAX_ETAPES", 6),
        instruction=instruction,
        context_budget=_integer("ARL_BUDGET_CONTEXTE", 6000),
        notes_dir=notes_dir,
        traces_dir=Path(os.getenv("ARL_TRACES", "traces")),
        api_key=os.getenv("ARL_CLE_API"),
    )
