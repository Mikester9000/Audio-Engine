# Bug Tracking Guidance

> Update this file whenever bug triage conventions change.

## What counts as a bug in this repo

- generation command fails unexpectedly
- asset output is malformed, empty, clipped, or obviously wrong
- documented workflow no longer matches the repo
- deterministic reproduction is broken or missing
- downstream import expectations are violated

## Bug record minimum fields

- area (`music`, `sfx`, `voice`, `pipeline`, `docs`, `integration`, `qa`)
- symptom
- reproduction command
- expected result
- actual result
- priority
- suspected files

## Triage priority guide

| Priority | Meaning |
|---|---|
| P0 | blocks generation or validation entirely |
| P1 | produces bad core assets or breaks downstream integration |
| P2 | quality issue with workaround |
| P3 | cleanup, polish, or low-priority documentation drift |

## Rule

If a bug affects future agent understanding, update both the bug record and the relevant persistent-memory docs.
