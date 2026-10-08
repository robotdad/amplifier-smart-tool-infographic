"""Provider-free evidence at the actual render boundary, not a pixel-quality verdict."""

import copy
import json
from pathlib import Path
from typing import Any, Literal

import pytest
from test_product import Reasoner, Renderer, png

from infographic import lib
from infographic.execution import Workflow
from infographic.intelligence.schemas import AgentRequest, AgentResult
from infographic.models import Brief
from infographic.storage import Store, digest


def live_excerpt() -> dict[str, Any]:
    return json.loads((Path(__file__).parent / "fixtures/guided_binding.json").read_text(encoding="utf-8"))


def input_record(
    tmp_path: Path, mode: Literal["infographic", "freeform"] = "infographic"
) -> tuple[dict[str, Any], Store]:
    fixture = live_excerpt()
    record: dict[str, Any] = {
        "id": "a" * 32,
        "brief": Brief(topic=fixture["topic"], mode=mode, panels=3 if mode == "infographic" else None).model_dump(),
        "feedback": fixture["feedback"],
        "parent_plan": {"panels": fixture["parent_panels"]},
        "plan": {
            "panels": [*fixture["parent_panels"][:2], fixture["revised_final"]],
            "style_brief": "Claymation",
            "orientation": "portrait",
        },
        "observed_style": "Cream lettering on wooden header '1. Prepare'; workshop props; warm clay texture.",
        "references": [],
        "files": [],
        "calls": [],
        "history": [],
    }
    if mode == "freeform":
        record["plan"] = {"description": "Watercolor coastal observatory without text.", "orientation": "landscape"}
        record["parent_plan"] = {"description": "Previous observatory"}
    storage = Store(tmp_path)
    storage.directory(record["id"]).mkdir(parents=True)
    storage.save(record)
    for index, role in enumerate(["style", "revision", "revision", "revision"], 1):
        name = f"reference-{index}.png"
        record["references"].append({"role": role, "name": name})
        storage.add_image(record, name, png(["yellow", "red", "green", "blue"][index - 1]))
    return record, storage


@pytest.mark.parametrize("panel", [1, 2, 3])
def test_live_plan_current_target_is_explicit_and_other_stage_changes_stay_context(tmp_path: Path, panel: int) -> None:
    record, storage = input_record(tmp_path)
    renderer = Renderer()
    flow = Workflow(record, storage, Reasoner(), renderer)
    anchor = png("purple") if panel > 1 else None
    direction = "Render three vertically stacked cutaway floors."  # Observed series-level alternative shape.
    flow.image(f"target-{panel}.png", panel, direction, anchor)
    prompt = renderer.requests[0]["prompt"]
    binding = json.loads(prompt.split("GUIDED_PANEL_BINDING_JSON:\n", 1)[1])
    target = binding["target"]
    assert target == {"panel_index": panel, "panel_count": 3, **record["plan"]["panels"][panel - 1]}
    assert binding["current_series_allocation_context_only"][2]["title"] == "3. Ship with confidence"
    assert binding["series_context_not_copy"]["caller_context"]["revision_request"] == live_excerpt()["feedback"]
    assert binding["series_context_not_copy"]["series_alternative"] == direction
    if panel == 1:
        assert target["title"] == "1. Prepare"
        assert target["content"] == ["Run tests", "Review the changelog"]
        assert "Keep the previous build available" not in json.dumps(target)
    if panel == 3:
        assert target["title"] == "3. Ship with confidence"
        assert "Keep the previous build available" in target["content"]
        assert "Beneath the rollback instructions label, a lower clay shelf" in target["visual"]
    assert "EXACTLY ONE" in prompt
    assert "not competing copy lists" in prompt
    assert "never overrides this single-panel boundary" in prompt
    refs = binding["reference_images_in_order"]
    previous = [entry for entry in refs if entry["role"] == "revision"]
    assert [entry["prior_panel_index"] for entry in previous] == [1, 2, 3]
    assert [entry["prior_title"] for entry in previous] == ["1. Prepare", "2. Verify", "3. Release"]
    assert [entry["image_index"] for entry in refs] == list(range(1, len(refs) + 1))
    assert [entry["sha256"] for entry in refs] == [digest(data) for data in renderer.requests[0]["references"]]
    if anchor:
        assert refs[0]["use"] == "style-only"
        assert refs[0]["content_authority"].startswith("none")
        assert renderer.requests[0]["references"][0] == anchor
    call = storage.read(record["id"])["calls"][-1]
    assert call["prompt"] == prompt
    assert call["prompt_sha256"] == digest(prompt.encode("utf-8"))
    assert call["panel_binding"] == binding
    assert "OPENAI_API_KEY" not in prompt


@pytest.mark.parametrize("restructure", ["reorder", "merge"])
def test_structural_change_never_assigns_same_index_prior_image_as_target(tmp_path: Path, restructure: str) -> None:
    record, storage = input_record(tmp_path)
    original = copy.deepcopy(record["plan"]["panels"])
    if restructure == "reorder":
        record["plan"]["panels"] = [original[2], original[0], original[1]]
    else:
        record["plan"]["panels"] = [
            {
                "title": "Prepare and verify",
                "content": original[0]["content"] + original[1]["content"],
                "visual": "Combine workbench and isolated test environment in a single scene.",
            },
            original[2],
        ]
    renderer = Renderer()
    Workflow(record, storage, Reasoner(), renderer).image("structural.png", 1, "")
    binding = record["calls"][-1]["panel_binding"]
    assert binding["target"]["title"] == record["plan"]["panels"][0]["title"]
    assert binding["target"]["panel_count"] == len(record["plan"]["panels"])
    refs = [entry for entry in binding["reference_images_in_order"] if entry["role"] == "revision"]
    assert len(refs) == 3
    assert [entry["prior_title"] for entry in refs] == ["1. Prepare", "2. Verify", "3. Release"]
    assert all(entry["current_panel_correspondence"].startswith("not-assumed") for entry in refs)
    assert "Panels may be reordered, merged or split" in renderer.requests[0]["prompt"]


def test_guided_prompt_receipt_exists_before_failed_image_request(tmp_path: Path) -> None:
    record, storage = input_record(tmp_path)

    class FailingRenderer(Renderer):
        def render(self, prompt: str, references: list[bytes], model: str, ratio: str, timeout: int) -> bytes:
            call = storage.read(record["id"])["calls"][-1]
            assert call["status"] == "started"
            assert call["prompt"] == prompt
            assert call["prompt_sha256"] == digest(prompt.encode("utf-8"))
            raise RuntimeError("simulated service failure")

    with pytest.raises(RuntimeError, match="simulated"):
        Workflow(record, storage, Reasoner(), FailingRenderer()).image("failed.png", 1, "")
    assert not any(item["name"] == "failed.png" for item in storage.read(record["id"])["files"])


def test_anchor_analysis_scoped_to_first_panel_and_transferable_style(tmp_path: Path) -> None:
    fixture = live_excerpt()

    class LivePlanReasoner(Reasoner):
        def run(self, request: AgentRequest) -> AgentResult:
            if request.output_schema["title"] == "Plan":
                self.requests.append(request)
                return AgentResult(
                    output={
                        "title": "Team release workflow",
                        "style_brief": "Claymation",
                        "panels": [*fixture["parent_panels"][:2], fixture["revised_final"]],
                    }
                )
            return super().run(request)

    reasoner = LivePlanReasoner(3)
    result = lib.generate(
        Brief(topic=fixture["topic"], panels=3),
        tmp_path,
        feedback=fixture["feedback"],
        intelligence=reasoner,
        image_service=Renderer(),
    )
    assert result["status"] == "completed"
    request = next(item for item in reasoner.requests if item.output_schema["title"] == "AnchorAnalysis")
    assert "panel 1 of 3" in request.prompt
    assert "Other panels are not expected in this image" in request.prompt
    assert "TRANSFERABLE STYLE ONLY" in request.prompt
    target = request.prompt.split("CURRENT_FIRST_PANEL: ", 1)[1].split("\nBACKGROUND", 1)[0]
    assert json.loads(target) == fixture["parent_panels"][0]
    call = next(item for item in result["calls"] if item["task"] == "AnchorAnalysis")
    assert call["prompt"] == request.prompt
    assert call["prompt_sha256"] == digest(request.prompt.encode("utf-8"))


def test_freeform_render_prompt_and_references_remain_byte_identical(tmp_path: Path) -> None:
    record, storage = input_record(tmp_path, mode="freeform")
    renderer = Renderer()
    workflow = Workflow(record, storage, Reasoner(), renderer)
    anchor = png("purple")
    direction, corrections = "Low-angle view", "Warm dawn light"
    expected = (
        "Produce a finished image following the caller's direction. "
        "When revising, use the supplied revision image as the edit target and preserve what the request "
        "does not change. Do not add text or explanatory structure unless requested.\n"
        f"Image description: {record['plan']['description']}\n"
        f"Caller direction: {workflow.context()}\nAlternative: {direction}\nCorrections: {corrections}\n"
        'Reference roles in order: ["chosen-first-image-anchor", "style", "revision", "revision", "revision"]. '
        "Match the chosen anchor's visual properties across the series. Original style references remain "
        "applicable; revision images preserve subject/composition unless the caller changes them."
        " Content references, when present, supply subject identity/content only, never an unrequested aesthetic."
    )
    workflow.image("freeform.png", 1, direction, anchor, corrections)
    assert renderer.requests[0]["prompt"] == expected
    assert renderer.requests[0]["references"] == [anchor, *[data for _, data in workflow.refs(("style", "revision"))]]
    assert "panel_binding" not in record["calls"][-1]
    assert "prompt" not in record["calls"][-1]
