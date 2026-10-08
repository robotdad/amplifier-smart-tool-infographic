"""Append-only run directories and verified artifact reads."""

import hashlib
import json
from pathlib import Path
import re
from typing import Any
import uuid

from infographic.schemas import InfographicError

DEFAULT_STORE = Path.home() / ".local" / "share" / "infographic"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Store:
    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().resolve()

    def directory(self, run_id: str) -> Path:
        if not re.fullmatch(r"[a-f0-9]{32}", run_id):
            raise InfographicError("Invalid result ID. Use a 32-character ID returned by generate or list.")
        path = self.root / run_id
        if path.is_symlink():
            raise InfographicError("Result directory is a symlink; use a private, intact store.")
        return path

    def read(self, run_id: str) -> dict[str, Any]:
        path = self.directory(run_id) / "result.json"
        try:
            if path.is_symlink():
                raise InfographicError("Result record is a symlink; restore an intact store.")
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise InfographicError("Result not found or unreadable. Check the ID and --store.") from exc

    def save(self, record: dict[str, Any]) -> None:
        directory = self.directory(record["id"])
        temp = directory / f".{uuid.uuid4().hex}.tmp"
        temp.write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")
        temp.replace(directory / "result.json")

    def artifact(self, run_id: str, name: str) -> bytes:
        record = self.read(run_id)
        entry = next((item for item in record["files"] if item["name"] == name), None)
        if not entry or not re.fullmatch(r"[a-z0-9-]+\.png", name):
            raise InfographicError("Artifact is not listed in this result.")
        path = self.directory(run_id) / name
        if path.is_symlink():
            raise InfographicError("Artifact is a symlink; restore original bytes.")
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise InfographicError("Artifact is missing; restore the original result files.") from exc
        if digest(data) != entry["sha256"]:
            raise InfographicError("Artifact integrity failed; restore original bytes before reuse.")
        return data

    def add_image(self, record: dict[str, Any], name: str, data: bytes) -> None:
        path = self.directory(record["id"]) / name
        with path.open("xb") as handle:
            handle.write(data)
        record["files"].append({"name": name, "sha256": digest(data), "bytes": len(data)})
        self.save(record)
