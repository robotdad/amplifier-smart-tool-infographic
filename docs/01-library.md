# Library Reference

Every capability of Infographic is reachable from `infographic.lib`.
All other surfaces, including the CLI, are thin wrappers over the library and add no capability of their own.

## Intelligence

Model-backed capabilities run through the `Intelligence` protocol in `infographic.intelligence.interface`:

```python
class Intelligence(Protocol):
    implementation: str

    def preflight(self) -> None: ...
    def run(self, request: AgentRequest) -> AgentResult: ...
```

`preflight` raises `InfographicError` naming what to configure when the implementation cannot run.
`run` executes one tool-free ephemeral Agent turn: `AgentRequest` holds prompt, provider, model, reasoning effort, timeout, required output schema and optional actual image bytes. `AgentResult` holds validated structured output, available usage, or a safe error.

`default_intelligence()` returns `AgentIntelligence`, built only on [Amplifier Agent's public API](https://github.com/microsoft/amplifier-agent).
Another implementation is a module satisfying the protocol and a branch in that factory.

The image service has a separate `ImageService` protocol (`preflight`, `render`) and a Gemini SDK implementation. It never changes the reasoning provider. Provider errors do not trigger fallback. Isolated worker processes use tool-owned public Agent 0.22 configuration, preventing unrelated host capture destinations and request overrides from being inherited. Binding and engine are both pinned to 0.22.0 in installation metadata, not only the development lock.

Effort uses public `AgentOptions.reasoning_effort` on all five routes, alongside `working_directory`, `sessions_directory` and scoped environment. No private engine imports or unsupported provider-parameter workarounds. Effective effort is not claimed from configuration alone.

## Product capabilities

```python
from pathlib import Path
from infographic import lib
from infographic.models import Brief

result = lib.generate(
    Brief(topic="Explain heat pumps", panels=3, layout="horizontal"),
    store=Path("./results"),
)
```

- `generate(brief, store, references=None, parent_id=None, feedback="", request_id=None, background=False, intelligence=None, image_service=None, style_references=None, revision_images=None)`: infographic or freeform planning, rendered alternatives, retained selection, assembly and actual-image review. Content references are at most three raster byte strings; style references at most two. Revision images are up to six prior outputs, supplied automatically by refine. Exact request IDs make retries read-only. Injection interfaces support provider-free tests. `background=True` returns admission while a bounded non-daemon thread runs.
- `select(run_id, candidate, store, request_id=None, background=False, intelligence=None, image_service=None)`: commit a 1-based candidate number from an awaiting-selection record. Exact selection retries observe the original operation. Alternative selections cannot replace the retained choice.
- `close_interrupted(run_id, store)`: deterministic acknowledgement of stopped work, refuses while the execution lock is held. Records previous stage and preserves outputs; never replays.
- `refine(run_id, feedback, store, changes=None, **kwargs)`: model-backed new child, inheriting the parent brief/settings with explicit `Brief` field overrides. Original bytes stay untouched.
- `inspect(run_id, store, verify=True)`: retained record with image hashes verified by default.
- `list_results(store, limit=50)`: recent result summaries, maximum 200.
- `artifact(run_id, name, store)`: only a registered artifact with matching hash, as bytes.
- `stitch_bytes(images, layout="vertical")`: 1 to 6 images assembled without cropping; returns PNG.
- `styles()`: original style suggestions.
- `check()`: installed versions and local credential presence, not live authentication.
- `dashboard(store, port=8765)`: constructs a loopback-only server; caller owns `serve_forever()` and `server_close()`.

Store defaults to `~/.local/share/infographic`. `Brief` validates mode, bounded source text, optional explicit panel count (otherwise density-based), auto/explicit layout and orientation, style/representation, 1-3 candidates, manual/auto selection, provider/model settings, per-call timeout and at most one automatic repair. Omitted model resolves to the chosen provider's default. Freeform accepts one output image, without infographic structure.
Results include `id`, `parent_id`, original brief, plan, role-labelled references/input hashes, candidates, selected candidate/actor/identity, observed anchor style, per-image files/hashes, attempts, review, stage history and call receipts. Manual alternatives pause in `awaiting-selection`; no read resumes generation. Failed/interrupted history does not block deliberate new work.
`status=completed` and `review.verdict=met` are different assertions. External failures leave `status=failed`, a safe error and any usable partial images. Exact retries never re-execute a failed or interrupted request.

The store is private local application data, not a multi-user security boundary against another process running as the same OS user. Keep its directory and launch URL private.

## Manifest

The tool's `SMART_TOOL.md` as structured data: the frontmatter as fields, the Markdown below it as `Manifest.body`.

```python
def load_manifest() -> Manifest
```

## Skill

What an agent reads once it has decided to drive the tool: the manifest body and the capability list, wrapped so the reader knows where the tool's files are.
Naming a capability returns that capability's own skill instead: the same wrapper, a heading carrying the capability's name, whether it is deterministic or model-backed, and the Markdown beside its code, which covers its arguments, a worked invocation, its result, and its failures.
The CLI's `--help` prints exactly this, the tool's at the root and the capability's on a command.
Raises `InfographicError` when the name is not a capability, naming the ones that are.

```python
def skill(capability: str | None = None) -> str
```

The capabilities the skill lists, one entry each, driven by the same table the CLI is built from:

```python
class Capability(NamedTuple):
    name: str
    summary: str
    model_backed: bool
    skill: str
    resources: tuple[str, ...] = ()
```

- `name` and `summary`: the command's name and its line in the tool's capability list.
- `model_backed`: whether it runs through the `Intelligence` interface, which decides the kind shown in both skills.
- `skill`: the capability's skill body, a Markdown file relative to `skill_directory()`, written without frontmatter, title, or kind line because the renderer supplies them.
- `resources`: the files that body refers to, relative to `skill_directory()`, listed under `<skill_resources>` in the capability's skill. The block is omitted when there are none.

The installed package root, resolved at runtime, where the files the skill names can be read.

```python
def skill_directory() -> Path
```

The files the skill lists under `<skill_resources>`, as paths relative to `skill_directory()`. Every one ships inside the package, so each resolves after installation.
The second does the same for one capability's skill, and raises `InfographicError` when the name is not a capability.

```python
def skill_resources() -> list[str]


def capability_skill_resources(capability: str) -> list[str]
```

The tool's canonical source, read from the package metadata's `[project.urls]` `Repository` entry, or `None` when the package declares none.
The skill carries it so a caller that can run the tool but not read its files still reaches the documentation.

```python
def repository_url() -> str | None
```

## Adding a capability

A capability's code goes in `infographic/capabilities/<name>/`, with its prompts, templates, and its own `SKILL.md` beside it, named on its row in `core/skill.py` `CAPABILITIES`, and `lib.py` gets a facade function that imports it and is the only caller of it.
Each capability of the library gets a section here: what it does and when to reach for it, the signature `lib.py` exposes, what each argument means, and what it returns or raises.
Model-backed capabilities say so, and take `model` and `reasoning_effort`, defaulting to `DEFAULT_INTELLIGENCE_MODEL` and `medium` from `infographic.schemas`.
