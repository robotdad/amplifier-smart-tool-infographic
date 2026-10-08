"""Precise admission/interruption seam checks; external work is simulated."""

from concurrent.futures import ThreadPoolExecutor
from importlib import import_module
from pathlib import Path
import threading
from typing import Any

import pytest
from test_product import Reasoner, Renderer, png

from infographic import lib
from infographic.models import Brief
from infographic.schemas import InfographicError
from infographic.storage import Store


def test_interruption_refuses_while_reference_admission_is_live(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = Store.add_image
    admitted, release = threading.Event(), threading.Event()
    renderer = Renderer()
    run_id = "a" * 32

    def pause(storage: Store, record: dict[str, Any], name: str, data: bytes) -> None:
        if name == "reference-content-1.png":
            admitted.set()
            assert release.wait(10)
        original(storage, record, name, data)

    monkeypatch.setattr(Store, "add_image", pause)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(
            lib.generate,
            Brief(topic="Alpha", panels=1),
            tmp_path,
            [png("red")],
            request_id=run_id,
            intelligence=Reasoner(1),
            image_service=renderer,
        )
        try:
            assert admitted.wait(10)
            snapshot = Store(tmp_path).read(run_id)
            with pytest.raises(InfographicError, match="admission"):
                lib.close_interrupted(run_id, tmp_path)
            assert Store(tmp_path).read(run_id) == snapshot
            assert not renderer.requests
        finally:
            release.set()
        result = future.result(timeout=10)
    assert result["status"] == "completed"
    assert len(renderer.requests) == 1
    assert not any(item["event"] == "caller-acknowledged-interruption" for item in result["history"])


def test_stopped_reference_admission_can_be_acknowledged_without_losing_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = Store.add_image
    run_id = "b" * 32
    renderer = Renderer()

    def stopped(storage: Store, record: dict[str, Any], name: str, data: bytes) -> None:
        original(storage, record, name, data)
        raise OSError("simulated process admission failure after retained reference")

    monkeypatch.setattr(Store, "add_image", stopped)
    with pytest.raises(OSError, match="simulated"):
        lib.generate(
            Brief(topic="Alpha", panels=1),
            tmp_path,
            [png("red")],
            request_id=run_id,
            intelligence=Reasoner(1),
            image_service=renderer,
        )
    original_record = lib.inspect(run_id, tmp_path)
    closed = lib.close_interrupted(run_id, tmp_path)
    assert closed["status"] == "interrupted"
    assert closed["files"] == original_record["files"]
    assert closed["history"][-1]["event"] == "caller-acknowledged-interruption"
    assert closed["history"][-1]["previous_status"] == "queued"
    assert lib.close_interrupted(run_id, tmp_path) == closed
    assert (
        lib.generate(
            Brief(topic="Alpha", panels=1),
            tmp_path,
            [png("red")],
            request_id=run_id,
            intelligence=Reasoner(1),
            image_service=renderer,
        )
        == closed
    )
    assert not renderer.requests


def test_acknowledgement_between_admission_and_launch_prevents_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = import_module("infographic.capabilities.generate.run")
    original_launch = module.launch
    admitted, release = threading.Event(), threading.Event()
    renderer = Renderer()
    run_id = "c" * 32

    def pause(*args: Any) -> None:
        admitted.set()
        assert release.wait(10)
        original_launch(*args)

    monkeypatch.setattr(module, "launch", pause)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(
            lib.generate,
            Brief(topic="Alpha", panels=1),
            tmp_path,
            [png("red")],
            request_id=run_id,
            intelligence=Reasoner(1),
            image_service=renderer,
        )
        try:
            assert admitted.wait(10)
            closed = lib.close_interrupted(run_id, tmp_path)
            assert closed["status"] == "interrupted"
            assert len(closed["files"]) == 1
        finally:
            release.set()
        result = future.result(timeout=10)
    assert result == closed
    assert lib.inspect(run_id, tmp_path) == closed
    assert not renderer.requests
