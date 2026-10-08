Create a new result linked to a completed `RUN_ID`, using required `FEEDBACK`.
The original result and its hashes remain unchanged. Refinement is model-backed.

`--store` selects retained work. Provider/image settings inherit from the parent unless overridden:
`--provider`, `--model`, `--reasoning-effort`, `--image-model`.
Explicit structural changes use `--panels`, `--orientation`, `--layout`, `--style`, `--constraints`.
`--auto-panels` clears an inherited fixed count; do not combine it with `--panels`.
`--mode` changes between infographic and freeform, `--representation` requests diagram/scene/diorama,
`--candidates` and `--selection` control new alternatives. `--reference` and `--style-reference`
replace inherited references of that role; omitted references are retained. Browser/library also allow clearing a role.
`--request-id` supplies a stable 32-character lowercase hex identity for exact retries.

```bash
infographic refine 0123456789abcdef0123456789abcdef "Make the labels larger and simplify the diagram" --store ./results
```

Returns the same result envelope as generate, with `parent_id`. All panels are regenerated, not edited in place; there is no promise of pixel-identical unchanged regions. The entire previous plan and ALL prior output panels are supplied as revision images, separately from original style/content references. Changing provider without specifying a model resolves that provider's default. Explicit models are never changed.
Failure to read or verify the parent stops before model calls. A failed/in-progress parent cannot be refined. A new completed child can itself be refined, preserving the whole ancestry.