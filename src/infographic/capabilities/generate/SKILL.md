Create actual Gemini images with a plan and visual review through Amplifier Agent.

## Arguments

- `TOPIC`: required explanation brief.
- `--store`: private retained-results directory; default `~/.local/share/infographic`.
- `--source`: optional UTF-8 file containing source material. No automatic web research.
- `--mode`: infographic (default) or freeform. Freeform follows image/artwork direction with no compulsory text, headings or diagram style.
- `--panels`: optional explicit 1 to 6; omitted means density-based planning. Freeform makes one image.
- `--orientation`: auto (default), portrait, landscape or square.
- `--layout`: auto (default), vertical, horizontal or grid assembly.
- `--style`: optional curated name or any visual treatment; omitted does not impose a preset.
- `--representation`: auto, diagram, scene or diorama; infographic-only.
- `--candidates`: 1 (default), 2 or 3 meaningfully different first images.
- `--selection`: manual (default) retains a pause when there are alternatives; auto explicitly authorizes image-based automatic choice. One candidate needs no choice.
- `--constraints`: required wording, audience, language or things to avoid.
- `--provider`: openai (default), anthropic, gemini, chatgpt or github.
- `--model`: omitted resolves by provider: openai/chatgpt gpt-6-luna, anthropic claude-haiku-5-5, gemini gemini-3.8-flash, github gpt-5.4. Explicit values are never substituted. Defaults are not entitlement evidence.
- `--reasoning-effort`: none, minimal, low, medium (default), high, xhigh or max; sent through public Agent 0.22 options, provider support varies.
- `--image-model`: separate Gemini image model; default gemini-3.1-flash-image-preview.
- `--timeout-seconds`: per reasoning turn or image request, 10 to 600; default 180.
- `--repair-rounds`: 0 (default) or 1; an optional complete re-render if review finds issues.
- `--reference`: content-source raster path, repeatable up to three. Informs factual/subject planning, not style. Freeform also sends it as subject-only image context; guided rendering uses the extracted plan instead.
- `--style-reference`: aesthetic raster path, repeatable up to two. Passed to generation, including alongside the chosen first-panel anchor.
- `--request-id`: optional 32 lowercase hex characters. Exact retry reads the prior result without new model calls; changed inputs are refused.

```bash
infographic generate "Explain the water cycle for a classroom" --panels 3 --layout horizontal --constraints "Use only evaporation, condensation and precipitation as stage names"
```

Returns JSON containing ID, brief, plan, provider settings, review, files and SHA256 hashes.
Images and all repair attempts are retained under STORE/ID. `status=completed` means execution completed, not that the visual review passed. Check `attempts[-1].review`.
A run uses one planning turn; alternatives add one alternatives turn and 2-3 first-image calls. Automatic choice adds one image-based choice turn. Each infographic attempt analyzes its chosen first image before later panels, then reviews the actual completed images. Freeform uses its own plan/review criteria and skips infographic anchor analysis. Repairs regenerate once at most.
Manual alternatives return `awaiting-selection`; use `select` to continue the same retained request. Alternatives, selection and revisions survive reopen without new calls.
There is no automatic provider fallback. Reference images are normalized to PNG at maximum 1600 pixels per side; original input hashes are retained.

Image generation always needs GOOGLE_API_KEY or GEMINI_API_KEY. Reasoning needs the selected provider's credentials or subscription login. Failures retain partial images and a safe actionable error; CLI exits 1. Exact retry does not re-execute failed or interrupted work. A fresh request ID is explicit new paid work.