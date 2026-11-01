"""Filesystem configuration without global working-directory changes."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    raw_dir: Path
    database_path: Path
    policies_path: Path

    @classmethod
    def from_environment(cls, project_root: Path | None = None) -> "Settings":
        root = Path(
            project_root if project_root is not None
            else os.environ.get("EMPORIO_PROJECT_ROOT", ".")
        ).expanduser().resolve()

        def resolve_path(variable: str, default: str) -> Path:
            path = Path(os.environ.get(variable, default)).expanduser()
            return (root / path).resolve() if not path.is_absolute() else path.resolve()

        return cls(
            raw_dir=resolve_path("EMPORIO_RAW_DIR", "data/raw"),
            database_path=resolve_path("EMPORIO_DATABASE_PATH", "data/processed/emporio.sqlite3"),
            policies_path=resolve_path("EMPORIO_POLICIES_PATH", "data/raw/políticas_da_loja.pdf"),
        )
