"""Top level entry point for the Infographic library."""

from pathlib import Path
from typing import Any

from infographic.core import manifest
from infographic.core import skill as skill_module
from infographic.images import ImageService
from infographic.intelligence.interface import Intelligence
from infographic.models import Brief
from infographic.schemas import Manifest
from infographic.storage import DEFAULT_STORE, Store


def load_manifest() -> Manifest:
    """The tool's manifest as structured data, read from the SMART_TOOL.md shipped inside the package."""
    return manifest.load_manifest()


def skill(capability: str | None = None) -> str:
    """The tool's skill, or the named capability's own skill, wrapped so a reader knows where the tool's files are."""
    return skill_module.skill(capability)


def skill_directory() -> Path:
    """The installed package root, where the files the skill names can be read."""
    return skill_module.skill_directory()


def skill_resources() -> list[str]:
    """The files the skill lists, as paths relative to the skill directory. Every one ships inside the package."""
    return skill_module.skill_resources()


def capability_skill_resources(capability: str) -> list[str]:
    """The files that capability's skill lists, as paths relative to the skill directory."""
    return skill_module.capability_skill_resources(capability)


def repository_url() -> str | None:
    """The tool's canonical source, from the package metadata, or None when the package declares none."""
    return skill_module.repository_url()


def generate(
    brief: Brief,
    store: Path = DEFAULT_STORE,
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
    from infographic.capabilities.generate.run import generate as run

    return run(
        brief,
        store,
        references,
        parent_id,
        feedback,
        request_id,
        background,
        intelligence,
        image_service,
        style_references,
        revision_images,
    )


def select(
    run_id: str,
    candidate: int,
    store: Path = DEFAULT_STORE,
    request_id: str | None = None,
    background: bool = False,
    intelligence: Intelligence | None = None,
    image_service: ImageService | None = None,
) -> dict[str, Any]:
    from infographic.capabilities.select.run import select as run

    return run(run_id, candidate, store, request_id, background, intelligence, image_service)


def close_interrupted(run_id: str, store: Path = DEFAULT_STORE) -> dict[str, Any]:
    from importlib import import_module

    return import_module("infographic.capabilities.close-interrupted.run").close_interrupted(run_id, store)


def refine(
    run_id: str,
    feedback: str,
    store: Path = DEFAULT_STORE,
    changes: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    from infographic.capabilities.refine.run import refine as run

    return run(run_id, feedback, store, changes, **kwargs)


def inspect(run_id: str, store: Path = DEFAULT_STORE, verify: bool = True) -> dict[str, Any]:
    from infographic.capabilities.inspect.run import inspect as run

    return run(run_id, store, verify)


def list_results(store: Path = DEFAULT_STORE, limit: int = 50) -> list[dict[str, Any]]:
    from infographic.capabilities.list.run import list_results as run

    return run(store, limit)


def artifact(run_id: str, name: str, store: Path = DEFAULT_STORE) -> bytes:
    return Store(store).artifact(run_id, name)


def stitch_bytes(images: list[bytes], layout: str = "vertical") -> bytes:
    from infographic.capabilities.stitch.run import stitch

    return stitch(images, layout)


def styles() -> dict[str, str]:
    from infographic.capabilities.styles.run import styles as run

    return run()


def check() -> dict[str, Any]:
    from infographic.capabilities.check.run import check as run

    return run()


def dashboard(store: Path = DEFAULT_STORE, port: int = 8765) -> Any:
    """Create a loopback-only server. Caller owns serve_forever and server_close."""
    from infographic.capabilities.serve.run import dashboard as run

    return run(store, port)
