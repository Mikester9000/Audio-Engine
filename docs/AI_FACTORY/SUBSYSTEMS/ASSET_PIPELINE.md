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
- Direct request-batch execution (`generate-request-batch --batch-file`) now supports additive optional request-level `durationSeconds` for explicit music/SFX durations without requiring a plan file.
- OGG export depends on `soundfile`; if unavailable, requests that specify `.ogg` fail.

## Near-term goal

Unify explicit-duration behavior across both request-batch execution paths (`--batch-file` and backward-compat `--request-file`) while preserving additive compatibility.
