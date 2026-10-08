"""Public product records."""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from infographic.schemas import DEFAULT_INTELLIGENCE_MODEL, ReasoningEffort

DEFAULT_IMAGE_MODEL = "gemini-3.1-flash-image-preview"
Provider = Literal["openai", "anthropic", "gemini", "chatgpt", "github"]
DEFAULT_MODELS = {
    "openai": DEFAULT_INTELLIGENCE_MODEL,
    "anthropic": "claude-haiku-5-5",
    "gemini": "gemini-3.8-flash",
    "chatgpt": DEFAULT_INTELLIGENCE_MODEL,
    "github": "gpt-5.4",
}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Brief(StrictModel):
    mode: Literal["infographic", "freeform"] = "infographic"
    topic: str = Field(min_length=1, max_length=12000)
    source: str = Field(default="", max_length=30000)
    panels: int | None = Field(default=None, ge=1, le=6)
    orientation: Literal["auto", "portrait", "landscape", "square"] = "auto"
    layout: Literal["auto", "vertical", "horizontal", "grid"] = "auto"
    style: str = Field(default="", max_length=2000)
    representation: Literal["auto", "diagram", "scene", "diorama"] = "auto"
    candidates: int = Field(default=1, ge=1, le=3)
    selection: Literal["manual", "auto"] = "manual"
    constraints: str = Field(default="", max_length=4000)
    provider: Provider = "openai"
    model: str = Field(default="", max_length=150)
    reasoning_effort: ReasoningEffort = "medium"
    image_model: str = Field(default=DEFAULT_IMAGE_MODEL, min_length=1, max_length=150)
    timeout_seconds: int = Field(default=180, ge=10, le=600)
    repair_rounds: int = Field(default=0, ge=0, le=1)

    @model_validator(mode="after")
    def resolve_defaults(self) -> Self:
        if not self.model:
            self.model = DEFAULT_MODELS[self.provider]
        if self.mode == "freeform" and self.panels not in (None, 1):
            raise ValueError("Freeform makes one image, not a panel sequence; use candidates for alternatives.")
        return self


class Panel(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    content: list[str] = Field(min_length=1, max_length=8)
    visual: str = Field(min_length=1, max_length=2000)


class Plan(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    style_brief: str = Field(min_length=1, max_length=3000)
    panels: list[Panel] = Field(min_length=1, max_length=6)
    factual_caveats: list[str] = Field(default_factory=list, max_length=20)
    layout: Literal["vertical", "horizontal", "grid"] = "vertical"
    orientation: Literal["portrait", "landscape", "square"] = "portrait"
    density_rationale: str = Field(default="", max_length=3000)


class FreeformPlan(StrictModel):
    description: str = Field(min_length=1, max_length=6000)
    orientation: Literal["portrait", "landscape", "square"]


class Alternative(StrictModel):
    label: str = Field(min_length=1, max_length=100)
    difference: str = Field(min_length=1, max_length=2000)
    direction: str = Field(min_length=1, max_length=3000)


class Alternatives(StrictModel):
    options: list[Alternative] = Field(min_length=2, max_length=3)


class AnchorAnalysis(StrictModel):
    observed_style: str = Field(min_length=1, max_length=4000)
    discrepancies: list[str] = Field(max_length=20)


class Choice(StrictModel):
    candidate: int = Field(ge=1, le=3)
    rationale: str = Field(min_length=1, max_length=2000)


class Issue(StrictModel):
    panel: int = Field(ge=0, le=6, description="1-based panel number, or 0 for the whole set")
    category: Literal["content", "readability", "visual-explanation", "fidelity", "consistency", "composition"]
    detail: str = Field(min_length=1, max_length=2000)
    correction: str = Field(min_length=1, max_length=2000)


class Review(StrictModel):
    verdict: Literal["met", "needs-work"]
    summary: str = Field(min_length=1, max_length=3000)
    issues: list[Issue] = Field(max_length=30)
