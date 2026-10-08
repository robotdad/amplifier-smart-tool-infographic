---
name: infographic
description: >-
  Create and refine styled single- and multi-panel infographics with Amplifier Agent and image generation. Drive it from the command line as `infographic`, or from Python through
  `infographic.lib`. Triggers on "infographic".
license: MIT
metadata:
  repository: https://github.com/robotdad/amplifier-smart-tool-infographic
---

# Using infographic

Create and refine styled single- and multi-panel infographics with Amplifier Agent and image generation.

## Install

```bash
# as a CLI
uv tool install git+https://github.com/robotdad/amplifier-smart-tool-infographic

# as a library, from another project
uv add "infographic @ git+https://github.com/robotdad/amplifier-smart-tool-infographic"

# once, without installing
uvx --from git+https://github.com/robotdad/amplifier-smart-tool-infographic infographic --help
```
## Use it

Run `infographic --help`. It prints the tool's skill: when to use it, every capability, sharp
edges, and which files to read. Follow it. Then read the capability's own skill with
`infographic <command> --help` before calling it: it carries the arguments, a worked
invocation, the result, and the failures. Never work from memory.
