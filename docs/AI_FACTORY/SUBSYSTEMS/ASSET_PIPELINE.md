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
- Request format behavior is strict:
  - requested `.ogg` outputs must be produced as `.ogg`
  - no silent OGG→WAV fallback in request-batch execution paths

## Current constraints

- Plan-driven execution requires request batches that contain executable entries for all required plan targets.
- Per-target duration from plan metadata (`durationTargetSeconds`) is still guidance; current request-batch execution does not yet enforce this value as a hard duration override.
- OGG export depends on `soundfile`; if unavailable, requests that specify `.ogg` fail.

## Near-term goal

Execute `SESSION-011` to document backend evaluation and dependency/availability guidance so the current backend registry/selection surfaces can be used consistently by future sessions.
