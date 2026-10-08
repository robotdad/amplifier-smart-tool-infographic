---
smart_tool_format: 1
name: infographic
version: 0.1.0
description: >-
  Create and refine styled single- and multi-panel infographics with Amplifier Agent and image generation
use_cases:
  - >-
    Create and refine styled single- and multi-panel infographics with Amplifier Agent and image generation
platforms:
  - linux
  - macos
  - windows
requires:
  - name: reasoning-provider
    purpose: Amplifier Agent reasoning credentials or subscription login for the selected provider.
    optional: true
    install: https://github.com/microsoft/amplifier-agent/blob/main/docs/providers.md
  - name: gemini-image-service
    purpose: GOOGLE_API_KEY or GEMINI_API_KEY for image generation, independent of reasoning provider.
    optional: true
    install: https://ai.google.dev/gemini-api/docs/image-generation
---

Create and refine styled single- and multi-panel infographics with Amplifier Agent and image generation.

**The library is the tool.** `infographic.lib` holds every capability. The CLI is a thin
wrapper over it, so anything you can do from the shell you can also do from Python.

## When to reach for it

- Create and refine styled single- and multi-panel infographics with Amplifier Agent and image generation.

## Before writing code

Every capability has its own skill. Read `infographic <command> --help` before calling it: it
carries the arguments, a worked invocation, the result, and the failures. Do not fill gaps
from memory. The library source beside this file, `lib.py`, carries the signatures. The
repository's `docs/01-library.md` and `docs/02-cli.md` carry the rest.

## Install

```bash
# as a CLI
uv tool install git+https://github.com/robotdad/amplifier-smart-tool-infographic

# as a library, from another project
uv add "infographic @ git+https://github.com/robotdad/amplifier-smart-tool-infographic"

# once, without installing
uvx --from git+https://github.com/robotdad/amplifier-smart-tool-infographic infographic --help
```
Verify with `infographic manifest`, which needs no credentials.

## Prerequisites

Deterministic capabilities require no provider. Reasoning runs through public Amplifier Agent:
`openai`, `anthropic`, `gemini`, `chatgpt` or `github`, with an explicit compatible model.
OpenAI/Anthropic/Gemini use their environment API keys; ChatGPT uses Agent-compatible OAuth;
GitHub uses a documented Copilot token variable or cached SDK login and entitlement. Images always use the separate Gemini service.
`check` reports local presence, not live authentication. Credentials are never printed.

Portable Python implementation; Linux checked locally. Windows and macOS parity is not yet verified.

## Straight and smart paths

Start with `serve` for a local browser experience, or `generate` for the command line.
Inspect the retained plan, panels, composite, hashes and visual review; `refine` creates a child result.
No provider fallback, shell tools, arbitrary model writes or automatic crash replay.
One optional repair round is caller-controlled. Execution completion is not a quality verdict.
Agent binding and engine are 0.22.0. All routes use explicit public reasoning-effort options.
Use `--mode freeform` for caller-directed artwork without infographic structure.
Infographic mode offers automatic density/layout planning, curated/custom styles and dioramas.
Request 2-3 candidates for alternatives; manual choice pauses until `select`.
Original style references stay alongside the analyzed first-image anchor.
Browser supports role-specific reference uploads and structural/provider refinement controls.
Interrupted runs retain evidence; `close-interrupted` acknowledges stopped work without replay.

## Output and failure contract

Results go to stdout, diagnostics to stderr. A failure prints a message naming what went
wrong and how to fix it, and exits non-zero: 1 for a failure the tool can name, 2 for a
bad invocation. Never treat an empty result as success.

## Choosing a surface

Import the library from Python. Shell out to the CLI from anything that cannot import
Python in-process: a shell script, a CI job, or an agent that can run commands but not
load a Python object. Both reach the same capabilities.
