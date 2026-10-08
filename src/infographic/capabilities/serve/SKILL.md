Serve a local dashboard over the same library. `--store` selects retained work;
`--port` selects a port, default 8765; 0 asks the operating system for a free port.

```bash
infographic serve --store ./results --port 8765
```

Prints a private launch URL to stderr. Open the whole URL to authenticate. The server binds only 127.0.0.1.
The page creates infographics, displays actual stages, reviews and provenance, refines completed results, and downloads verified panels/composites.
Startup, listing and viewing are deterministic; submitting creation/refinement makes model calls and may incur paid usage.

Do not publish or forward this server to the network. The launch token grants access to all material in the selected store.
Browser controls include infographic/freeform mode, auto/explicit structure, curated/custom styles and diorama representation, 1-3 alternatives, manual/automatic choice, content/style reference uploads and structural/provider revision overrides.
Each upload is at most 4 MiB. The selected prior revision's images are automatically supplied to refinement.
Submissions are persisted in browser IndexedDB before sending. A lost acknowledgement offers observation or exact-payload retry; refresh never submits. Per-tab selected result and target-specific drafts survive reload.
Interrupted records do not block deliberate new requests. Acknowledge interruption explicitly to retain an honest terminal state; a running operation's lock prevents premature acknowledgement. No automatic replay.
Stop with Ctrl+C. An in-flight bounded background job is allowed to finish before process exit. No cancellation/restart recovery claim. Port conflicts fail before serving.