Read `RUN_ID` from `--store` (default `~/.local/share/infographic`) and verify all registered image hashes.

```bash
infographic inspect 0123456789abcdef0123456789abcdef --store ./results
```

Returns retained JSON, including failure details and partial artifacts. A failed result exits 1 but remains inspectable.
Missing records, symlinks or changed artifact bytes fail with an actionable diagnostic. No provider or network is required.