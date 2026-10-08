Acknowledge stopped work identified by `RUN_ID` in `--store`, without rerunning it.

```bash
infographic close-interrupted 0123456789abcdef0123456789abcdef --store ./results
```

Deterministic. Refuses while the operation holds its cross-process execution lock. Otherwise records the previous stage and caller acknowledgement, preserves all files and marks the run interrupted. Completed, failed, already interrupted or awaiting-selection records are unchanged.
A subsequent create uses a new identity and is deliberate new work, not recovery of unknown external effects. The dashboard also permits explicit new requests without requiring removal of historical interrupted records.