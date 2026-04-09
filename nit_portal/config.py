from __future__ import annotations

import os
from pathlib import Path


def load_dotenv(dotenv_path: Path | str = ".env") -> None:
    path = Path(dotenv_path)
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"missing required env var: {name}")
    return value


def get_database_url() -> str:
    return os.environ.get("DATABASE_URL", "sqlite:///data/nit_portal.db")
