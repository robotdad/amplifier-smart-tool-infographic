"""Explicitly acknowledge stopped work without replaying it or deleting evidence."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from filelock import FileLock, Timeout

from infographic.schemas import InfographicError
from infographic.storage import Store


def close_interrupted(run_id: str, store: Path) -> dict[str, Any]:
    storage = Store(store)
    record = storage.read(run_id)
    try:
        # Admission may still be saving references after publishing the queued
        # record. Match its guard before checking execution or changing status.
        with (
            FileLock(str(storage.root / ".admission.lock"), timeout=0),
            FileLock(str(storage.directory(run_id) / ".execution.lock"), timeout=0),
        ):
            record = storage.read(run_id)
            if record["status"] in {"completed", "failed", "interrupted", "awaiting-selection"}:
                return record
            record.setdefault("history", []).append(
                {
                    "event": "caller-acknowledged-interruption",
                    "previous_status": record["status"],
                    "at": datetime.now(UTC).isoformat(),
                }
            )
            record["status"] = "interrupted"
            record["error"] = (
                "Execution was interrupted; external effects may be unknown. Preserved without replay. A new request is explicit new work."
            )
            storage.save(record)
            return record
    except Timeout as exc:
        raise InfographicError(
            "The store still holds an admission lock or this operation holds its execution lock. "
            "It cannot be marked interrupted during admission or execution; retry acknowledgement after work stops."
        ) from exc
