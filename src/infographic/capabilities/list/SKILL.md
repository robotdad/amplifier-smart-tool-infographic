List recent results from `--store`, default `~/.local/share/infographic`. `--limit` is 1 to 200, default 50.

```bash
infographic list --store ./results --limit 20
```

Returns a JSON array with IDs, timestamps, briefs, parents and status. An absent store returns an empty array.
Unreadable records are omitted; use inspect with a known ID to diagnose them. No model calls.