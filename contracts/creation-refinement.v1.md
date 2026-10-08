# Creation and refinement v1

Status: DRAFT. Core contains proposed promises, not locked clauses.
Authority: [vision and exact user direction](../docs/00-vision.md).

## Core

CR1. Caller intent governs. Guided infographic and freeform image creation are
first-class choices in the library, CLI and browser. Freeform requests are not
rewritten into infographic panels, text, headings or presets. Explicit direction
takes precedence over defaults; service limits produce an actionable explanation.

CR2. Infographic strengths remain available. Plan automatic layout, style and
content allocation, including density-based one-to-six panel decomposition.
Honor explicit counts and orientation. Offer curated aesthetics, freeform styling
and scene/diorama treatments. Offer meaningfully different candidates and retain
the caller's exact selection. Automatic selection is an explicit option, not
invented human approval.

CR3. Rendered evidence guides consistency. Analyze the chosen first panel before
producing later panels and replace the proposed style description with observed
visual properties. Later panels use that first image and any applicable original
style reference. Content references are not silently treated as style references.
Keep individual panels and deterministically assemble the ordered composite.

CR4. Refine the identified prior result, not whichever is newest. Supply relevant
prior images, brief and plan as context. Preserve original files and link the
new revision. Allow changed direction, style or structure explicitly. Do not
promise unchanged pixels from a generative image service.

CR5. Review actual images against the request. Report content, readability,
explanation, composition and consistency where relevant. Freeform review does
not require diagram qualities. Repairs are finite and attempts retained.
Execution completion and quality verdict are separate. No fabricated review or
perfect-text/fact-checking claim.

CR6. Reasoning uses public Amplifier Agent 0.22.0 binding and engine. OpenAI,
Anthropic, Gemini, ChatGPT and GitHub Copilot are selectable, with provider-specific
models and explicit effort. No silent fallback. Image generation is a separate
named service, initially Gemini. Report authentication and model support gaps
without calling metadata discovery or simulated tests live success.

## Backlogged

Exact topology-preserving DOT/Mermaid beautification is a source proposal, not
implemented upstream behavior at the consulted revision. No such guarantee here.
Additional image-generation services may be added without making the five
reasoning providers interchangeable image backends.

## Conformance

- Generate guided single/multi-panel examples and a no-text freeform landscape;
  wrong count, unwanted infographic structure or lost explicit choices falsify CR1/2.
- Exercise candidate selection, auto planning, curated/freeform/diorama styling
  and content versus style references. Compare actual downstream reference inputs
  and first-panel reconciliation with CR3.
- Revise an exact retained result twice, preserving previous hashes and proving
  requested visible changes. New unrelated generations do not establish CR4.
- Test failed review and bounded repair; review text without supplied pixels
  falsifies CR5. Separate external evaluation from product self-review.
- Check wheel metadata and installed binding/engine, provider/effort selection on
  the public boundary, and available live provider routes in the DTU Smart Tool.
- Use focused simulated-user journeys inspired by
  microsoft/amplifier-app-simulated-user-research. Retain actions, screenshots,
  downloaded bytes and failures; label simulated reactions separately.

Source capability inventory: singh2/infographic-builder at
26e9a307dbd0f4e355ab1ae8fa685766adb444b7, agents/infographic-builder.md,
docs/style-guide.md and behaviors/infographic.yaml. Independently implemented;
source prose, code and assets are not copied.

## Reserved

No unlimited model capability, public deployment, autonomous publication,
unbounded retries, hidden provider substitution or arbitrary filesystem authority.

## Changelog

- 2026-10-08: Initial draft derived from original intent and freeform/Agent0.22
  corrections. No ratification or locking recorded.