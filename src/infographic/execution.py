"""Shared finite image workflow, with a retained pause for candidate selection."""

from datetime import UTC, datetime
import json
import threading
from typing import Any

from filelock import FileLock, Timeout
from pydantic import BaseModel, ValidationError

from infographic.images import GeminiImages, ImageService, normalize
from infographic.intelligence.interface import Intelligence, default_intelligence
from infographic.intelligence.schemas import AgentRequest
from infographic.models import Alternatives, AnchorAnalysis, Brief, Choice, FreeformPlan, Plan, Review
from infographic.schemas import InfographicError
from infographic.storage import Store, digest


def launch(
    record: dict[str, Any],
    storage: Store,
    background: bool,
    intelligence: Intelligence | None,
    image_service: ImageService | None,
) -> None:
    guard = FileLock(str(storage.directory(record["id"]) / ".execution.lock"), timeout=0, thread_local=False)
    try:
        guard.acquire()
    except Timeout:
        return
    record = storage.read(record["id"])
    if record["status"] not in {"queued", "selection-admitted"}:
        guard.release()
        return
    args = (record, storage, intelligence or default_intelligence(), image_service or GeminiImages(), guard)
    if background:
        threading.Thread(target=execute, args=args, daemon=False, name=f"infographic-{record['id']}").start()
    else:
        execute(*args)


class Workflow:
    def __init__(self, record: dict[str, Any], storage: Store, reasoner: Intelligence, renderer: ImageService) -> None:
        self.record, self.storage, self.reasoner, self.renderer = record, storage, reasoner, renderer
        self.brief = Brief.model_validate(record["brief"])

    def save(self, status: str | None = None) -> None:
        if status:
            self.record["status"] = status
            if status in {"completed", "failed", "awaiting-selection"}:
                self.record["history"].append({"event": status, "at": datetime.now(UTC).isoformat()})
        self.storage.save(self.record)

    def ask(self, prompt: str, schema: type[BaseModel], images: list[bytes]) -> dict[str, Any]:
        call: dict[str, Any] = {
            "task": schema.__name__,
            "provider": self.brief.provider,
            "model": self.brief.model,
            "reasoning_effort": self.brief.reasoning_effort,
            "status": "started",
            "image_sha256": [digest(data) for data in images],
        }
        if schema is AnchorAnalysis:
            call.update({"prompt": prompt, "prompt_sha256": digest(prompt.encode("utf-8"))})
        self.record["calls"].append(call)
        self.save()
        result = self.reasoner.run(
            AgentRequest(
                prompt=prompt,
                output_schema=schema.model_json_schema(),
                images=images,
                provider=self.brief.provider,
                model=self.brief.model,
                reasoning_effort=self.brief.reasoning_effort,
                timeout_seconds=self.brief.timeout_seconds,
            )
        )
        call.update({"status": "failed" if result.error else "completed", "usage": result.usage, "error": result.error})
        self.save()
        if result.error or result.output is None:
            raise InfographicError(result.error or "Agent produced no structured result.")
        return schema.model_validate(result.output).model_dump()

    def refs(self, roles: tuple[str, ...]) -> list[tuple[str, bytes]]:
        return [
            (item["role"], self.storage.artifact(self.record["id"], item["name"]))
            for item in self.record["references"]
            if item["role"] in roles
        ]

    def context(self) -> str:
        # Execution options are not creative direction, and defaults must not
        # sneak a style or structure into a freeform image.
        data = self.brief.model_dump(
            exclude={
                "provider",
                "model",
                "reasoning_effort",
                "image_model",
                "timeout_seconds",
                "repair_rounds",
                "candidates",
                "selection",
            }
        )
        if self.brief.mode == "freeform":
            for key in ("panels", "layout", "representation"):
                data.pop(key, None)
        return json.dumps(
            {
                "request": data,
                "revision_request": self.record["feedback"],
                "previous_plan": self.record.get("parent_plan"),
            }
        )

    def plan(self) -> None:
        from infographic import lib

        self.save("planning")
        refs = self.refs(("content", "style", "revision"))
        roles = [role for role, _ in refs]
        if self.brief.mode == "freeform":
            prompt = (
                "Prepare a faithful image-generation description. Preserve the user's subject, treatment, exclusions "
                "and any requested edit to the supplied prior image. Add no headings, labels, diagram structure, "
                "or preset style unless the caller requested them. Choose shape from their direction when auto. "
                "Do not reinterpret a photographic or artistic request as an explanatory graphic."
            )
            schema: type[BaseModel] = FreeformPlan
        else:
            prompt = (
                "Plan an infographic with visual explanation, concise readable content and no invented facts. "
                "Choose layout and 1-6 panels from content density and narrative relationships when automatic. "
                "Explicit panel count/shape/layout/style and instructions in the caller's prose win over defaults. "
                "Keep explicit counts exactly. Explain density and layout decisions in density_rationale. "
                "Allocate content without omissions. For diorama representation use actors and props in a miniature "
                "scene, not a grid of unrelated icons. Curated style descriptions are suggestions, not extra constraints:\n"
                + json.dumps(lib.styles())
            )
            schema = Plan
        prompt += (
            "\nReference roles in image order: "
            + json.dumps(roles)
            + ". Content references supply facts/subjects, NOT their aesthetic. Style references supply visual "
            "treatment, NOT factual content. Revision images are the actual work being changed.\n" + self.context()
        )
        plan = self.ask(prompt, schema, [image for _, image in refs])
        if self.brief.mode == "infographic":
            if self.brief.panels is not None and len(plan["panels"]) != self.brief.panels:
                raise InfographicError("Planner did not honor the requested panel count. No image calls were made.")
            if self.brief.layout != "auto":
                plan["layout"] = self.brief.layout
        if self.brief.orientation != "auto":
            plan["orientation"] = self.brief.orientation
        self.record["plan"] = plan
        self.save()

    def image(self, name: str, panel: int, direction: str, anchor: bytes | None = None, corrections: str = "") -> bytes:
        plan = self.record["plan"]
        refs = self.refs(("content", "style", "revision") if self.brief.mode == "freeform" else ("style", "revision"))
        if anchor is not None:
            refs = [("chosen-first-image-anchor", anchor), *refs]
        if self.brief.mode == "freeform":
            prompt = (
                "Produce a finished image following the caller's direction. "
                "When revising, use the supplied revision image as the edit target and preserve what the request "
                "does not change. Do not add text or explanatory structure unless requested.\n"
                f"Image description: {plan['description']}\n"
            )
            prompt += (
                f"Caller direction: {self.context()}\nAlternative: {direction}\nCorrections: {corrections}\n"
                f"Reference roles in order: {json.dumps([role for role, _ in refs])}. "
                "Match the chosen anchor's visual properties across the series. Original style references remain "
                "applicable; revision images preserve subject/composition unless the caller changes them."
                " Content references, when present, supply subject identity/content only, never an unrequested aesthetic."
            )
            binding = None
        else:
            prompt, binding = self.guided_render_prompt(panel, direction, refs, corrections)
        call: dict[str, Any] = {
            "task": "image",
            "provider": "gemini",
            "model": self.brief.image_model,
            "artifact": name,
            "panel": panel,
            "status": "started",
            "reference_roles": [role for role, _ in refs],
            "reference_sha256": [digest(data) for _, data in refs],
        }
        if binding is not None:
            call.update(
                {
                    "prompt": prompt,
                    "prompt_sha256": digest(prompt.encode("utf-8")),
                    "panel_binding": binding,
                }
            )
        self.record["calls"].append(call)
        self.save(f"rendering-{name.removesuffix('.png')}")
        data = normalize(
            self.renderer.render(
                prompt,
                [data for _, data in refs],
                self.brief.image_model,
                {"portrait": "3:4", "landscape": "4:3", "square": "1:1"}[plan["orientation"]],
                self.brief.timeout_seconds,
            )
        )
        self.storage.add_image(self.record, name, data)
        call.update({"status": "completed", "output_sha256": digest(data)})
        self.save()
        return data

    def guided_render_prompt(
        self,
        panel: int,
        direction: str,
        refs: list[tuple[str, bytes]],
        corrections: str,
    ) -> tuple[str, dict[str, Any]]:
        plan = self.record["plan"]
        target = {"panel_index": panel, "panel_count": len(plan["panels"]), **plan["panels"][panel - 1]}
        prior_panels = (self.record.get("parent_plan") or {}).get("panels", [])
        reference_bindings = []
        prior_index = 0
        for image_index, (role, data) in enumerate(refs, 1):
            reference: dict[str, Any] = {"image_index": image_index, "role": role, "sha256": digest(data)}
            if role == "chosen-first-image-anchor":
                reference.update(
                    {
                        "use": "style-only",
                        "current_series_panel_index": 1,
                        "content_authority": "none; do not copy headings, actions or stage-specific objects",
                    }
                )
            elif role == "style":
                reference.update({"use": "original-style-only", "content_authority": "none"})
            elif role == "revision":
                prior_index += 1
                reference.update(
                    {
                        "use": "prior-series-context",
                        "source_image_index": prior_index,
                        "prior_panel_index": prior_index if prior_index <= len(prior_panels) else None,
                        "prior_title": prior_panels[prior_index - 1]["title"]
                        if prior_index <= len(prior_panels)
                        else None,
                        "current_panel_correspondence": "not-assumed; use current content and semantic subject, never ordinal position",
                    }
                )
            reference_bindings.append(reference)
        binding = {
            "schema": "guided-panel-binding/v1",
            "target": target,
            "current_series_allocation_context_only": [
                {"panel_index": index, "title": item["title"], "content": item["content"]}
                for index, item in enumerate(plan["panels"], 1)
            ],
            "reference_images_in_order": reference_bindings,
            "transferable_style_only": self.record.get("observed_style", plan["style_brief"]),
            "series_context_not_copy": {
                "caller_context": json.loads(self.context()),
                "series_alternative": direction,
                "review_corrections": corrections,
            },
        }
        prompt = (
            "Render EXACTLY ONE finished infographic panel, identified by target.panel_index out of "
            "target.panel_count. Do not render the whole series or stack multiple stages in this image. "
            "CURRENT CONTENT AUTHORITY: target.title is this panel's heading, target.content its action copy, "
            "and target.visual its subject and spatial-placement directions. Preserve these words and placements. "
            "Never replace this heading or import another panel's actions because a global revision mentions them. "
            "The current plan has already allocated stage-specific edits; 'final panel' is not 'this panel' "
            "unless the indices agree. Keep the target's explicit beneath/above/beside relationships intact. "
            "The current_series_allocation_context_only map disambiguates stages; its other entries are NOT "
            "text to reproduce here. Original brief, global revision request, OLD plan, review corrections and "
            "series alternative are BACKGROUND CONTEXT, not competing copy lists. Apply only corrections relevant "
            "to this target. A series alternative saying 'three stacked scenes' describes the series, never "
            "overrides this single-panel boundary. Preserve caller-wide language, exclusions, style and constraints "
            "without moving stage-specific edits across panels. No invented measurements. "
            "A diorama remains a coherent miniature scene for this target, not an entire multi-stage poster. "
            "Reference labels identify actual image order and PRIOR source indices/titles, not current edit slots. "
            "Panels may be reordered, merged or split: use relevant prior subjects as context without assuming "
            "same-index correspondence or copying obsolete text. The chosen first-image anchor and original "
            "style references supply STYLE ONLY: palette, type treatment, materials, lighting and visual grammar, "
            "not their headings, action text or stage-specific props. Likewise, any literal headings, props or "
            "whole-series observations in transferable_style_only are not content instructions. "
            "If aesthetic is unspecified, the alternative may vary its treatment within this target scope.\n"
            "GUIDED_PANEL_BINDING_JSON:\n" + json.dumps(binding)
        )
        return prompt, binding

    def candidates(self) -> None:
        count = self.brief.candidates
        options = [{"label": "Requested direction", "difference": "Single requested result", "direction": ""}]
        if count > 1:
            options = self.ask(
                f"Propose exactly {count} meaningfully different visual approaches to this SAME request. "
                "Preserve all explicit constraints and content. If style is unspecified, contrast aesthetics; "
                "if style is specified, contrast composition, visual metaphor or environment instead. "
                "An original style-reference image also fixes the aesthetic; vary composition in that case. "
                "Never introduce text when prohibited. Return concrete differences, not cosmetic synonyms.\n"
                + self.context()
                + "\nPlan: "
                + json.dumps(self.record["plan"])
                + "\nStyle references supplied: "
                + str(bool(self.refs(("style",)))),
                Alternatives,
                [],
            )["options"]
            if len(options) != count or len({item["direction"] for item in options}) != count:
                raise InfographicError(
                    "Planner did not provide the requested distinct alternatives. No candidate images were made."
                )
        for index, option in enumerate(options, 1):
            name = f"candidate-{index}.png"
            data = self.image(name, 1, option["direction"])
            candidate = {"id": index, **option, "image": name, "sha256": digest(data)}
            self.record["candidates"].append(candidate)
            self.save()
        if count > 1 and self.brief.selection == "manual":
            self.save("awaiting-selection")
            return
        if count == 1:
            choice = {"candidate": 1, "rationale": "Only one candidate was requested.", "actor": "single-requested"}
        else:
            choice = self.ask(
                "Select the candidate best satisfying the caller's explicit direction. Judge the ACTUAL images "
                "in candidate order. Explain the choice; this is automatic selection, never human approval.\n"
                + self.context(),
                Choice,
                [
                    self.storage.artifact(self.record["id"], candidate["image"])
                    for candidate in self.record["candidates"]
                ],
            )
            if choice["candidate"] > count:
                raise InfographicError("Automatic selection named a nonexistent candidate.")
            choice["actor"] = "automatic-requested"
        self.record["selection"] = choice
        self.save()

    def finish(self) -> None:
        from infographic import lib

        selection = self.record["selection"]
        candidate = self.record["candidates"][selection["candidate"] - 1]
        plan = self.record["plan"]
        count = len(plan["panels"]) if self.brief.mode == "infographic" else 1
        first = self.storage.artifact(self.record["id"], candidate["image"])
        corrections = ""
        for attempt in range(self.brief.repair_rounds + 1):
            entry: dict[str, Any] = {"index": attempt, "panels": [], "review": None}
            self.record["attempts"].append(entry)
            if attempt:
                first = self.image(f"attempt-{attempt}-panel-1.png", 1, candidate["direction"], first, corrections)
                first_name = f"attempt-{attempt}-panel-1.png"
            else:
                first_name = "attempt-0-panel-1.png"
                self.storage.add_image(self.record, first_name, first)
            entry["panels"].append(first_name)
            rendered = [first]
            if self.brief.mode == "infographic":
                self.save("analyzing-chosen-anchor")
                analysis = self.ask(
                    f"Analyze the ACTUAL chosen first panel ONLY: panel 1 of {count}. "
                    "Other panels are not expected in this image; do not flag their absence. "
                    "Evaluate heading, actions and placement against CURRENT_FIRST_PANEL below, not another stage's "
                    "edits in the background context. Describe TRANSFERABLE STYLE ONLY in observed_style: palette, "
                    "typographic treatment (not literal heading text), materials, texture, lighting and visual grammar. "
                    "Do not include stage-specific props, scene content or whole-series completeness claims in style. "
                    "Replace speculative style with observed properties; put target-content mismatches in discrepancies. "
                    "Do not invent properties from the proposed plan.\n"
                    f"CURRENT_FIRST_PANEL: {json.dumps(plan['panels'][0])}\n"
                    f"BACKGROUND_SERIES_CONTEXT_NOT_TARGET_COPY: {self.context()}",
                    AnchorAnalysis,
                    [first],
                )
                entry["anchor_analysis"] = analysis
                self.record["observed_style"] = analysis["observed_style"]
                self.save()
            for index in range(2, count + 1):
                name = f"attempt-{attempt}-panel-{index}.png"
                rendered.append(self.image(name, index, candidate["direction"], first, corrections))
                entry["panels"].append(name)
                self.save()
            self.save("assembling")
            composite = lib.stitch_bytes(rendered, plan.get("layout", "vertical")) if count > 1 else rendered[0]
            name = f"attempt-{attempt}-composite.png"
            self.storage.add_image(self.record, name, composite)
            entry["composite"] = name
            self.record["composite"] = name
            self.save("reviewing")
            criteria = (
                "Assess composition, subject, treatment and requested changes/exclusions. Do NOT require labels, "
                "headings, diagrams, explanatory text or infographic qualities."
                if self.brief.mode == "freeform"
                else "Assess content, readability, visual explanation, explicit direction and cross-panel consistency."
            )
            review = self.ask(
                "Review the ACTUAL supplied images in order against the caller's request. "
                + criteria
                + " Report only observed material issues with actionable corrections. This is not a perfection "
                "contest or external fact check. Use met only without material issues.\n"
                + self.context()
                + "\nPlan: "
                + json.dumps(plan),
                Review,
                rendered,
            )
            if review["issues"]:
                review["verdict"] = "needs-work"
            entry["review"] = review
            self.save()
            if review["verdict"] == "met":
                break
            corrections = json.dumps(review)
        self.save("completed")


def execute(record: dict[str, Any], storage: Store, reasoner: Intelligence, renderer: ImageService, guard: Any) -> None:
    workflow = Workflow(record, storage, reasoner, renderer)
    try:
        reasoner.preflight()
        renderer.preflight()
        if not record.get("plan"):
            workflow.plan()
            workflow.candidates()
        if record["selection"]:
            workflow.finish()
    except Exception as exc:
        if record["calls"] and record["calls"][-1].get("status") == "started":
            record["calls"][-1]["status"] = "failed-or-unknown"
        if isinstance(exc, InfographicError):
            record["error"] = str(exc)
        elif isinstance(exc, ValidationError):
            record["error"] = (
                "Model output did not satisfy product validation. Inspect partial artifacts and make an explicit new request."
            )
        else:
            record["error"] = (
                f"Execution failed ({type(exc).__name__}). Inspect partial artifacts and check dependencies/store permissions."
            )
        workflow.save("failed")
    finally:
        guard.release()
