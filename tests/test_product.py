"""Provider-free functional tests. Raster fixtures are NOT live generated output."""

from io import BytesIO
import json
from pathlib import Path
from typing import Any

from PIL import Image
import pytest

from infographic import lib
from infographic.images import normalize
from infographic.intelligence.schemas import AgentRequest, AgentResult
from infographic.models import Brief
from infographic.schemas import InfographicError
from infographic.storage import digest


def png(color: str = "navy", size: tuple[int, int] = (60, 80)) -> bytes:
    output = BytesIO()
    Image.new("RGB", size, color).save(output, format="PNG")
    return output.getvalue()


class Reasoner:
    implementation = "test-fixture"

    def __init__(self, panels: int = 2, verdict: str = "met", fail_review: bool = False) -> None:
        self.panels = panels
        self.verdict = verdict
        self.fail_review = fail_review
        self.requests: list[AgentRequest] = []

    def preflight(self) -> None:
        pass

    def run(self, request: AgentRequest) -> AgentResult:
        self.requests.append(request)
        if request.output_schema["title"] == "AnchorAnalysis":
            return AgentResult(
                output={
                    "observed_style": "Observed teal objects with cream background and ink type.",
                    "discrepancies": [],
                }
            )
        if request.output_schema["title"] == "FreeformPlan":
            return AgentResult(
                output={
                    "description": "Watercolor coastal observatory, no text, at blue hour.",
                    "orientation": "landscape",
                }
            )
        if request.output_schema["title"] == "Alternatives":
            count = 3 if "exactly 3" in request.prompt else 2
            return AgentResult(
                output={
                    "options": [
                        {
                            "label": f"Option {index}",
                            "difference": f"Distinct composition {index}",
                            "direction": f"Composition angle {index}",
                        }
                        for index in range(1, count + 1)
                    ]
                }
            )
        if request.output_schema["title"] == "Choice":
            return AgentResult(output={"candidate": 2, "rationale": "Fixture choice based on supplied pixels."})
        if request.output_schema["title"] == "Plan":
            return AgentResult(
                output={
                    "title": "Heat pumps",
                    "style_brief": "Editorial navy, cream and simple labelled arrows.",
                    "panels": [
                        {"title": f"Stage {index}", "content": ["Heat moves"], "visual": "A flow diagram"}
                        for index in range(self.panels)
                    ],
                    "factual_caveats": ["No external research performed."],
                }
            )
        if self.fail_review:
            return AgentResult(error="Review provider unavailable. Check service availability.")
        return AgentResult(
            output={
                "verdict": self.verdict,
                "summary": "Fixture review only.",
                "issues": []
                if self.verdict == "met"
                else [
                    {"panel": 1, "category": "readability", "detail": "Small labels", "correction": "Larger type"},
                ],
            }
        )


class Renderer:
    def __init__(self, fail_at: int | None = None) -> None:
        self.requests: list[dict[str, Any]] = []
        self.fail_at = fail_at

    def preflight(self) -> None:
        pass

    def render(self, prompt: str, references: list[bytes], model: str, ratio: str, timeout: int) -> bytes:
        self.requests.append(
            {"prompt": prompt, "references": references, "model": model, "ratio": ratio, "timeout": timeout}
        )
        if len(self.requests) == self.fail_at:
            raise InfographicError("Image service unavailable; check quota.")
        return png("navy" if len(self.requests) % 2 else "teal")


def test_multiplayer_pipeline_uses_actual_anchor_and_actual_review_pixels(tmp_path: Path) -> None:
    reasoner, renderer = Reasoner(), Renderer()
    reference = png("red")
    brief = Brief(
        topic="Heat pumps", panels=2, constraints="Keep this exact phrase", layout="horizontal", orientation="landscape"
    )
    result = lib.generate(brief, tmp_path, [reference], intelligence=reasoner, image_service=renderer)
    assert result["status"] == "completed"
    assert len(reasoner.requests) == 3
    assert len(renderer.requests) == 2
    anchor = lib.artifact(result["id"], "attempt-0-panel-1.png", tmp_path)
    assert renderer.requests[1]["references"][0] == anchor
    assert renderer.requests[0]["references"] == []
    assert reasoner.requests[0].images == [normalize(reference)]
    assert all(call["ratio"] == "4:3" for call in renderer.requests)
    assert "Keep this exact phrase" in renderer.requests[1]["prompt"]
    assert reasoner.requests[-1].images == [anchor, lib.artifact(result["id"], "attempt-0-panel-2.png", tmp_path)]
    image = Image.open(BytesIO(lib.artifact(result["id"], result["composite"], tmp_path)))
    assert image.size == (120, 80)
    assert lib.inspect(result["id"], tmp_path) == result
    assert len(lib.list_results(tmp_path)) == 1
    assert result["reference_input_sha256"] == [digest(reference)]
    assert len([call for call in result["calls"] if call["task"] == "image"]) == 2


def test_exact_retry_never_reexecutes_and_changed_inputs_refused(tmp_path: Path) -> None:
    reasoner, renderer = Reasoner(1), Renderer()
    request_id = "a" * 32
    brief = Brief(topic="Example")
    result = lib.generate(brief, tmp_path, request_id=request_id, intelligence=reasoner, image_service=renderer)
    assert lib.generate(brief, tmp_path, request_id=request_id, intelligence=reasoner, image_service=renderer) == result
    assert len(renderer.requests) == 1
    with pytest.raises(InfographicError, match="different inputs"):
        lib.generate(Brief(topic="Changed"), tmp_path, request_id=request_id)


def test_refinement_and_adjacent_cycle_preserve_original_bytes(tmp_path: Path) -> None:
    reasoner, renderer = Reasoner(), Renderer()
    first = lib.generate(Brief(topic="Heat", panels=2), tmp_path, intelligence=reasoner, image_service=renderer)
    original_record = (tmp_path / first["id"] / "result.json").read_bytes()
    child = lib.refine(first["id"], "Bigger labels", tmp_path, intelligence=reasoner, image_service=renderer)
    grandchild = lib.refine(
        child["id"], "Keep palette, simplify arrows", tmp_path, intelligence=reasoner, image_service=renderer
    )
    assert child["parent_id"] == first["id"]
    assert grandchild["parent_id"] == child["id"]
    assert grandchild["brief"] == first["brief"]
    assert (tmp_path / first["id"] / "result.json").read_bytes() == original_record
    assert child["parent_plan"] == first["plan"]
    assert lib.inspect(first["id"], tmp_path) == first
    assert len(lib.list_results(tmp_path)) == 3


def test_explicit_structural_refinement_overrides(tmp_path: Path) -> None:
    first = lib.generate(Brief(topic="Heat", panels=2), tmp_path, intelligence=Reasoner(), image_service=Renderer())
    child = lib.refine(
        first["id"],
        "Condense to one panel",
        tmp_path,
        {"panels": 1, "orientation": "square", "layout": "grid"},
        intelligence=Reasoner(1),
        image_service=Renderer(),
    )
    assert child["status"] == "completed"
    assert child["brief"]["panels"] == 1
    assert len(child["attempts"][0]["panels"]) == 1
    assert lib.inspect(first["id"], tmp_path)["brief"]["panels"] == 2


def test_bounded_repair_retains_first_attempt(tmp_path: Path) -> None:
    reasoner, renderer = Reasoner(verdict="needs-work"), Renderer()
    result = lib.generate(
        Brief(topic="Heat", panels=2, repair_rounds=1), tmp_path, intelligence=reasoner, image_service=renderer
    )
    assert result["status"] == "completed"
    assert len(result["attempts"]) == 2
    assert result["attempts"][-1]["review"]["verdict"] == "needs-work"
    assert len(renderer.requests) == 4
    assert len(reasoner.requests) == 5
    assert "Larger type" in renderer.requests[2]["prompt"]
    lib.inspect(result["id"], tmp_path)


@pytest.mark.parametrize("failure", ["image", "review"])
def test_partial_failure_is_retained_and_retry_is_read_only(tmp_path: Path, failure: str) -> None:
    renderer = Renderer(fail_at=2 if failure == "image" else None)
    reasoner = Reasoner(fail_review=failure == "review")
    brief = Brief(topic="Heat", panels=2)
    result = lib.generate(brief, tmp_path, request_id="b" * 32, intelligence=reasoner, image_service=renderer)
    assert result["status"] == "failed"
    assert result["error"]
    assert len(result["files"]) >= 1
    assert lib.generate(brief, tmp_path, request_id="b" * 32) == result
    lib.inspect(result["id"], tmp_path)
    with pytest.raises(InfographicError, match="completed"):
        lib.refine(result["id"], "retry", tmp_path)


def test_wrong_panel_count_fails_before_images(tmp_path: Path) -> None:
    renderer = Renderer()
    result = lib.generate(Brief(topic="Heat", panels=2), tmp_path, intelligence=Reasoner(1), image_service=renderer)
    assert result["status"] == "failed"
    assert not renderer.requests
    assert "panel count" in result["error"]


def test_bad_model_schema_fails_retained(tmp_path: Path) -> None:
    class BadReasoner(Reasoner):
        def run(self, request: AgentRequest) -> AgentResult:
            return AgentResult(output={"not": "a plan"})

    result = lib.generate(Brief(topic="Heat"), tmp_path, intelligence=BadReasoner(), image_service=Renderer())
    assert result["status"] == "failed"
    assert "validation" in result["error"]


@pytest.mark.parametrize("run_id", ["../private", "a/b", "", "ABC", "x" * 32])
def test_store_rejects_arbitrary_paths(tmp_path: Path, run_id: str) -> None:
    with pytest.raises(InfographicError, match="Invalid result ID"):
        lib.inspect(run_id, tmp_path)


def test_integrity_and_symlink_denials(tmp_path: Path) -> None:
    result = lib.generate(Brief(topic="Heat"), tmp_path, intelligence=Reasoner(1), image_service=Renderer())
    name = result["composite"]
    path = tmp_path / result["id"] / name
    original = path.read_bytes()
    path.write_bytes(b"changed")
    with pytest.raises(InfographicError, match="integrity"):
        lib.artifact(result["id"], name, tmp_path)
    path.unlink()
    outside = tmp_path / "outside.png"
    outside.write_bytes(original)
    path.symlink_to(outside)
    with pytest.raises(InfographicError, match="symlink"):
        lib.artifact(result["id"], name, tmp_path)
    with pytest.raises(InfographicError, match="not listed"):
        lib.artifact(result["id"], "../../secret", tmp_path)


@pytest.mark.parametrize(("layout", "size"), [("vertical", (60, 240)), ("horizontal", (180, 80)), ("grid", (120, 160))])
def test_stitch_layouts(layout: str, size: tuple[int, int]) -> None:
    data = lib.stitch_bytes([png(), png(), png()], layout)
    assert Image.open(BytesIO(data)).size == size


def test_bad_and_large_image_denied() -> None:
    with pytest.raises(InfographicError, match="decodable"):
        normalize(b"not an image")
    with pytest.raises(InfographicError, match="12 MiB"):
        normalize(b"a" * (12 * 1024 * 1024 + 1))
    with pytest.raises(InfographicError, match="1 to 6"):
        lib.stitch_bytes([])


def test_deterministic_commands_need_no_keys(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    assert lib.styles()
    assert lib.check()["image_service"]["key_present"] is False
    assert lib.list_results(tmp_path) == []
    assert lib.load_manifest().name == "infographic"
    assert json.loads(lib.load_manifest().model_dump_json())["smart_tool_format"] == 1
