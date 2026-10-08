# Vision

Create and refine styled single- and multi-panel infographics with Amplifier Agent and image generation.

## Goals

What the tool must do well, as outcomes a reader can check. Each goal names a capability and what makes it done.

## Non-Goals

What the tool deliberately leaves to other tools, hosts, or the caller, so scope stays defensible.

## Principles

- The library is the tool. The CLI and any other surface are thin wrappers over it.
- Deterministic capabilities run with no model provider configured, and never refuse to load without one.
- The intelligence is behind an interface, so another implementation is a new module rather than a rewrite.
- The tool works on Windows, macOS, and Linux seamlessly.
