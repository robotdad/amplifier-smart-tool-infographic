# CLI Reference

The CLI is a thin wrapper over the [library](01-library.md): one command per capability, taking the same arguments under the same names, and doing nothing the library does not. 
What each argument means and what a capability returns or raises is documented there. This page covers only what the CLI adds: the invocation shape, and what reaches stdout, stderr, and the exit code.

Results go to stdout and diagnostics to stderr. A failure the library can name prints its message to stderr and exits 1; a bad invocation exits 2.

## Help

```
infographic -h                 terse summary for a person: the commands, a line each
infographic --help             the tool's skill, written for an agent driving it
infographic <command> -h       terse summary of one command: its arguments and defaults
infographic <command> --help   that command's skill, written for an agent about to call it
```

`--help` on the tool prints what `lib.skill()` returns and on a command what `lib.skill("<command>")` returns; the CLI adds nothing of its own.

## infographic manifest

```bash
infographic manifest
```

`lib.load_manifest()`, printed as JSON.

## Adding a command

Each command gets a section here: the invocation shape with its options and defaults, which library function it calls, and what it prints and exits with. Argument meanings belong in the library reference, not here.

## Product commands

```bash
infographic check
infographic styles
infographic generate "A concise explanation brief" --panels 2 --store ./results
infographic generate "Watercolor cliffside observatory, no text" --mode freeform --orientation landscape --store ./results
infographic generate "Explain a release workflow" --candidates 3 --style claymation --store ./results
infographic select RESULT_ID 2 --store ./results
infographic list --store ./results
infographic inspect RESULT_ID --store ./results
infographic refine RESULT_ID "Larger labels" --store ./results
infographic stitch panel-1.png panel-2.png --output composite.png --layout vertical
infographic serve --store ./results --port 8765
infographic close-interrupted RESULT_ID --store ./results
```

Each wraps the matching `lib` capability; stitch reads files and writes the returned PNG without overwriting an existing output.
Generate/refine print the full retained record, including on execution failure (exit 1).
Serve prints its private authentication URL to stderr and runs until interrupted. Open the full URL on the same machine.
Read each command's `--help` for complete flags and defaults. No hidden model fallback or implicit live calls from check/inspect/list/styles/stitch.
