"""Filesystem configuration without global working-directory changes."""

import os
import math
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


def load_environment(project_root: Path | None = None) -> Path:
    """Read the selected project's .env without replacing shell variables."""
    root = Path(project_root or os.environ.get("EMPORIO_PROJECT_ROOT", ".")).expanduser().resolve()
    load_dotenv(root / ".env", override=False)
    return root


@dataclass(frozen=True)
class Settings:
    raw_dir: Path
    database_path: Path
    policies_path: Path
    project_root: Path | None = None

    @classmethod
    def from_environment(cls, project_root: Path | None = None) -> "Settings":
        root = Path(
            project_root if project_root is not None
            else os.environ.get("EMPORIO_PROJECT_ROOT", ".")
        ).expanduser().resolve()
        load_environment(root)

        def resolve_path(variable: str, default: str) -> Path:
            path = Path(os.environ.get(variable, default)).expanduser()
            return (root / path).resolve() if not path.is_absolute() else path.resolve()

        return cls(
            raw_dir=resolve_path("EMPORIO_RAW_DIR", "data/raw"),
            database_path=resolve_path("EMPORIO_DATABASE_PATH", "data/processed/emporio.sqlite3"),
            policies_path=resolve_path("EMPORIO_POLICIES_PATH", "data/raw/políticas_da_loja.pdf"),
            project_root=root,
        )


@dataclass(frozen=True)
class ModelSettings:
    api_key: str = field(default="", repr=False)
    model: str = "gemini-3.8-flash"
    language: str = "pt-BR"
    timeout: float = 45.0
    max_tool_rounds: int = 6
    max_turns: int = 20

    @classmethod
    def from_environment(cls, project_root: Path | None = None) -> "ModelSettings":
        load_environment(project_root)
        try:
            timeout = float(os.environ.get("EMPORIO_MODEL_TIMEOUT", "45"))
            rounds = int(os.environ.get("EMPORIO_MAX_TOOL_ROUNDS", "6"))
            turns = int(os.environ.get("EMPORIO_MAX_TURNS", "20"))
        except ValueError as error:
            raise ValueError("Model timeout and session limits must be numeric.") from error
        language = os.environ.get("EMPORIO_CHAT_LANGUAGE", "pt-BR")
        if not math.isfinite(timeout) or not 1 <= timeout <= 120:
            raise ValueError("Model timeout must be between 1 and 120 seconds.")
        if not 1 <= rounds <= 10 or not 1 <= turns <= 50:
            raise ValueError("Tool rounds must be 1..10 and session turns must be 1..50.")
        if language not in {"pt-BR", "en"}:
            raise ValueError("Chat language must be pt-BR or en.")
        model = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash").strip()
        if not model or len(model) > 150:
            raise ValueError("GEMINI_MODEL must contain a valid model identifier.")
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if api_key in {"GEMINI_API_KEY", "YOUR_API_KEY", "your-api-key", "sua_chave_real_aqui"}:
            api_key = ""
        return cls(
            api_key=api_key,
            model=model, language=language, timeout=timeout,
            max_tool_rounds=rounds, max_turns=turns,
        )
