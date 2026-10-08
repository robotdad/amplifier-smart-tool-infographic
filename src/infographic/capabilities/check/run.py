"""Local readiness, not a live provider acceptance test."""

from importlib.metadata import version
import os
import shutil
from typing import Any


def check() -> dict[str, Any]:
    return {
        "packages": {
            name: version(name)
            for name in ("infographic", "amplifier-agent", "amplifier-agent-engine", "google-genai", "Pillow")
        },
        "reasoning": {
            "openai": {"environment_key_present": bool(os.getenv("OPENAI_API_KEY"))},
            "anthropic": {"environment_key_present": bool(os.getenv("ANTHROPIC_API_KEY"))},
            "gemini": {"environment_key_present": bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))},
            "chatgpt": {"authentication": "Agent OAuth cache; not checked"},
            "github": {
                "token_present": any(
                    os.getenv(key)
                    for key in ("COPILOT_AGENT_TOKEN", "COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN")
                ),
                "gh_available": bool(shutil.which("gh")),
            },
        },
        "image_service": {
            "provider": "gemini",
            "key_present": bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")),
        },
        "live_validation": "not performed; key presence does not prove authentication, quota, model access or image support",
    }
