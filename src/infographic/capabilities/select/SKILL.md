Select `CANDIDATE` (1-based number) from exact retained `RUN_ID`.
`--store` selects the private result directory. `--request-id` is an optional stable 32-character lowercase hex selection identity.

```bash
infographic select 0123456789abcdef0123456789abcdef 2 --store ./results
```

Model-backed: uses the selected result's retained provider/model/effort and original references. The chosen first image is analyzed before later panels render. Its observed style replaces the speculative description. Returns the result envelope with retained selection actor and identity.
Exact retry with the same identity and candidate only observes the prior operation; it never starts production twice. A different selection after commitment fails. All rejected candidate images remain downloadable. Failed or interrupted selection is not automatically replayed.