"""Bounded, tool-free requests to the public Agent API."""

from typing import Any

from pydantic import BaseModel, Field

from infographic.schemas import DEFAULT_INTELLIGENCE_MODEL, ReasoningEffort


class AgentRequest(BaseModel):
    prompt: str
    provider: str = "openai"
    model: str = DEFAULT_INTELLIGENCE_MODEL
    output_schema: dict[str, Any]
    images: list[bytes] = Field(default_factory=list)
    reasoning_effort: ReasoningEffort = "medium"
    timeout_seconds: int = Field(default=180, ge=10, le=600)


class AgentResult(BaseModel):
    output: dict[str, Any] | None = None
    text: str = ""
    error: str | None = None
    usage: dict[str, Any] | None = None
