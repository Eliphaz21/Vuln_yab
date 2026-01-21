from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
import os
import re

from . import config


@dataclass
class Document:
    absolute_path: Path
    relative_path: str  # POSIX-style path relative to docs root
    title: str
    content: str
    lower_content: str


def _should_skip_dir(dir_path: Path) -> bool:
    # Skip if any part of the path equals an excluded directory name
    for part in dir_path.parts:
        if part in config.EXCLUDE_DIRS:
            return True
    # Skip if the directory is under any excluded absolute prefix
    try:
        resolved = dir_path.resolve()
    except FileNotFoundError:
        resolved = dir_path
    for prefix in config.EXCLUDE_PREFIXES:
        try:
            if resolved.is_relative_to(prefix):
                return True
        except AttributeError:
            if str(resolved).startswith(str(prefix)):
                return True
    return False


def _is_allowed_file(path: Path) -> bool:
    return path.suffix.lower() in config.INCLUDE_EXTENSIONS


def _extract_title(file_path: Path, content: str) -> str:
    # Use first markdown H1 if present, else first non-empty line, else filename
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
        if stripped:
            return stripped
    return file_path.stem


def discover_documents() -> List[Document]:
    docs: List[Document] = []
    root: Path = config.DOCS_ROOT

    for current_root, dirnames, filenames in os.walk(root):
        current_root_path = Path(current_root)
        # Prune excluded directories in-place for os.walk
        pruned: List[str] = []
        for d in list(dirnames):
            candidate = current_root_path / d
            if _should_skip_dir(candidate):
                pruned.append(d)
        for d in pruned:
            dirnames.remove(d)

        for filename in filenames:
            file_path = current_root_path / filename
            if not _is_allowed_file(file_path):
                continue
            try:
                absolute_path = file_path.resolve()
            except FileNotFoundError:
                continue
            if not config.is_under_docs_root(absolute_path):
                continue
            try:
                text = absolute_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                # Ignore unreadable files
                continue
            rel_path = absolute_path.relative_to(root).as_posix()
            title = _extract_title(absolute_path, text)
            docs.append(
                Document(
                    absolute_path=absolute_path,
                    relative_path=rel_path,
                    title=title,
                    content=text,
                    lower_content=text.lower(),
                )
            )

    # Deterministic order: by relative path
    docs.sort(key=lambda d: d.relative_path)
    return docs


def build_tree(documents: Iterable[Document]) -> Dict:
    """Build a nested tree structure from document relative paths.

    Returns a dict-based tree:
    {
      'name': '', 'path': '', 'type': 'dir', 'children': { 'subdir': {...}, 'file.md': {...} }
    }
    """
    root: Dict = {"name": "", "path": "", "type": "dir", "children": {}}

    for doc in documents:
        parts = doc.relative_path.split('/')
        cursor = root
        accumulated: List[str] = []
        for i, part in enumerate(parts):
            accumulated.append(part)
            is_last = i == len(parts) - 1
            if "children" not in cursor:
                cursor["children"] = {}
            children = cursor["children"]
            if part not in children:
                children[part] = {
                    "name": part,
                    "path": "/".join(accumulated),
                    "type": "file" if is_last else "dir",
                }
            cursor = children[part]
    return root


class SearchResult:
    def __init__(self, document: Document, score: float, excerpt: str) -> None:
        self.document = document
        self.score = score
        self.excerpt = excerpt


class SimpleSearchIndex:
    def __init__(self, documents: List[Document]) -> None:
        self._documents = documents

    @property
    def documents(self) -> List[Document]:
        return self._documents

    def search(self, query: str, limit: int = 50) -> List[SearchResult]:
        q = query.strip()
        if not q:
            return []
        pattern = re.compile(re.escape(q), flags=re.IGNORECASE)
        results: List[SearchResult] = []
        for doc in self._documents:
            title_hits = len(re.findall(pattern, doc.title))
            content_hits = len(re.findall(pattern, doc.content))
            score = title_hits * 5 + content_hits
            if score == 0:
                continue
            excerpt = _make_excerpt(doc.content, pattern)
            results.append(SearchResult(doc, float(score), excerpt))
        results.sort(key=lambda r: (-r.score, r.document.relative_path))
        return results[:limit]


def _make_excerpt(text: str, pattern: re.Pattern, context: int = 120) -> str:
    match = pattern.search(text)
    if not match:
        return text[:2 * context]
    start = max(match.start() - context, 0)
    end = min(match.end() + context, len(text))
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    snippet = text[start:end].replace("\n", " ")
    return f"{prefix}{snippet}{suffix}"
