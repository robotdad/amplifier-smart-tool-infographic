"""Admission of immutable creative inputs. Execution is shared with selection."""

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any
import uuid

from filelock import FileLock, Timeout

from infographic.execution import launch
from infographic.images import ImageService, normalize
from infographic.intelligence.interface import Intelligence
from infographic.models import Brief
from infographic.schemas import InfographicError
from infographic.storage import Store, digest


def generate(
    brief: Brief,
    store: Path,
    references: list[bytes] | None = None,
    parent_id: str | None = None,
    feedback: str = "",
    request_id: str | None = None,
    background: bool = False,
    intelligence: Intelligence | None = None,
    image_service: ImageService | None = None,
    style_references: list[bytes] | None = None,
    revision_images: list[bytes] | None = None,
) -> dict[str, Any]:
    groups = {"content": references or [], "style": style_references or [], "revision": revision_images or []}
    if len(groups["content"]) > 3 or len(groups["style"]) > 2 or len(groups["revision"]) > 6:
        raise InfographicError("Use at most 3 content references, 2 style references and 6 prior revision images.")
    normalized = {role: [normalize(data) for data in images] for role, images in groups.items()}
    storage = Store(store)
    run_id = request_id or uuid.uuid4().hex
    directory = storage.directory(run_id)
    storage.root.mkdir(parents=True, exist_ok=True)
    identity = digest(
        json.dumps(
            {
                "brief": brief.model_dump(),
                "references": {role: [digest(data) for data in images] for role, images in groups.items()},
                "parent": parent_id,
                "feedback": feedback,
            },
            sort_keys=True,
        ).encode()
    )
    try:
        with FileLock(str(storage.root / ".admission.lock"), timeout=0):
            if directory.exists():
                previous = storage.read(run_id)
                if previous["request_hash"] != identity:
                    raise InfographicError(
                        "Request ID belongs to different inputs. Inspect it or choose an explicitly new ID."
                    )
                return previous
            parent = storage.read(parent_id) if parent_id else None
            directory.mkdir(exist_ok=False)
            record: dict[str, Any] = {
                "schema_version": 2,
                "id": run_id,
                "parent_id": parent_id,
                "request_hash": identity,
                "created_at": datetime.now(UTC).isoformat(),
                "status": "queued",
                "brief": brief.model_dump(),
                "feedback": feedback,
                "files": [],
                "attempts": [],
                "calls": [],
                "references": [],
                "reference_input_sha256": [digest(data) for data in groups["content"]],
                "error": None,
                "composite": None,
                "candidates": [],
                "selection": None,
                "history": [{"event": "admitted", "at": datetime.now(UTC).isoformat()}],
            }
            if parent:
                record["parent_plan"] = parent.get("plan")
                record["parent_request_hash"] = parent["request_hash"]
            storage.save(record)
            for role, images in normalized.items():
                for index, data in enumerate(images, 1):
                    name = f"reference-{role}-{index}.png"
                    record["references"].append(
                        {"role": role, "name": name, "input_sha256": digest(groups[role][index - 1])}
                    )
                    storage.add_image(record, name, data)
    except Timeout as exc:
        raise InfographicError("Another request is being admitted. Retry the SAME request ID and payload.") from exc
    launch(record, storage, background, intelligence, image_service)
    return storage.read(run_id)
