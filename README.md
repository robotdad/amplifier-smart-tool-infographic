# Infographic Smart Tool

Create and refine styled infographics and freeform images with Amplifier Agent and image generation.

Infographic is a [Smart Tool](https://github.com/microsoft/amplifier-smart-tools): a library with a thin CLI over it, whose model-backed capabilities sit behind an interface.

## Installation

Prerequisites:
- [uv](https://docs.astral.sh/uv/getting-started/installation/).
- Python 3.13 or newer.
- A reasoning provider supported by Amplifier Agent: OpenAI, Anthropic, Gemini, ChatGPT OAuth or GitHub Copilot.
- `GOOGLE_API_KEY` or `GEMINI_API_KEY` for the separate Gemini image service, regardless of reasoning provider.

```bash
uv tool install git+https://github.com/robotdad/amplifier-smart-tool-infographic
```

To use it as a library:

```bash
uv add "infographic @ git+https://github.com/robotdad/amplifier-smart-tool-infographic"
```

To run it once without installing:

```bash
uvx --from git+https://github.com/robotdad/amplifier-smart-tool-infographic infographic --help
```

To teach a coding agent how to use it, install the [skill](skills/infographic/SKILL.md):

```bash
npx skills add robotdad/amplifier-smart-tool-infographic
```

To update:

```bash
uv tool upgrade infographic
npx skills update infographic   # add --global if the skill was installed globally
```

To uninstall:

```bash
uv tool uninstall infographic
npx skills remove infographic   # add --global if the skill was installed globally
```

Verify an install with `infographic manifest`, which needs no credentials.

## Interface

```bash
infographic check
infographic serve --store ./results
```

Open the full private URL printed by `serve`. Create a brief, review the result, download the PNG and refine it as a new version. The server listens only on `127.0.0.1`.

```bash
infographic generate "Explain a heat pump to a homeowner" --panels 3 --layout horizontal --store ./results
infographic list --store ./results
infographic refine RESULT_ID "Use larger labels" --store ./results
```

Reasoning uses **Amplifier Agent 0.22.0's public API** (binding and engine), with no shell, filesystem or MCP tools granted to the model. Select `--provider openai|anthropic|gemini|chatgpt|github` and optionally `--model`; omitted models resolve per provider: OpenAI/ChatGPT `gpt-6-luna`, Anthropic `claude-haiku-5-5`, Gemini `gemini-3.8-flash`, GitHub `gpt-5.4`. Defaults are suggestions, not proof of account entitlement. Explicit models are never substituted. Image generation separately uses `gemini-3.1-flash-image-preview`, configurable with `--image-model`. ChatGPT requires Agent-compatible OAuth login; GitHub needs a Copilot-entitled account via token or `gh auth login`.

Reasoning turns run in isolated processes with tool-owned public configuration. All five routes use Agent's public `reasoning_effort`, `working_directory`, `sessions_directory` and environment options. Medium effort is the default; unsupported values fail rather than switching models. Configuration is not a claim of effective delivery on every live call.

Each run retains its brief, plan, normalized role-labelled references, alternatives, selection, rendered images, deterministic composite, SHA256 hashes, reasoning usage where reported, image-call receipts, and actual-image review. Chosen panel one is analyzed before later panels render: observed visual properties replace speculative style, and the anchor is sent alongside original style references. Optional `--repair-rounds 1` permits one reviewed regeneration; default zero. Refinements supply all previous output images, retain originals and link their exact parent.

## Strong defaults, not rails

```bash
infographic generate "A watercolor coastal observatory at blue hour. No text." --mode freeform --orientation landscape
infographic generate "Explain the release process" --candidates 3 --representation diorama --style claymation
infographic select RESULT_ID 2
```

Freeform has its own planning and review criteria, without compulsory headings, labels or explanatory structure. Infographics support density-based automatic panel/layout planning, explicit overrides, curated styles and any custom aesthetic. One candidate is the bounded default; request two or three for meaningful alternatives. Manual selection pauses without producing later panels; `--selection auto` explicitly authorizes an image-based automatic choice, recorded as such.

Content references inform the plan, and freeform rendering also receives them as subject-only image context. Style references guide appearance and are sent to image generation. Both roles support browser uploads and CLI paths. Browser refinements expose mode, structure, style, representation, provider/model/effort and reference overrides. Existing output images are always supplied as revision inputs.

**Current limits:** no web fact checking, perfect generated text guarantee, image-service cost estimate, pixel-identical generative edits, cancellation or automatic crash replay. Completion and visual quality are separate: inspect the review verdict. Interrupted work remains inspectable and does not prevent explicit new requests; `close-interrupted` records acknowledgement only when its execution lock is no longer held. Candidate images remain available even when rejected. Browser reference limit is 4 MiB each; library/CLI limit is 12 MiB each, normalized to a maximum 1600px per side. Local browser and SDK regression tests simulate external services; live quality, five-provider entitlement and installed DTU acceptance require separate evidence. macOS/Windows support is a goal, not verified parity.

## Verification and remaining gaps

The initial local acceptance campaign passed 95 source tests, 95 installed tests
in the DTU Smart Tool, and 16 Smart Tool conformance checks. Live reasoning runs
exercised OpenAI, Anthropic, Gemini and GitHub Copilot. ChatGPT's missing-login
failure was checked; successful ChatGPT generation still requires OAuth and has
not been verified.

Actual browser journeys covered creation, candidate selection, refinement,
reopening and desktop/mobile downloads. Independent model review judged the
freeform revision and latest guided revision functionally met. Generated small
text can still be imperfect; earlier failed-quality results were preserved.
This is bounded functional evidence, not human acceptance or universal quality.

Upstream per-candidate automatic screening/regeneration is not reproduced.
There is no MCP App yet. The vision and contracts remain drafts.

## Attribution

Functional inspiration: [Gurkaran Singh's infographic-builder](https://github.com/singh2/infographic-builder), consulted at `26e9a307dbd0f4e355ab1ae8fa685766adb444b7`. This is an independent implementation; no source code, prompt prose or assets were copied. The source README declares MIT but its LICENSE target was absent when consulted.

See the [CLI reference](docs/02-cli.md) for every flag and the [library reference](docs/01-library.md) for the Python surface.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to set up your development environment.
