"""Read retained metadata and validate all registered artifact hashes."""

from pathlib import Path
from typing import Any

from infographic.storage import Store


def inspect(run_id: str, store: Path, verify: bool = True) -> dict[str, Any]:
    storage = Store(store)
    result = storage.read(run_id)
    if verify:
        for file in result["files"]:
            storage.artifact(run_id, file["name"])
    return result
