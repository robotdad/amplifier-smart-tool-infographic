# Vision

Status: DRAFT. User direction is recorded below; this document is not locked.

Create and refine images from the caller's direction. Rich infographic workflows,
styles and layouts provide a strong starting point, never compulsory rails.

## Goals

Turn a topic or supplied source material into a useful finished infographic, then
let the caller refine that retained work without losing the original.

- Offer freeform image creation and image-guided revision without mandatory
  infographic headings, explanatory text, panels, or preset aesthetics.
- Preserve the substantive infographic workflow: meaningful alternatives and
  retained selection, automatic layout and density-based panel planning, curated
  and freeform styles, diorama treatments, content/style reference roles, actual
  first-render style reconciliation, subsequent-panel consistency, and review.

- Plan layout, aesthetic, concise factual content, and one to six panels from a
  plain-language brief. Respect explicit layout, panel count, orientation, and style.
- Generate actual images, not placeholder cards. Use a shared style brief and the
  first rendered panel as the reference for later panels; assemble the composite
  deterministically and keep individual panels.
- Review the actual images for content, readability, visual explanation, prompt
  fidelity, and consistency. Record concrete issues separately from execution
  failure. Bound automatic repair and retain all attempts.
- Support references and refinement of an existing result. Keep provenance,
  original brief, plan, provider choices, review, files, and hashes together.
- Use only Amplifier Agent's supported public API for reasoning. Support OpenAI,
  Anthropic, Gemini, ChatGPT, and GitHub Copilot provider selection without silently
  switching providers. Image generation is a separate service, initially Gemini,
  and does not imply that every reasoning provider generates images.
  The requested integration version is 0.22.0 for both binding and engine.
- Ship an importable library, thin CLI, complete capability help, deterministic
  inspection/assembly, and a simple local browser experience for generation,
  review, refinement, and downloads.
- Verify a built installation in the DTU Smart Tool, including real generation,
  multiple panels, retained refinement, and usable downloaded images. Test all five
  provider routes; distinguish live evidence from simulated coverage and auth gaps.

## Non-Goals

- No dependence on an outer Amplifier bundle session or private runtime patches.
- No invented facts, hidden provider fallback, fabricated review, or demo images
  substituted for model output. Caller material is data, not tool authority.
- No hosted generation service, catalog submission, global credential changes, or
  scraping private user files. A public static GitHub Pages product site is now
  authorized; it does not expose the local generator or service credentials.
  Platform portability is a goal, not a claim of tested parity.
- No reproduction of the source bundle's code, prompts, or images. This is an
  independent implementation of its functional approach with attribution.

## Origin and authority

Requested by Marc Goodner in conversation
`85c5ddbb-ee9e-4e66-a46f-42d8a6eab2cd`, message
`9d49e9f2-be2d-440d-a1ac-bc13319d1653`:

> Can you go find the infographics builder bundle taht Gurkaran made, bring it down here, and lets build a version of that as a smart tool. Setup a new repo on my user for that, if his repo is public mine can be as well, if it is private keep mine private. Take this as complete as you can without further input from me. Keys needed for the services should be in place. The choice for the intelligence in this should be amplifier agent, support openai, anthropic, gemini, chatgpt, and github as providers. Use the dtu smart tool for validating how well it works. Only bother me if you are blocked or you have an end to end experience I can try.

Functional inspiration: Gurkaran Singh's public
https://github.com/singh2/infographic-builder at
`26e9a307dbd0f4e355ab1ae8fa685766adb444b7`. Its README declares MIT but its
LICENSE link has no tracked target. We retain a consult-only clone, credit the
source, and implement independently rather than republish its materials.

The goals above are engineering interpretation, not additional user quotations.
The browser experience is the chosen delivery approach. Acceptance prioritizes
functional fidelity and a usable result, not subjective aesthetic perfection.

### Subsequent direction in the same conversation

Version correction, superseding the earlier 0.20 request:

> sorry you siad .20 and I thought it was newest, use .22

Scope clarification:

> btw I really want all the infographic goodness from gurkaran's project but I don't want people locked on those rails, they should be able to direct any image generation they want through this as well, that just gives some really good core capabilities and styles

Verification direction:

> when you get to testing try using the simulated user testing ideas from <https://github.com/microsoft/amplifier-app-simulated-user-research>

Document guidance:

> I would also suggest at some point you may want to take a swing at developing a vision doc and contracts per converge practices to help track and guide your development.

Interpretation: freeform creation is a first-class path through the same retained
work experience; infographic techniques are available when useful, not forced.
The provider list governs reasoning through Agent. Gemini image generation remains
a separately identified service, with its own supported capabilities and limits.
Simulated journeys supply observed usability evidence, not invented human approval.
Drafting contracts does not ratify or lock their wording.

## Draft contracts

### Publication direction

The user subsequently authorized:

> commit and push what we have, look at the smart tool catalog and create the gh io pages from the templates there for it. Use unfold to figure out a logo for this, make an animated version of it to use in the io page.

This authorizes source publication and a static product site using catalog
templates, with Unfold-generated branding and animation. It does not turn the
static site into a hosted image service or ratify the draft contracts.

After rejecting the initial logo, the user directed:

> Can you publish the site without the logo? Then get to work on a new one?

Publish the static site without the rejected product mark or animation.
Replacement branding remains a separate design task and is reviewed before
being added to the live site.

- [Creation and refinement](../contracts/creation-refinement.v1.md)
- [Retained work](../contracts/retained-work.v1.md)

These describe seams and discriminating checks. Execution status belongs in
verification records, not in this vision. Neither passing tests nor an initial
implementation silently reduces the source-inspired capability inventory.

## Principles

- The library is the tool. The CLI and any other surface are thin wrappers over it.
- Deterministic capabilities run with no model provider configured, and never refuse to load without one.
- The intelligence is behind an interface, so another implementation is a new module rather than a rewrite.
- Target Windows, macOS, and Linux; distinguish tested platforms from portability goals.
