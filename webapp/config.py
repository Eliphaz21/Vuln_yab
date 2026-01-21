from __future__ import annotations

from pathlib import Path
import os
from typing import Set


# Root of the repository (default docs root)
REPO_ROOT: Path = Path(__file__).resolve().parents[1]

# Allow overriding docs root with an environment variable
DOCS_ROOT: Path = Path(os.environ.get("DOCS_ROOT", str(REPO_ROOT))).resolve()

# File extensions to include as documentation
INCLUDE_EXTENSIONS: Set[str] = {".md", ".markdown", ".txt"}

# Directory names to exclude during discovery
EXCLUDE_DIRS: Set[str] = {
    ".git",
    ".github",
    "node_modules",
    "__pycache__",
    "venv",
    ".venv",
    ".mypy_cache",
    ".pytest_cache",
    ".idea",
    ".vscode",
    ".cursor",
}

# Absolute-path based exclude prefixes (relative to DOCS_ROOT)
EXCLUDE_PREFIXES: Set[Path] = {
    (DOCS_ROOT / "advance" / "fonts").resolve(),  # binary fonts; not docs
}


def is_under_docs_root(path: Path) -> bool:
    try:
        return path.resolve().is_relative_to(DOCS_ROOT)
    except AttributeError:
        # Python <3.9 compatibility fallback
        return str(path.resolve()).startswith(str(DOCS_ROOT))
