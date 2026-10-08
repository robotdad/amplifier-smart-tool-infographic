"""Mocked public SDK boundary checks, not live provider support evidence."""

import asyncio
import base64
from types import SimpleNamespace
from typing import Any

from amplifier_agent import AgentOptions, ImagePart, TextPart, TurnResult
import pytest
from test_product import png

from infographic.images import GeminiImages
from infographic.intelligence.agent import PROVIDERS, AgentIntelligence
from infographic.intelligence.schemas import AgentRequest
from infographic.schemas import InfographicError


@pytest.mark.parametrize("provider", list(PROVIDERS))
def test_public_agent_selection_tool_denial_multimodal_and_config_isolation(
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
) -> None:
    import amplifier_agent

    observed: dict[str, Any] = {}
    monkeypatch.setenv("AMPLIFIER_AGENT_CONFIG", "/unrelated/host/config.json")
    monkeypatch.setenv("AMPLIFIER_AGENT_MODEL", "wrong-model")

    class FakeSession:
        async def __aenter__(self) -> Any:
            return self

        async def __aexit__(self, *args: Any) -> None:
            pass

        async def run(self, value: Any) -> TurnResult:
            observed["content"] = value.content
            return TurnResult(state="success", content=[TextPart('{"ok":true}')])

    class FakeAgent:
        async def __aenter__(self) -> Any:
            return self

        async def __aexit__(self, *args: Any) -> None:
            pass

        async def create_session(self, options: Any) -> Any:
            observed["session"] = options
            return FakeSession()

    async def create(options: AgentOptions) -> Any:
        observed["options"] = options
        return FakeAgent()

    monkeypatch.setattr(amplifier_agent, "create_agent", create)
    image = png()
    result = asyncio.run(
        AgentIntelligence()._run(
            AgentRequest(
                prompt="Review actual pixels",
                provider=provider,
                model="explicit-model",
                output_schema={"type": "object", "required": ["ok"], "properties": {"ok": {"type": "boolean"}}},
                images=[image],
            )
        )
    )
    assert result.output == {"ok": True}
    options = observed["options"]
    assert options.provider == PROVIDERS[provider]
    assert options.model == "explicit-model"
    assert options.sessions_directory
    assert options.working_directory
    assert options.reasoning_effort == "medium"
    assert options.tools == options.skills == options.mcp_servers == []
    assert options.approvals == "deny"
    assert observed["session"].persistence == "ephemeral"
    part = observed["content"][1]
    assert isinstance(part, ImagePart)
    assert base64.b64decode(part.data) == image


@pytest.mark.parametrize("provider", list(PROVIDERS))
def test_agent_failure_redacts_exception_and_does_not_fallback(monkeypatch: pytest.MonkeyPatch, provider: str) -> None:
    import amplifier_agent

    calls = []

    async def fail(options: AgentOptions) -> Any:
        calls.append(options.provider)
        raise RuntimeError("secret-token-must-not-leak")

    monkeypatch.setattr(amplifier_agent, "create_agent", fail)
    result = asyncio.run(
        AgentIntelligence()._run(AgentRequest(prompt="x", provider=provider, output_schema={"type": "object"}))
    )
    assert result.error
    assert "secret-token" not in result.error
    assert calls == [PROVIDERS[provider]]


def test_gemini_actual_sdk_content_shape_no_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    from google import genai

    observed: dict[str, Any] = {}
    image = png()

    class Client:
        def __init__(self, **kwargs: Any) -> None:
            observed["init"] = kwargs
            self.models = self

        def __enter__(self) -> Any:
            return self

        def __exit__(self, *args: Any) -> None:
            pass

        def generate_content(self, **kwargs: Any) -> Any:
            observed["request"] = kwargs
            return SimpleNamespace(parts=[SimpleNamespace(thought=False, inline_data=SimpleNamespace(data=image))])

    monkeypatch.setattr(genai, "Client", Client)
    monkeypatch.setenv("GEMINI_API_KEY", "not-a-real-key")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    result = GeminiImages().render("Prompt", [image], "explicit-image-model", "4:3", 30)
    assert result == image
    request = observed["request"]
    assert request["model"] == "explicit-image-model"
    assert request["config"].image_config.aspect_ratio == "4:3"
    assert request["contents"].parts[1].inline_data.data == image
    assert observed["init"]["http_options"].retry_options.attempts == 1
    assert observed["init"]["http_options"].timeout == 30000


def test_gemini_missing_credentials_actionable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(InfographicError, match="every reasoning provider"):
        GeminiImages().preflight()
