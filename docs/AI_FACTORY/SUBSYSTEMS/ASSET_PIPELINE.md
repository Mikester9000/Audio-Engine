# Asset Pipeline Status

## What exists now

- Legacy fixed-map generation remains available via `AssetPipeline.generate_*` and CLI:
  - `generate-game-assets`
  - `verify-game-assets`
- Request-driven generation is implemented via `RequestBatchPipeline` and CLI:
  - `generate-request-batch --batch-file ...`
- Plan-driven orchestration is implemented via `PlanBatchOrchestrator` and CLI:
  - `generate-plan-batch --plan-file ... --request-file ...`
  - plan targets select and order executable requests; missing required plan targets fail execution
- Per-request provenance sidecars are written for successful draft outputs:
  - `<stem>.provenance.json` with request ID, asset ID, backend, seed, prompt, output path, import path, review status, and timestamp
- QA/export/approval workflow is implemented end-to-end:
  - `qa-batch`
  - `export-drafts`
  - `approve-draft`
- Machine-readable review-log writing is executable:
  - `write-review-log`
  - optional review-log update flags on `approve-draft` and `export-drafts`
  - review entries are sourced from provenance sidecars and can optionally include `qa-batch` snapshot fields
- Request format behavior is strict:
  - requested `.ogg` outputs must be produced as `.ogg`
  - no silent OGG→WAV fallback in request-batch execution paths

## Current constraints

- Plan-driven execution requires request batches that contain executable entries for all required plan targets.
- Plan-driven execution now enforces per-target plan durations (`durationTargetSeconds`) by forwarding them as per-request duration overrides in request execution.
- Both request-batch execution entrypoints now support additive optional request-level `durationSeconds` for explicit music/SFX durations without requiring a plan file:
  - `generate-request-batch --batch-file` (`RequestBatchPipeline`)
  - backward-compatible `generate-request-batch --request-file` (`AssetPipeline.execute_request_batch`)
- On the legacy `--request-file` path, `--music-duration` and `--sfx-duration` remain fallback defaults for requests that omit `durationSeconds`.
- OGG export depends on `soundfile`; if unavailable, requests that specify `.ogg` fail.

## Near-term goal

Reduce remaining differences between the newer drafts/provenance-oriented request-batch pipeline and the backward-compatible legacy `--request-file` execution path without breaking stable CLI/output behavior.
