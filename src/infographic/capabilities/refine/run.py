"""Refinement creates a child result and never modifies its parent."""

from pathlib import Path
from typing import Any

from infographic.models import Brief
from infographic.schemas import InfographicError
from infographic.storage import Store


def refine(
    run_id: str, feedback: str, store: Path, changes: dict[str, Any] | None = None, **kwargs: Any
) -> dict[str, Any]:
    from infographic import lib

    if not feedback.strip() or len(feedback) > 6000:
        raise InfographicError("Refinement needs 1 to 6000 characters of feedback.")
    storage = Store(store)
    parent = lib.inspect(run_id, store)
    if parent["status"] != "completed":
        raise InfographicError(
            "Refine a completed result. Failed runs remain inspectable; generate a new request to retry."
        )
    changes = changes or {}
    inherited = parent["brief"].copy()
    if "provider" in changes and changes["provider"] != inherited["provider"] and "model" not in changes:
        inherited["model"] = ""
    if changes.get("mode") == "freeform" and "panels" not in changes:
        inherited["panels"] = None
    brief = Brief.model_validate({**inherited, **changes})
    panels = parent["attempts"][-1]["panels"]
    revision_images = [storage.artifact(run_id, name) for name in panels]
    references = kwargs.pop("references", None)
    style_references = kwargs.pop("style_references", None)
    if references is None:
        references = [
            storage.artifact(run_id, item["name"]) for item in parent.get("references", []) if item["role"] == "content"
        ]
    if style_references is None:
        style_references = [
            storage.artifact(run_id, item["name"]) for item in parent.get("references", []) if item["role"] == "style"
        ]
    return lib.generate(
        brief,
        store=store,
        references=references,
        style_references=style_references,
        revision_images=revision_images,
        parent_id=run_id,
        feedback=feedback,
        **kwargs,
    )
