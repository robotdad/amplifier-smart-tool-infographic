"""Exactly-once selection of a retained candidate, followed by bounded production."""

from pathlib import Path
from typing import Any
import uuid

from filelock import FileLock, Timeout

from infographic.execution import launch
from infographic.images import ImageService
from infographic.intelligence.interface import Intelligence
from infographic.schemas import InfographicError
from infographic.storage import Store


def select(
    run_id: str,
    candidate: int,
    store: Path,
    request_id: str | None = None,
    background: bool = False,
    intelligence: Intelligence | None = None,
    image_service: ImageService | None = None,
) -> dict[str, Any]:
    storage = Store(store)
    identity = request_id or uuid.uuid4().hex
    storage.directory(identity)
    directory = storage.directory(run_id)
    if not directory.exists():
        raise InfographicError("Result not found. Inspect the selected ID.")
    previous = storage.read(run_id)
    if (previous.get("selection") or {}).get("request_id") == identity:
        if previous["selection"]["candidate"] != candidate:
            raise InfographicError("Selection identity already belongs to a different candidate.")
        return previous
    try:
        with (
            FileLock(str(directory / ".selection.lock"), timeout=0),
            FileLock(str(directory / ".execution.lock"), timeout=0),
        ):
            record = storage.read(run_id)
            if record.get("selection"):
                chosen = record["selection"]
                if chosen.get("request_id") == identity and chosen["candidate"] == candidate:
                    return record
                raise InfographicError("This result already has a retained selection. It cannot be replaced.")
            if record["status"] != "awaiting-selection" or not 1 <= candidate <= len(record["candidates"]):
                raise InfographicError("Select a listed candidate from a result awaiting selection.")
            storage.artifact(run_id, record["candidates"][candidate - 1]["image"])
            record["selection"] = {
                "candidate": candidate,
                "actor": "caller",
                "request_id": identity,
                "rationale": "Explicit caller selection.",
            }
            record["status"] = "selection-admitted"
            storage.save(record)
    except Timeout as exc:
        raise InfographicError("Selection is being admitted. Retry the same identity and candidate.") from exc
    launch(record, storage, background, intelligence, image_service)
    return storage.read(run_id)
