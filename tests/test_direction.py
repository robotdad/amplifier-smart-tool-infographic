"""Direction-specific checks using explicit simulated reasoning and image fixtures."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import threading
from typing import Any

from filelock import FileLock
import pytest
from test_product import Reasoner, Renderer, png

from infographic import lib
from infographic.intelligence.schemas import AgentRequest, AgentResult
from infographic.models import DEFAULT_MODELS, Brief
from infographic.schemas import InfographicError
from infographic.storage import Store, digest


def test_freeform_has_no_forced_content_structure_and_revises_exact_image_twice(tmp_path: Path) -> None:
    reasoner, renderer = Reasoner(), Renderer()
    first = lib.generate(
        Brief(mode="freeform", topic="Watercolor observatory, no text", orientation="landscape"),
        tmp_path,
        intelligence=reasoner,
        image_service=renderer,
    )
    assert first["status"] == "completed"
    assert [request.output_schema["title"] for request in reasoner.requests] == ["FreeformPlan", "Review"]
    prompt = renderer.requests[0]["prompt"]
    assert "Render one finished infographic" not in prompt
    assert "Panel 1" not in prompt
    assert '"style": ""' in prompt
    assert "Editorial" not in prompt
    assert "Do NOT require labels" in reasoner.requests[-1].prompt
    assert renderer.requests[0]["ratio"] == "4:3"
    original = (tmp_path / first["id"] / "result.json").read_bytes()
    child = first
    for feedback in ("Make it dawn, keep composition and no text", "Add a distant sailboat; preserve treatment"):
        parent = child
        before = len(renderer.requests)
        child = lib.refine(parent["id"], feedback, tmp_path, intelligence=reasoner, image_service=renderer)
        assert child["status"] == "completed"
        assert child["parent_id"] == parent["id"]
        previous_pixels = lib.artifact(parent["id"], parent["attempts"][-1]["panels"][0], tmp_path)
        assert previous_pixels in renderer.requests[before]["references"]
        assert feedback in renderer.requests[before]["prompt"]
    assert (tmp_path / first["id"] / "result.json").read_bytes() == original
    assert lib.inspect(first["id"], tmp_path) == first


def test_manual_candidate_selection_retained_exact_retry_and_anchor_gate(tmp_path: Path) -> None:
    reasoner, renderer = Reasoner(3), Renderer()
    result = lib.generate(
        Brief(topic="Release flow", panels=3, candidates=3, style="claymation"),
        tmp_path,
        intelligence=reasoner,
        image_service=renderer,
    )
    assert result["status"] == "awaiting-selection"
    assert len(renderer.requests) == 3
    assert not any(request.output_schema["title"] == "AnchorAnalysis" for request in reasoner.requests)
    assert len({candidate["direction"] for candidate in result["candidates"]}) == 3
    before = [(entry["name"], entry["sha256"]) for entry in result["files"]]
    assert lib.inspect(result["id"], tmp_path) == result
    final = lib.select(result["id"], 2, tmp_path, "a" * 32, intelligence=reasoner, image_service=renderer)
    assert final["status"] == "completed"
    assert final["selection"] == {
        "candidate": 2,
        "actor": "caller",
        "request_id": "a" * 32,
        "rationale": "Explicit caller selection.",
    }
    assert all(pair in [(entry["name"], entry["sha256"]) for entry in final["files"]] for pair in before)
    anchor = lib.artifact(result["id"], "candidate-2.png", tmp_path)
    assert reasoner.requests[-2].output_schema["title"] == "AnchorAnalysis"
    assert reasoner.requests[-2].images == [anchor]
    assert renderer.requests[3]["references"][0] == anchor
    assert renderer.requests[4]["references"][0] == anchor
    assert "Observed teal objects" in renderer.requests[3]["prompt"]
    count = len(renderer.requests)
    assert lib.select(result["id"], 2, tmp_path, "a" * 32) == final
    assert len(renderer.requests) == count
    with pytest.raises(InfographicError, match="already has"):
        lib.select(result["id"], 1, tmp_path, "b" * 32)


def test_auto_candidate_selection_is_not_human_approval(tmp_path: Path) -> None:
    reasoner, renderer = Reasoner(2), Renderer()
    result = lib.generate(
        Brief(topic="Flow", candidates=2, selection="auto"), tmp_path, intelligence=reasoner, image_service=renderer
    )
    assert result["status"] == "completed"
    assert result["selection"]["actor"] == "automatic-requested"
    assert result["selection"]["candidate"] == 2
    choice = next(request for request in reasoner.requests if request.output_schema["title"] == "Choice")
    assert len(choice.images) == 2


def test_anchor_failure_never_produces_later_panels(tmp_path: Path) -> None:
    class FailingAnchor(Reasoner):
        def run(self, request: AgentRequest) -> AgentResult:
            if request.output_schema["title"] == "AnchorAnalysis":
                return AgentResult(error="Anchor analysis failed. Inspect image support.")
            return super().run(request)

    renderer = Renderer()
    result = lib.generate(
        Brief(topic="Flow", panels=3), tmp_path, intelligence=FailingAnchor(3), image_service=renderer
    )
    assert result["status"] == "failed"
    assert len(renderer.requests) == 1
    assert result["files"]


def test_reference_roles_original_style_alongside_anchor_and_revisions(tmp_path: Path) -> None:
    reasoner, renderer = Reasoner(2), Renderer()
    content, style = png("red"), png("yellow")
    first = lib.generate(
        Brief(topic="Flow", panels=2),
        tmp_path,
        [content],
        style_references=[style],
        intelligence=reasoner,
        image_service=renderer,
    )
    assert first["status"] == "completed"
    assert reasoner.requests[0].images == [content, style]
    assert renderer.requests[0]["references"] == [style]
    anchor = lib.artifact(first["id"], "candidate-1.png", tmp_path)
    assert renderer.requests[1]["references"] == [anchor, style]
    assert content not in renderer.requests[1]["references"]
    calls = [call for call in first["calls"] if call["task"] == "image"]
    assert calls[1]["reference_roles"] == ["chosen-first-image-anchor", "style"]
    assert calls[1]["reference_sha256"] == [digest(anchor), digest(style)]
    child = lib.refine(first["id"], "Larger labels", tmp_path, intelligence=reasoner, image_service=renderer)
    assert child["status"] == "completed"
    assert [item["role"] for item in child["references"]] == ["content", "style", "revision", "revision"]
    assert style in renderer.requests[2]["references"]
    assert all(
        lib.artifact(first["id"], name, tmp_path) in renderer.requests[2]["references"]
        for name in first["attempts"][-1]["panels"]
    )


def test_freeform_content_reference_preserves_subject_not_unrequested_style(tmp_path: Path) -> None:
    renderer = Renderer()
    subject = png("red")
    result = lib.generate(
        Brief(mode="freeform", topic="Paint this subject in watercolor"),
        tmp_path,
        [subject],
        intelligence=Reasoner(),
        image_service=renderer,
    )
    assert result["status"] == "completed"
    assert renderer.requests[0]["references"] == [subject]
    assert '["content"]' in renderer.requests[0]["prompt"]
    assert "never an unrequested aesthetic" in renderer.requests[0]["prompt"]


def test_auto_density_uses_plan_explicit_values_override(tmp_path: Path) -> None:
    result = lib.generate(
        Brief(topic="Dense material with several sections"),
        tmp_path,
        intelligence=Reasoner(4),
        image_service=Renderer(),
    )
    assert result["status"] == "completed"
    assert len(result["attempts"][0]["panels"]) == 4
    explicit = lib.generate(
        Brief(
            topic="Flow", panels=1, orientation="square", layout="grid", style="brick-built", representation="diorama"
        ),
        tmp_path,
        intelligence=Reasoner(1),
        image_service=Renderer(),
    )
    assert explicit["plan"]["orientation"] == "square"
    assert explicit["plan"]["layout"] == "grid"
    assert explicit["brief"]["representation"] == "diorama"
    assert {"claymation", "brick-built", "diorama", "freeform", "sketch", "dark-tech"} <= lib.styles().keys()


@pytest.mark.parametrize("provider", list(DEFAULT_MODELS))
def test_provider_specific_defaults_and_explicit_model(provider: Any) -> None:
    assert Brief(topic="x", provider=provider).model == DEFAULT_MODELS[provider]
    assert Brief(topic="x", provider=provider, model="my-exact-model").model == "my-exact-model"


def test_interruption_ack_preserves_evidence_and_new_work_is_possible(tmp_path: Path) -> None:
    first = lib.generate(Brief(topic="x"), tmp_path, intelligence=Reasoner(1), image_service=Renderer())
    storage = Store(tmp_path)
    interrupted = {**first, "status": "reviewing"}
    storage.save(interrupted)
    with (
        FileLock(str(storage.directory(first["id"]) / ".execution.lock")),
        pytest.raises(InfographicError, match="still holds"),
    ):
        lib.close_interrupted(first["id"], tmp_path)
    closed = lib.close_interrupted(first["id"], tmp_path)
    assert closed["status"] == "interrupted"
    assert closed["files"] == first["files"]
    assert closed["history"][-1]["previous_status"] == "reviewing"
    assert lib.close_interrupted(first["id"], tmp_path) == closed
    second = lib.generate(
        Brief(topic="Deliberate next work"), tmp_path, intelligence=Reasoner(1), image_service=Renderer()
    )
    assert second["status"] == "completed"
    assert lib.inspect(first["id"], tmp_path) == closed


def test_concurrent_selection_has_single_effect(tmp_path: Path) -> None:
    result = lib.generate(Brief(topic="x", candidates=2), tmp_path, intelligence=Reasoner(2), image_service=Renderer())
    renderer = Renderer()
    gate = threading.Barrier(2)

    def choose() -> str:
        gate.wait()
        try:
            return lib.select(result["id"], 1, tmp_path, "c" * 32, intelligence=Reasoner(2), image_service=renderer)[
                "status"
            ]
        except InfographicError:
            return "refused"

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(choose) for _ in range(2)]
        states = [future.result() for future in futures]
    assert "completed" in states
    assert len(renderer.requests) == 1
    assert lib.inspect(result["id"], tmp_path)["selection"]["candidate"] == 1


def test_terminal_history_is_published_in_same_snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original = Store.save
    snapshots = []

    def save(storage: Store, record: dict[str, Any]) -> None:
        if record["status"] in {"completed", "failed", "awaiting-selection"}:
            assert record["history"][-1]["event"] == record["status"]
            snapshots.append(record["status"])
        original(storage, record)

    monkeypatch.setattr(Store, "save", save)
    result = lib.generate(Brief(topic="Flow"), tmp_path, intelligence=Reasoner(1), image_service=Renderer())
    assert result["status"] == "completed"
    assert snapshots == ["completed"]


def test_selection_cannot_commit_before_prior_worker_releases_execution_lock(tmp_path: Path) -> None:
    result = lib.generate(
        Brief(topic="Flow", candidates=2), tmp_path, intelligence=Reasoner(2), image_service=Renderer()
    )
    storage = Store(tmp_path)
    with (
        FileLock(str(storage.directory(result["id"]) / ".execution.lock")),
        pytest.raises(InfographicError, match="Retry the same"),
    ):
        lib.select(result["id"], 1, tmp_path, "f" * 32, intelligence=Reasoner(2), image_service=Renderer())
    assert lib.inspect(result["id"], tmp_path) == result
    final = lib.select(result["id"], 1, tmp_path, "f" * 32, intelligence=Reasoner(2), image_service=Renderer())
    assert final["status"] == "completed"
