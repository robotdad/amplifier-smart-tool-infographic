"""Bounded retained result inventory."""

from pathlib import Path
from typing import Any

from infographic.schemas import InfographicError
from infographic.storage import Store


def list_results(store: Path, limit: int = 50) -> list[dict[str, Any]]:
    if not 1 <= limit <= 200:
        raise InfographicError("List limit must be 1 to 200.")
    storage = Store(store)
    result = []
    if not storage.root.exists():
        return result
    for path in sorted(storage.root.iterdir(), key=lambda path: path.stat().st_mtime, reverse=True):
        if not path.is_dir() or path.is_symlink():
            continue
        try:
            record = storage.read(path.name)
            result.append({key: record[key] for key in ("id", "created_at", "status", "brief", "parent_id", "error")})
        except InfographicError:
            continue
        if len(result) == limit:
            break
    return result
