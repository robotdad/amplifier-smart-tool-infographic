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
  - name: gh
    purpose: >-
      Generates the token that signs in to GitHub Copilot. Without it, the model-backed
      capabilities cannot authenticate.
    optional: true
    install: https://cli.github.com/
  - name: github-copilot-subscription
    purpose: >-
      A Copilot subscription on the account signed in to gh powers the model-backed
      capabilities. Without it, only the deterministic capabilities run.
    optional: true
    install: https://github.com/github/copilot-cli#prerequisites
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

Deterministic capabilities need only `uv`. Model-backed capabilities run through GitHub
Copilot, signed in as the GitHub CLI's user: `gh` must be installed and `gh auth login`
completed with an account that has a Copilot subscription. Without that, a model-backed
capability fails immediately and names what to configure; it never falls back to a
deterministic answer.

Runs on Linux, macOS, and Windows.

## Straight and smart paths

Deterministic capabilities run with no provider configured. Model-backed capabilities go
through GitHub Copilot, signed in as the GitHub CLI's user, and say so in their help text.

## Output and failure contract

Results go to stdout, diagnostics to stderr. A failure prints a message naming what went
wrong and how to fix it, and exits non-zero: 1 for a failure the tool can name, 2 for a
bad invocation. Never treat an empty result as success.

## Choosing a surface

Import the library from Python. Shell out to the CLI from anything that cannot import
Python in-process: a shell script, a CI job, or an agent that can run commands but not
load a Python object. Both reach the same capabilities.
