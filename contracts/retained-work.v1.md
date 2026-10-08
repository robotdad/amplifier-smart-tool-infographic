# Retained work v1

Status: DRAFT. Core contains proposed promises, not locked clauses.
Authority: [vision and exact user direction](../docs/00-vision.md).

## Core

RW1. A retained request has an identity, original inputs, selected provider/model,
image service, state, and actual outputs. Preserve plans, candidate choices,
review findings, repair attempts, revision ancestry and artifact hashes.
Never replace a failed attempt's evidence with a later success.

RW2. Exact retries observe the same request; conflicting inputs under that
identity are rejected. Refreshing or reopening does not start generation.
Uncertain or interrupted execution is not success and is not automatically replayed.

RW3. Existing results remain inspectable and downloadable when credentials are
missing or a new operation fails. Serve only registered, integrity-checked
artifacts from the chosen store; never arbitrary caller/model paths.

RW4. Library, CLI and local browser operate the same retained identities and
capabilities. Show actual stages, issues and usable partial artifacts honestly.
Selection and refinement target the displayed revision, including after refresh
or navigation. Downloaded image bytes match the selected artifact.

RW5. Restrict local browser access and mutations to the intended user/session.
Do not expose keys in results, error text or URLs. User/model-supplied content is
data, not authority to execute code, browse private files or expand access.

## Backlogged

Multi-user collaboration, remote hosting and MCP App delivery are not initial
promises. Durable automatic restart/resumption of an interrupted generation is
not promised; retained state must not falsely say it completed.

## Conformance

- In the installed DTU package, create, reopen, revise and download real images.
  Verify original and selected-download hashes, revision links, and repeated
  reads producing no generation.
- Deny changed payloads for the same identity, arbitrary paths, unregistered
  files, cross-origin mutations and integrity failures. Test concurrent admission.
- Simulate service/auth failure and process interruption without discarding
  previous images. Verify a user can inspect prior work and make an explicit
  subsequent request without guessing which work is still active.
- Drive the real browser at desktop and phone widths. Inspect selection during
  delayed operations, refresh, failure, and refinement; screenshots alone do not
  prove downloads, persistence or targeting.
- Keep candidate/version, exact check, observed result, evidence, gap and owner
  in the existing acceptance record. Passing checks do not lock this draft.

## Reserved

The store is private single-user data, not isolation from a hostile same-UID
process. No automatic deletion of originals, hidden uncertain-effect retries,
or public sharing of retained content.

## Changelog

- 2026-10-08: Initial draft for the authorized local Smart Tool experience.
  No ratification or locking recorded.